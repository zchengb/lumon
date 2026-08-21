from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.definitions import ensure_definitions_loaded, get_definition
from agents.runner.local_isolated import TrustedAgentRunner
from agents.runtime.autonomous import _publish_native_workstream_events
from agents.runtime.connected_tools import ConnectedToolExecutor, ConnectedToolRegistry
from agents.runtime.cursor_runtime import AgentRunResult
from agents.runtime.harness_events import HarnessEvent
from agents.runtime.native_tool_server import NativeToolDispatcher, _dispatch_to_host
from agents.runtime.observability import TraceContext
from agents.security.access_policy import AccessDecision, InteractionContext
from agents.security.actions import ActionRequest
from agents.security.broker import CapabilityBroker
from agents.security.flags import (
    ISOLATED_AGENT_WORLD,
    TRUSTED_DEDICATED_MACHINE,
    agent_security_mode,
    trusted_dedicated_machine_enabled,
)


class _Runtime:
    supports_resume = True

    def __init__(self) -> None:
        self.isolated_env = None
        self.entry_gate = None
        self.calls: list[tuple[Path, str]] = []

    def run(self, *, workspace, prompt, provider_session_id=None, trace=None, obs=None, on_event=None):
        self.calls.append((Path(workspace), str(prompt)))
        return AgentRunResult(
            text="done",
            provider_session_id=provider_session_id or "provider-session",
            status="succeeded",
        )


class _Output:
    def __init__(self) -> None:
        self.observed: list[tuple[str, dict]] = []

    def observe(self, event_type, text, **payload):
        self.observed.append((event_type, payload))

    def message(self, text, **payload):
        return type("Receipt", (), {"status": "succeeded"})()

    def progress(self, text, **payload):
        return type("Receipt", (), {"status": "succeeded"})()

    def question(self, text, **payload):
        return type("Receipt", (), {"status": "succeeded"})()

    def artifact(self, path, **payload):
        return type("Receipt", (), {"status": "succeeded"})()


class AgentSovereigntyM08Tests(unittest.TestCase):
    def test_security_world_defaults_to_trusted_and_preserves_explicit_isolation(self) -> None:
        self.assertEqual(TRUSTED_DEDICATED_MACHINE, agent_security_mode({}))
        self.assertTrue(trusted_dedicated_machine_enabled({}))
        self.assertEqual(
            ISOLATED_AGENT_WORLD,
            agent_security_mode({"agent_security": {"workspace_isolation_v2": True}}),
        )
        self.assertEqual(
            TRUSTED_DEDICATED_MACHINE,
            agent_security_mode({"agent_security": {"mode": "dedicated_agent_machine"}}),
        )

    def test_trusted_runner_uses_canonical_workspace_without_disposable_publish(self) -> None:
        ensure_definitions_loaded()
        definition = get_definition("mark")
        self.assertIsNotNone(definition)
        runtime = _Runtime()
        trace = TraceContext(trace_id="tr-sovereignty", project_slug="mbpass")
        with tempfile.TemporaryDirectory(prefix="lumon-m08-", dir="/tmp") as tmp, patch.dict(
            os.environ, {"LUMEN_AGENTS_HOME": str(Path(tmp) / "agents")}, clear=False
        ), patch("agents.runner.local_isolated.DisposableWorkspace.create", side_effect=AssertionError("isolated")):
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            result = TrustedAgentRunner(runtime=runtime, config={"agent_security": {"mode": TRUSTED_DEDICATED_MACHINE}}).run(
                definition=definition,
                workspace=workspace,
                prompt="inspect the real workspace",
                provider_session_id=None,
                trace=trace,
            )
            manifest_exists = (workspace / ".lumon" / "native-tools.json").is_file()
        self.assertEqual("succeeded", result.status)
        self.assertEqual(workspace.resolve(), runtime.calls[0][0])
        self.assertTrue(manifest_exists)
        self.assertIsNone(runtime.isolated_env)

    def test_native_tool_events_are_observation_only_and_never_become_replay_requests(self) -> None:
        output = _Output()
        result = type(
            "ProviderResult",
            (),
            {
                "harness_events": [
                    HarnessEvent(
                        type="tool_call",
                        provider="codex",
                        payload={"tool": "feishu.file", "arguments": {"path": "out.pdf"}},
                    )
                ]
            },
        )()
        count, _, _, requests = _publish_native_workstream_events(
            result=result,
            output=output,
            session_id="session-1",
        )
        self.assertEqual(0, count)
        self.assertEqual([], requests)
        self.assertEqual("tool.started", output.observed[0][0])

    def test_native_mcp_side_effect_is_executed_once_when_harness_replays_events(self) -> None:
        calls: list[tuple[str, dict[str, object]]] = []
        executor = ConnectedToolExecutor(
            registry=ConnectedToolRegistry(include_legacy=False),
            native_executor=lambda name, arguments, _context: calls.append((name, arguments)) or {"ok": True},
        )
        from agents.security.trusted import TrustedActionContext

        context = TrustedActionContext(
            agent_id="mark",
            project_slug="mbpass",
            actor_user_id="ou-user",
            chat_id="oc-chat",
            thread_id="ot-thread",
            source_message_id="om-message",
            trace_id="tr-exactly-once",
        )
        with tempfile.TemporaryDirectory(prefix="lumon-m08-native-") as tmp:
            dispatcher = NativeToolDispatcher(
                socket_path=Path(tmp) / "native.sock",
                executor=executor,
                context=context,
            ).start()
            try:
                _dispatch_to_host(
                    str(dispatcher.socket_path),
                    {"name": "feishu.file", "arguments": {"path": "output.pdf"}},
                )
            finally:
                dispatcher.close()

        output = _Output()
        result = type(
            "ProviderResult",
            (),
            {
                "harness_events": [
                    HarnessEvent(
                        type="tool_call",
                        provider="codex",
                        payload={"tool": "feishu.file", "arguments": {"path": "output.pdf"}},
                    ),
                    HarnessEvent(
                        type="tool_result",
                        provider="codex",
                        payload={"tool": "feishu.file", "status": "succeeded"},
                    ),
                ]
            },
        )()
        _publish_native_workstream_events(result=result, output=output, session_id="session-1")
        self.assertEqual([("feishu.send_file", {"path": "output.pdf"})], calls)

    def test_trusted_broker_uses_gate_and_does_not_apply_role_action_acl(self) -> None:
        context = InteractionContext(
            agent_id="mark",
            user_id="ou-user",
            chat_id="oc-chat",
            chat_type="group",
            thread_id="ot-thread",
            message_id="om-message",
            is_dm=False,
            trust_zone="RESTRICTED",
        )
        decision = AccessDecision(
            allowed=True,
            reason_code="ENTRY_GATE",
            trust_zone="RESTRICTED",
            host_read_allowed=False,
            mutation_allowed=True,
            effective_capabilities=frozenset(),
            context=context,
        )
        request = ActionRequest(
            agent_id="mark",
            action="delivery.start",
            project_slug="mbpass",
            actor_user_id="ou-user",
            chat_id="oc-chat",
            thread_id="ot-thread",
            source_message_id="om-message",
            trace_id="tr-sovereignty",
            entry_gate_token="gate-test",
            access_decision=decision,
        )
        with patch("agents.security.broker.is_action_allowed_for_agent", return_value=False):
            receipt = CapabilityBroker(
                config={"agent_security": {"mode": TRUSTED_DEDICATED_MACHINE}},
                executors={"delivery.start": lambda _: {"started": True}},
            ).execute(request)
        self.assertEqual("succeeded", receipt.status)


if __name__ == "__main__":
    unittest.main()
