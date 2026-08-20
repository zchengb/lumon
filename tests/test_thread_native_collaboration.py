from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from agents.conversation.config import thread_native_config
from agents.conversation.relay import ConversationRelay, record_inbound_message
from agents.conversation.thread_context import ThreadContextLoader
from agents.conversation.thread_store import ThreadMessage, ThreadTranscriptStore
from agents.jobs.broker import execute_job_action
from agents.security.actions import ActionRequest
from feishu.agent_mentions import has_any_agent_or_user_mention, parse_agent_mentions
from feishu.client_registry import FeishuClientConfig
from feishu.messenger import FeishuMessenger
from agents.profiles import PROFILES
from feishu.handlers import should_handle


def test_mentions_are_exact_and_ignore_urls_code_and_quotes() -> None:
    text = "@Mark S. https://example.test/@Dylan `@Irving`\n> @Milchick"
    assert [item.agent_id for item in parse_agent_mentions(text)] == ["mark"]
    assert not has_any_agent_or_user_mention("email=a@example.com https://x.test/@Mark")
    assert parse_agent_mentions("@Mark Smith please review") == []
    assert [item.agent_id for item in parse_agent_mentions("@Mark please review")] == ["mark"]


def test_thread_store_is_idempotent_and_context_is_shared() -> None:
    with TemporaryDirectory() as tmp:
        store = ThreadTranscriptStore(Path(tmp) / "thread.sqlite3")
        record_inbound_message(
            message_id="u1",
            meta={"chat_id": "oc_chat", "root_id": "u1", "user_id": "ou_user"},
            text="Please have Mark inspect this.",
            mentions=["mark"],
            store=store,
        )
        store.record(
            ThreadMessage(
                message_id="m1",
                chat_id="oc_chat",
                root_id="u1",
                parent_id="u1",
                sender_kind="agent",
                sender_agent_id="milchick",
                text="@Mark I am handing this thread to you.",
            )
        )
        # Replaying the same Feishu event must not duplicate transcript rows.
        record_inbound_message(
            message_id="u1",
            meta={"chat_id": "oc_chat", "root_id": "u1", "user_id": "ou_user"},
            text="Please have Mark inspect this.",
            store=store,
        )
        messages = store.list_messages(chat_id="oc_chat", root_id="u1")
        assert [item.message_id for item in messages] == ["u1", "m1"]
        context = ThreadContextLoader(store).load(
            {"chat_id": "oc_chat", "root_id": "u1", "message_id": "m2"},
            exclude_message_id="m2",
        )
        assert "User:" in context.text
        assert "Milchick:" in context.text
        assert "@Mark" in context.text
        store.close()


def test_relay_preserves_human_authority_and_deduplicates() -> None:
    with TemporaryDirectory() as tmp:
        store = ThreadTranscriptStore(Path(tmp) / "thread.sqlite3")
        calls: list[tuple[str, str, dict[str, str]]] = []

        def dispatch(agent: str, text: str, meta: dict[str, str]) -> None:
            calls.append((agent, text, meta))

        relay = ConversationRelay(
            store=store,
            dispatch=dispatch,
        )
        meta = {
            "chat_id": "oc_chat",
            "root_id": "u1",
            "message_id": "u1",
            "user_id": "ou_human",
            "_project_slug": "mbpass",
            "_thread_native_handoff": "1",
        }
        relay.publish(
            source_agent_id="milchick",
            source_message_id="m1",
            text="@Mark please continue.",
            meta=meta,
            common={"agent_collaboration": {"thread_native_handoff": True}},
            dispatch_async=False,
        )
        relay.publish(
            source_agent_id="milchick",
            source_message_id="m1",
            text="@Mark please continue.",
            meta=meta,
            common={"agent_collaboration": {"thread_native_handoff": True}},
            dispatch_async=False,
        )
        assert len(calls) == 1
        assert calls[0][0] == "mark"
        assert calls[0][2]["user_id"] == "ou_human"
        assert calls[0][2]["_source_agent"] == "milchick"
        assert calls[0][2]["_relay_hop"] == "1"
        store.close()


