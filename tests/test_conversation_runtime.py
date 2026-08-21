#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from agents.compat.legacy_envelopes import parse_native_response
from agents.conversation.config import ThreadNativeConfig, native_provider_contract
from agents.conversation.event_bus import EventBus
from agents.conversation.events import ConversationEvent
from agents.conversation.output import ConversationOutput
from agents.conversation.thread_store import ThreadTranscriptStore
from agents.conversation.thread_context import ThreadContextLoader
from agents.runtime.jobs_pool import run_conversation_job
from agents.runtime.connected_tools import ConnectedToolExecutor, ConnectedToolRegistry
from agents.runtime.harness_events import from_provider_event
from agents.runtime.interaction import interaction_contract_prompt
from agents.runtime.session_host import AgentSessionHost
from agents.runtime.session_store import SessionStore
from agents.security.trusted import TrustedActionContext
from risk.store import GlobalAgentStore


class _FakeMessenger:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def reply_agent_text(self, message_id: str, text: str, **kwargs: object) -> dict[str, object]:
        self.calls.append(("reply", text))
        return {"data": {"message_id": f"reply-{len(self.calls)}"}}

    def upload_file(self, path: Path) -> str:
        self.calls.append(("upload", path.name))
        return "file-key"

    def reply_file(self, message_id: str, file_key: str, **kwargs: object) -> dict[str, object]:
        self.calls.append(("reply_file", file_key))
        return {"data": {"message_id": f"file-{len(self.calls)}"}}


