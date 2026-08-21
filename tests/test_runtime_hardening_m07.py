from __future__ import annotations

import os
import platform
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.runner.agent_world import AgentWorld, build_sandbox_profile, probe_agent_world
from agents.runner.certification import certify_provider
from agents.runner.service_identity import provision_service_identity, service_identity_status
from agents.runtime.connected_tools import ConnectedToolExecutor, ConnectedToolRegistry
from agents.runtime.native_tool_bridge import native_tool_manifest
from agents.runtime.native_tool_server import NativeToolDispatcher, _dispatch_to_host, handle
from agents.runtime.session_host import AgentSessionHost
from agents.security.access_policy import AccessDecision, InteractionContext, issue_entry_gate, resolve_entry_gate
from agents.security.actions import ActionRequest
from agents.security.broker import CapabilityBroker
from agents.security.trusted import bind_action_request, trusted_context_from_meta


class RuntimeHardeningM07Tests(unittest.TestCase):
    def _decision(self) -> AccessDecision:
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
        return AccessDecision(
            allowed=True,
            reason_code="ALLOWED",
            trust_zone="RESTRICTED",
            host_read_allowed=False,
            mutation_allowed=True,
            effective_capabilities=frozenset(),
            exposure_mode="restricted_team",
            context=context,
        )

    def test_profile_explicitly_denies_canonical_path(self) -> None:
        profile = build_sandbox_profile(
            operator_home=Path("/Users/operator"),
            canonical=Path("/workspace/canonical"),
            world_root=Path("/Users/operator/.lumon/world"),
            workspace=Path("/tmp/world/workspace"),
            service_home=Path("/Users/operator/.lumon/world/home"),
            tmp=Path("/Users/operator/.lumon/world/tmp"),
        )
        self.assertIn('(deny file-read* (subpath "/workspace/canonical"))', profile)
        self.assertIn('(deny file-write* (subpath "/workspace/canonical"))', profile)
        self.assertIn('(allow process-exec*)', profile)
        self.assertIn('(allow network*)', profile)

    def test_world_probe_and_static_certification_have_stable_contract(self) -> None:
        probe = probe_agent_world(agent_id="ci")
        self.assertEqual("agent-world/1", probe["contract"])
        self.assertEqual("host_only", probe["checks"]["canonical_access"])
        report = certify_provider("codex", agent_id="ci", live=False)
        self.assertEqual("agent-world/1", report["contract"])
        self.assertIn("canonical_write", report)
        self.assertIn("secret_read", report)

    @unittest.skipUnless(platform.system() == "Darwin", "sandbox-exec certification is macOS-specific")
    def test_live_world_allows_layer_and_blocks_canonical(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lumon-m07-test-") as tmp:
            root = Path(tmp).resolve()
            canonical = root / "canonical"
            workspace = root / "workspace"
            canonical.mkdir()
            workspace.mkdir()
            (canonical / "protected.txt").write_text("protected", encoding="utf-8")
            world = AgentWorld.create(canonical=canonical, workspace=workspace, agent_id="test", require_boundary=True)
            try:
                import subprocess

                env = world.environment(project="test")
                allowed = subprocess.run(world.command(["/bin/sh", "-c", "printf ok > allowed.txt"]), cwd=workspace, env=env, check=False)
                denied = subprocess.run(world.command(["/bin/sh", "-c", f"cat {canonical / 'protected.txt'}"]), cwd=workspace, env=env, check=False)
                self.assertEqual(0, allowed.returncode)
                self.assertNotEqual(0, denied.returncode)
            finally:
                world.close()

    def test_service_identity_never_reports_personal_copy(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lumon-identity-") as tmp:
            identity = provision_service_identity("mark", provider="codex", root=Path(tmp))
            status = service_identity_status("mark", provider="codex", root=Path(tmp))
            self.assertTrue(identity.provisioned)
            self.assertFalse(status["personal_credentials_copied"])
            self.assertEqual("agent:mark", status["service_identity"])

    def test_native_manifest_has_no_legacy_conversation_tools(self) -> None:
        manifest = native_tool_manifest(provider="codex")
        names = {item["name"] for item in manifest["tools"]}
        self.assertEqual("lumon-native-tools/1", manifest["protocol"])
        self.assertIn("feishu.file", names)
        self.assertNotIn("feishu.say", names)
        self.assertNotIn("agent.delegate", names)
        self.assertTrue(all(item["authorization_class"] == "entry_gate" for item in manifest["tools"]))

    def test_entry_gate_is_carried_without_reauthorizing_the_broker(self) -> None:
        decision = self._decision()
        meta = {"user_id": "ou-user", "chat_id": "oc-chat", "thread_id": "ot-thread", "message_id": "om-message"}
        gate = issue_entry_gate(agent_id="mark", meta=meta, decision=decision)
        self.assertIsNotNone(resolve_entry_gate(gate.token, agent_id="mark", meta=meta))
        context = trusted_context_from_meta(
            agent_id="mark",
            project_slug="mbpass",
            meta={**meta, "_entry_gate_token": gate.token, "chat_type": "group"},
            trace_id="tr-test",
            access_decision=decision,
        )
        request = bind_action_request(context=context, action="jira.workitem.get", arguments={"issue_key": "MBPAS-1"})
        self.assertTrue(context.gate_only)
        self.assertEqual(gate.token, request.entry_gate_token)

        calls: list[str] = []
        broker = CapabilityBroker(executors={"jira.workitem.get": lambda item: calls.append(item.action) or {"ok": True}})
        with patch("agents.security.access_policy.authorize_agent_interaction", side_effect=AssertionError("re-authorized")):
            receipt = broker.execute(request)
        self.assertEqual("succeeded", receipt.status)
        self.assertEqual(["jira.workitem.get"], calls)

    def test_native_stdio_call_uses_gate_context(self) -> None:
        seen = []

        def native(name, arguments, context):
            seen.append((name, context.gate_only, arguments))
            return {"status": "succeeded"}

        executor = ConnectedToolExecutor(registry=ConnectedToolRegistry(include_legacy=False), native_executor=native)
        env = {
            "LUMON_ENTRY_GATE_TOKEN": "gate-child",
            "LUMEN_AGENT_ID": "mark",
            "LUMON_GATE_USER_ID": "ou-user",
            "LUMON_GATE_CHAT_ID": "oc-chat",
            "LUMON_GATE_THREAD_ID": "ot-thread",
            "LUMON_GATE_MESSAGE_ID": "om-message",
            "LUMON_GATE_ALLOWED": "1",
            "LUMON_GATE_TRUST_ZONE": "RESTRICTED",
            "LUMON_GATE_CHAT_TYPE": "group",
            "LUMON_GATE_IS_DM": "0",
        }
        with patch.dict(os.environ, env, clear=False):
            result = handle(
                {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "feishu.file", "arguments": {"path": "report.pdf"}}},
                executor=executor,
            )
        self.assertIn("result", result)
        self.assertTrue(seen[0][1])
        self.assertEqual("feishu.send_file", seen[0][0])

    def test_native_tool_dispatcher_keeps_external_effect_in_host(self) -> None:
        decision = self._decision()
        context = trusted_context_from_meta(
            agent_id="mark",
            project_slug="mbpass",
            meta={
                "user_id": "ou-user",
                "chat_id": "oc-chat",
                "thread_id": "ot-thread",
                "message_id": "om-message",
                "chat_type": "group",
                "_entry_gate_token": "gate-host",
            },
            trace_id="tr-host",
            access_decision=decision,
        )
        seen = []
        executor = ConnectedToolExecutor(
            registry=ConnectedToolRegistry(include_legacy=False),
            native_executor=lambda name, arguments, bound: seen.append((name, bound.agent_id)) or {"status": "ok"},
        )
        with tempfile.TemporaryDirectory(prefix="lumon-dispatch-") as tmp:
            dispatcher = NativeToolDispatcher(
                socket_path=Path(tmp) / "native.sock",
                executor=executor,
                context=context,
            ).start()
            try:
                result = _dispatch_to_host(
                    str(dispatcher.socket_path),
                    {"name": "feishu.file", "arguments": {"path": "report.pdf"}},
                )
            finally:
                dispatcher.close()
        self.assertEqual({"status": "ok"}, result)
        self.assertEqual([("feishu.send_file", "mark")], seen)

    def test_session_host_waiting_question_has_owner_and_resume(self) -> None:
        host = AgentSessionHost()
        try:
            host.register(session_id="sess-m07", agent_id="mark", thread_id="thread-m07")
            host.start(
                "sess-m07",
                event={"text": "start"},
                runner=lambda event, state: {
                    "status": "waiting_human",
                    "question_id": "q-1",
                    "question": "Choose A or B",
                },
            )
            state = host.state("sess-m07")
            self.assertEqual("q-1", state.waiting_for["question_id"])
            host.resume_human(
                "sess-m07",
                question_id="q-1",
                answer="A",
                runner=lambda event, state: {"status": "completed", "provider_session_id": "provider-1"},
            )
            self.assertEqual("completed", host.state("sess-m07").state)
        finally:
            host.close()


if __name__ == "__main__":
    unittest.main()