def test_native_milchick_handoff_does_not_create_job() -> None:
    with TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        (workspace / "config").mkdir(parents=True)
        (workspace / "config" / "common.json").write_text(
            json.dumps({"agent_collaboration": {"thread_native_handoff": True}}),
            encoding="utf-8",
        )
        request = ActionRequest(
            agent_id="milchick",
            action="agent.job.create",
            project_slug="mbpass",
            actor_user_id="ou_user",
            chat_id="oc_chat",
            thread_id="omt_thread",
            source_message_id="u1",
            trace_id="tr_test",
            arguments={
                "target_agent": "mark",
                "capability": "loop.technical",
                "issue_key": "MBPAS-1503",
                "user_message": "Please produce a Technical Plan for MBPAS-1503.",
                "_workspace_path": str(workspace),
                "_thread_native_handoff": "1",
                "chat_type": "group",
            },
        )
        with patch("agents.jobs.broker.AgentJobBroker.create_parent") as create_parent:
            result = execute_job_action(request)
        assert result["thread_native"] is True
        assert result["job_created"] is False
        assert "@Mark" in result["handoff_text"]
        create_parent.assert_not_called()


def test_feature_flag_defaults_off() -> None:
    assert thread_native_config({}).enabled is False
    assert thread_native_config({"agent_collaboration": {"thread_native_handoff": True}}).enabled is True


def test_reply_agent_text_records_and_relays_each_visible_chunk() -> None:
    with TemporaryDirectory() as tmp:
        previous = os.environ.get("LUMEN_AGENTS_HOME")
        os.environ["LUMEN_AGENTS_HOME"] = tmp
        try:
            messenger = FeishuMessenger("milchick")
            text = "@Mark please continue.\n\n" + ("evidence " * 1800)
            counter = {"value": 0}

            def send_part(*args: object, **kwargs: object) -> dict[str, object]:
                counter["value"] += 1
                return {"data": {"message_id": f"outbound-{counter['value']}"}}

            with patch.object(messenger, "reply_markdown", side_effect=send_part), patch.object(
                ConversationRelay, "_dispatch", return_value=None
            ):
                sent = messenger.reply_agent_text(
                    "user-1",
                    text,
                    reply_in_thread=True,
                    conversation_meta={
                        "message_id": "user-1",
                        "chat_id": "oc_chat",
                        "root_id": "user-1",
                        "user_id": "ou_user",
                    },
                    conversation_common={
                        "agent_collaboration": {"thread_native_handoff": True}
                    },
                )
            assert sent["data"]["message_id"] == f"outbound-{counter['value']}"
            store = ThreadTranscriptStore()
            try:
                messages = store.list_messages(chat_id="oc_chat", root_id="user-1")
                assert len(messages) >= 2
                assert messages[0].mentions == ["mark"]
            finally:
                store.close()
        finally:
            if previous is None:
                os.environ.pop("LUMEN_AGENTS_HOME", None)
            else:
                os.environ["LUMEN_AGENTS_HOME"] = previous


def test_native_direct_reply_routes_only_to_the_agent_message_owner() -> None:
    with TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        (workspace / "config").mkdir(parents=True)
        (workspace / "config" / "common.json").write_text(
            json.dumps({"agent_collaboration": {"thread_native_handoff": True}}),
            encoding="utf-8",
        )
        previous = os.environ.get("LUMEN_AGENTS_HOME")
        os.environ["LUMEN_AGENTS_HOME"] = tmp
        try:
            store = ThreadTranscriptStore()
            store.record(
                ThreadMessage(
                    message_id="mark-reply",
                    chat_id="oc_chat",
                    root_id="user-root",
                    sender_kind="agent",
                    sender_agent_id="mark",
                    text="I need one decision.",
                )
            )
            store.close()
            event = {
                "event": {
                    "message": {
                        "message_id": "user-followup",
                        "chat_id": "oc_chat",
                        "chat_type": "group",
                        "parent_id": "mark-reply",
                        "root_id": "user-root",
                        "content": json.dumps({"text": "Here is the decision."}),
                        "mentions": [],
                    },
                    "sender": {"sender_type": "user", "sender_id": {"open_id": "ou_user"}},
                }
            }
            with patch("feishu.handlers.resolve_project", return_value={"workspace": str(workspace)}):
                mark = FeishuClientConfig("mark", "cli_m", "secret", PROFILES["mark"])
                milchick = FeishuClientConfig("milchick", "cli_c", "secret", PROFILES["milchick"])
                assert should_handle(event, mark) is True
                assert should_handle(event, milchick) is False
        finally:
            if previous is None:
                os.environ.pop("LUMEN_AGENTS_HOME", None)
            else:
                os.environ["LUMEN_AGENTS_HOME"] = previous
