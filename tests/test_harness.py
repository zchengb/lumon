from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from agents.runtime.final_response import extract_action_requests
from agents.runtime.harness import capabilities_for_provider, probe_harness
from agents.security.tools import host_tool_manifest


class HarnessTests(unittest.TestCase):
    def test_provider_capabilities_are_provider_neutral(self) -> None:
        codex = capabilities_for_provider("codex", mode="unshackled", sandbox=True)
        opencode = capabilities_for_provider("opencode", mode="unshackled", sandbox=True)
        open_without_provider_sandbox = capabilities_for_provider(
            "cursor", mode="unshackled", sandbox=False, task_mode="explore"
        )
        api = capabilities_for_provider("api", mode="restricted", sandbox=False)
        self.assertTrue(codex.persistent_session)
        self.assertTrue(codex.native_tools)
        self.assertTrue(codex.workspace_write)
        self.assertTrue(opencode.question)
        self.assertTrue(opencode.subagents)
        self.assertTrue(open_without_provider_sandbox.workspace_write)
        self.assertTrue(open_without_provider_sandbox.build)
        self.assertTrue(open_without_provider_sandbox.tests)
        self.assertTrue(open_without_provider_sandbox.scripts)
        self.assertTrue(open_without_provider_sandbox.subagents)
        self.assertFalse(api.workspace_write)
        self.assertFalse(api.native_tools)

    def test_probe_requires_the_disposable_boundary(self) -> None:
        with mock.patch("agents.runtime.harness._provider_check", return_value=(True, "test-provider")), mock.patch(
            "agents.runtime.codex_runtime.codex_account_status",
            return_value={"matches": True, "configured": True, "email": "kuoyio0820@gmail.com"},
        ):
            result = probe_harness(
                "codex",
                project="mbpass",
                config={
                    "agent_security": {"workspace_isolation_v2": True, "provider_sandbox": "unrestricted"},
                    "harness": {"mode": "unshackled"},
                },
                require_provider=True,
            )
        self.assertTrue(result.ready)
        self.assertEqual(result.provider, "codex")
        self.assertEqual(result.mode, "unshackled")
        self.assertEqual(result.checks["provider_sandbox_mode"], "unrestricted")
        self.assertFalse(any(result.security.values()))

    def test_native_tool_call_is_compatible_with_the_action_receipt_path(self) -> None:
        raw = '<NATIVE_TOOL_CALL>{"name":"feishu.send_file","arguments":{"path":"output/pdf/plan.pdf"}}</NATIVE_TOOL_CALL>'
        requests = extract_action_requests(raw)
        self.assertEqual(requests[0]["action"], "feishu.send_file")
        self.assertEqual(requests[0]["arguments"]["path"], "output/pdf/plan.pdf")

    def test_host_registry_is_dynamic_and_includes_delegation(self) -> None:
        names = {entry["name"] for entry in host_tool_manifest()}
        self.assertIn("agent.delegate", names)
        self.assertIn("test_case.generate", names)
        self.assertIn("feishu.send_file", names)


if __name__ == "__main__":
    unittest.main()