class ConversationRuntimeTests(unittest.TestCase):
    def test_event_bus_persists_and_replays_after_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ThreadTranscriptStore(Path(tmp) / "thread.sqlite3")
            bus = EventBus(store=store)
            first = bus.publish(
                ConversationEvent.create(
                    thread_id="root-1",
                    chat_id="chat-1",
                    agent_id="mark",
                    type="agent.finding",
                    text="The scheduler has one shared dispatcher.",
                    dedupe_key="finding:1",
                )
            )
            duplicate = bus.publish(
                ConversationEvent.create(
                    thread_id="root-1",
                    chat_id="chat-1",
                    agent_id="mark",
                    type="agent.finding",
                    text="The scheduler has one shared dispatcher.",
                    dedupe_key="finding:1",
                )
            )
            second = bus.publish(
                ConversationEvent.create(
                    thread_id="root-1",
                    chat_id="chat-1",
                    agent_id="dylan",
                    type="agent.decision",
                    text="Keep activity-level sent markers.",
                )
            )
            self.assertIsNotNone(first)
            self.assertIsNone(duplicate)
            self.assertIsNotNone(second)
            replay = bus.replay(chat_id="chat-1", thread_id="root-1", after_event_id=first.event_id)
            self.assertEqual([second.event_id], [item.event_id for item in replay])
            self.assertTrue(bus.has_dedupe("finding:1"))
            bus.close()
            store.close()

    def test_native_output_sends_multiple_messages_and_deduplicates_before_transport(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ThreadTranscriptStore(root / "thread.sqlite3")
            bus = EventBus(store=store)
            messenger = _FakeMessenger()
            output = ConversationOutput(
                agent_id="mark",
                meta={
                    "message_id": "human-1",
                    "chat_id": "chat-1",
                    "root_id": "human-1",
                    "_workspace_path": str(root),
                },
                messenger=messenger,
                event_bus=bus,
                config=ThreadNativeConfig(minimum_event_interval_seconds=0),
            )
            first = output.message("I found the shared dispatcher.")
            duplicate = output.message("I found the shared dispatcher.")
            second = output.decision("I will preserve the existing dispatcher and add a marker.")
            self.assertEqual("succeeded", first.status)
            self.assertEqual("duplicate", duplicate.status)
            self.assertEqual("succeeded", second.status)
            self.assertEqual(["reply", "reply"], [kind for kind, _ in messenger.calls])
            self.assertEqual(2, len(bus.replay(chat_id="chat-1", thread_id="human-1")))
            output.close()
            bus.close()
            store.close()

    def test_internal_harness_telemetry_is_persisted_without_feishu_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ThreadTranscriptStore(root / "thread.sqlite3")
            bus = EventBus(store=store)
            messenger = _FakeMessenger()
            output = ConversationOutput(
                agent_id="mark",
                meta={"message_id": "human-1", "chat_id": "chat-1", "root_id": "human-1"},
                messenger=messenger,
                event_bus=bus,
            )
            receipt = output.observe("tool.started", tool="jira.get", call_id="c1")
            self.assertEqual("succeeded", receipt.status)
            self.assertEqual([], messenger.calls)
            events = bus.replay(chat_id="chat-1", thread_id="human-1", visibility="internal")
            self.assertEqual(1, len(events))
            self.assertEqual("tool.started", events[0].type)
            self.assertFalse(events[0].user_visible)
            output.close()
            bus.close()
            store.close()

    def test_public_output_firewall_removes_transport_syntax_and_records_telemetry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ThreadTranscriptStore(root / "thread.sqlite3")
            bus = EventBus(store=store)
            messenger = _FakeMessenger()
            output = ConversationOutput(
                agent_id="mark",
                meta={"message_id": "human-1", "chat_id": "chat-1", "root_id": "human-1"},
                messenger=messenger,
                event_bus=bus,
                config=ThreadNativeConfig(minimum_event_interval_seconds=0),
            )
            filtered = output.message(
                '<ACTION_REQUEST>{"action":"jira.workitem.create","arguments":{}}</ACTION_REQUEST>'
            )
            self.assertEqual("filtered", filtered.status)
            self.assertEqual([], messenger.calls)
            internal = bus.replay(chat_id="chat-1", thread_id="human-1", visibility="internal")
            self.assertTrue(any(item.type == "conversation.protocol_leak.prevented" for item in internal))

            unwrapped = output.message("<FINAL_RESPONSE>Hello from the native Agent.</FINAL_RESPONSE>")
            self.assertEqual("succeeded", unwrapped.status)
            self.assertEqual(("reply", "Hello from the native Agent."), messenger.calls[-1])
            output.close()
            bus.close()
            store.close()

    def test_native_artifact_requires_workspace_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "plan.pdf"
            artifact.write_bytes(b"pdf")
            messenger = _FakeMessenger()
            store = ThreadTranscriptStore(root / "thread.sqlite3")
            output = ConversationOutput(
                agent_id="mark",
                meta={
                    "message_id": "human-1",
                    "chat_id": "chat-1",
                    "root_id": "human-1",
                    "_workspace_path": str(root),
                },
                messenger=messenger,
                event_bus=EventBus(store=store),
                config=ThreadNativeConfig(minimum_event_interval_seconds=0),
            )
            sent = output.artifact(artifact, text="The requested artifact is ready.")
            blocked = output.artifact(Path(tmp).parent / "outside.pdf")
            self.assertEqual("succeeded", sent.status)
            self.assertEqual("failed", blocked.status)
            self.assertEqual(["reply", "upload", "reply_file"], [kind for kind, _ in messenger.calls])
            output.close()
            output.event_bus.close()
            store.close()

    def test_relative_artifact_path_is_resolved_against_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "output" / "pdf").mkdir(parents=True)
            (root / "output" / "pdf" / "plan.pdf").write_bytes(b"pdf")
            store = ThreadTranscriptStore(root / "thread.sqlite3")
            bus = EventBus(store=store)
            messenger = _FakeMessenger()
            output = ConversationOutput(
                agent_id="mark",
                meta={
                    "message_id": "human-1",
                    "chat_id": "chat-1",
                    "root_id": "human-1",
                    "_workspace_path": str(root),
                },
                messenger=messenger,
                event_bus=bus,
                config=ThreadNativeConfig(minimum_event_interval_seconds=0),
            )
            receipt = output.artifact("output/pdf/plan.pdf")
            self.assertEqual("succeeded", receipt.status)
            self.assertEqual(("upload", "plan.pdf"), messenger.calls[0])
            output.close()
            bus.close()
            store.close()

    def test_artifact_event_is_available_to_the_next_agent_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ThreadTranscriptStore(Path(tmp) / "thread.sqlite3")
            bus = EventBus(store=store)
            bus.publish(
                ConversationEvent.create(
                    thread_id="root-1",
                    chat_id="chat-1",
                    agent_id="mark",
                    type="agent.artifact",
                    text="The current plan PDF is ready.",
                    payload={"path": "output/pdf/plan.pdf"},
                )
            )
            context = ThreadContextLoader(store).load(
                {"chat_id": "chat-1", "root_id": "root-1", "message_id": "human-2"},
            )
            self.assertIn("Mark [artifact]: plan.pdf", context.text)
            self.assertEqual(1, len(context.events))
            self.assertTrue(context.last_event_id)
            bus.close()
            store.close()

    def test_same_inbound_message_can_run_for_two_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            previous = os.environ.get("LUMEN_AGENTS_HOME")
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            try:
                mark = run_conversation_job(
                    message_id="human-1",
                    chat_id="chat-1",
                    thread_id="root-1",
                    user_id="user-1",
                    agent_id="mark",
                    worker=lambda: {"status": "ok", "action": "mark"},
                )
                dylan = run_conversation_job(
                    message_id="human-1",
                    chat_id="chat-1",
                    thread_id="root-1",
                    user_id="user-1",
                    agent_id="dylan",
                    worker=lambda: {"status": "ok", "action": "dylan"},
                )
                duplicate = run_conversation_job(
                    message_id="human-1",
                    chat_id="chat-1",
                    thread_id="root-1",
                    user_id="user-1",
                    agent_id="mark",
                    worker=lambda: {"status": "should-not-run"},
                )
                self.assertEqual("completed", mark["status"])
                self.assertEqual("completed", dylan["status"])
                self.assertEqual("duplicate", duplicate["status"])
            finally:
                if previous is None:
                    os.environ.pop("LUMEN_AGENTS_HOME", None)
                else:
                    os.environ["LUMEN_AGENTS_HOME"] = previous

    def test_session_host_waiting_is_per_agent_and_resumable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            global_store = GlobalAgentStore(Path(tmp) / "agents.sqlite3")
            sessions = SessionStore(global_store)
            session = sessions.create(
                agent_id="mark",
                chat_id="chat-1",
                conversation_scope_id="agent:mark:thread:chat-1:root-1",
                workspace_path=tmp,
            )
            transcript = ThreadTranscriptStore(Path(tmp) / "thread.sqlite3")
            bus = EventBus(store=transcript)
            host = AgentSessionHost(session_store=sessions, event_bus=bus)
            host.register(session, thread_id="root-1", chat_id="chat-1")
            waiting = host.start(
                session["session_id"],
                event={"text": "choose"},
                runner=lambda event, state: {"status": "waiting_human", "question": "Choose A or B."},
            )
            self.assertEqual("waiting_human", host.state(session["session_id"]).state)
            self.assertEqual("waiting_human", sessions.runtime_state(sessions.get(session["session_id"])))
            resumed = host.resume(
                session["session_id"],
                {"text": "A"},
                runner=lambda event, state: {"status": "completed", "provider_session_id": "provider-1"},
            )
            self.assertEqual("completed", host.state(session["session_id"]).state)
            self.assertEqual("provider-1", resumed.get("provider_session_id", ""))
            lifecycle = bus.replay(chat_id="chat-1", thread_id="root-1", visibility="internal")
            self.assertTrue(any(item.type == "session.waiting" for item in lifecycle))
            host.close()
            bus.close()
            transcript.close()
            sessions.close()

    def test_native_registry_exposes_tools_without_legacy_conversation_actions(self) -> None:
        registry = ConnectedToolRegistry(include_legacy=False)
        names = {item.name for item in registry.list()}
        self.assertIn("jira.update", names)
        self.assertIn("bitable.write", names)
        self.assertIn("feishu.file", names)
        self.assertIn("agent.directory", names)
        self.assertIn("agent.job.create", names)
        self.assertNotIn("agent.delegate", names)
        self.assertNotIn("feishu.say", names)

        calls: list[tuple[str, dict[str, object], str]] = []

        def native(name: str, args: dict[str, object], context: TrustedActionContext) -> dict[str, object]:
            calls.append((name, args, context.agent_id))
            return {"status": "succeeded", "tool": name}

        executor = ConnectedToolExecutor(registry=registry, native_executor=native)
        context = TrustedActionContext(
            agent_id="mark",
            project_slug="mbpass",
            actor_user_id="ou-user",
            chat_id="chat-1",
            thread_id="root-1",
            source_message_id="m1",
            trace_id="trace-1",
        )
        result = executor.execute(
            "jira.update",
            {"issue_key": "MBPAS-1", "actor_user_id": "forged", "_workspace_path": "/tmp/forged"},
            context=context,
        )
        self.assertEqual("succeeded", result["status"])
        self.assertEqual(("jira.workitem.update", {"issue_key": "MBPAS-1"}, "mark"), calls[0])

    def test_native_adapter_redacts_secret_metadata_and_native_parser_never_executes_envelopes(self) -> None:
        event = from_provider_event(
            {
                "type": "progress",
                "message": "Checking the workspace",
                "api_key": "should-not-be-shared",
                "phase": "investigate",
            },
            provider="codex",
        )
        self.assertIsNotNone(event)
        self.assertNotIn("api_key", json.dumps(event.to_dict()))
        parsed = parse_native_response(
            '<ACTION_REQUEST>{"action":"jira.update","arguments":{"issue_key":"MBPAS-1"}}</ACTION_REQUEST>'
            '<FINAL_RESPONSE>Only this text is visible.</FINAL_RESPONSE>'
        )
        self.assertEqual("native", parsed.mode)
        self.assertEqual("Only this text is visible.", parsed.text)
        self.assertEqual([], parsed.action_requests)

    def test_native_tool_events_preserve_a_safe_connected_tool_request(self) -> None:
        event = from_provider_event(
            {
                "type": "tool_call",
                "tool_call": {
                    "name": "jira.update",
                    "arguments": {"issue_key": "MBPAS-1", "description": "ready"},
                },
                "call_id": "call-1",
            },
            provider="codex",
        )
        self.assertIsNotNone(event)
        self.assertEqual("tool_call", event.type)
        self.assertEqual("jira.update", event.payload["tool"])
        self.assertEqual("MBPAS-1", event.payload["arguments"]["issue_key"])

    def test_native_prompt_does_not_require_legacy_markers(self) -> None:
        prompt = interaction_contract_prompt(agent_id="mark", native_provider=True)
        for marker in ("ACTION_REQUEST", "FINAL_RESPONSE", "CLARIFICATION_REQUEST", "CONVERSATION_DECISION"):
            self.assertNotIn(marker, prompt)
        self.assertIn("connected-tool registry", prompt)

    def test_native_provider_aliases_include_cursor_cli(self) -> None:
        config = ThreadNativeConfig(native_first=True)
        self.assertTrue(native_provider_contract("cursor_cli", config))
        self.assertTrue(native_provider_contract("codex", config))
        self.assertFalse(native_provider_contract("openai_compatible", config))


if __name__ == "__main__":
    unittest.main()
