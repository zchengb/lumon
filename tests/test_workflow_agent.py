from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
import sys

if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))


spec = importlib.util.spec_from_file_location("workflow_agent", LIB / "scripts" / "run-workflow-agent.py")
assert spec and spec.loader
workflow_agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow_agent)


class WorkflowAgentTests(unittest.TestCase):
    def test_resolve_config_uses_global_provider_for_every_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "config").mkdir()
            (workspace / "config" / "common.json").write_text(json.dumps({"execution": {"provider": "deepseek", "model": "deepseek-v4-flash"}}), encoding="utf-8")
            (workspace / "config" / "delivery.json").write_text(json.dumps({"execution": {"provider": "deepseek", "model": "deepseek-v4-pro", "patch_provider": "openai_compatible", "patch_model": "gpt-test"}}), encoding="utf-8")
            self.assertEqual("deepseek", workflow_agent.resolve_config(workspace, "auto_scan")["provider"])
            self.assertEqual("deepseek-v4-flash", workflow_agent.resolve_config(workspace, "auto_delivery")["model"])
            self.assertEqual("deepseek", workflow_agent.resolve_config(workspace, "auto_patch")["provider"])
            self.assertEqual("deepseek-v4-flash", workflow_agent.resolve_config(workspace, "auto_patch")["model"])

    def test_resolve_config_keeps_legacy_delivery_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "config").mkdir()
            (workspace / "config" / "delivery.json").write_text(json.dumps({"execution": {"provider": "deepseek", "model": "deepseek-v4-pro", "patch_provider": "openai_compatible", "patch_model": "gpt-test"}}), encoding="utf-8")
            self.assertEqual("deepseek-v4-pro", workflow_agent.resolve_config(workspace, "auto_delivery")["model"])
            self.assertEqual("openai_compatible", workflow_agent.resolve_config(workspace, "auto_patch")["provider"])
            self.assertEqual("gpt-test", workflow_agent.resolve_config(workspace, "auto_patch")["model"])

    def test_api_runtime_executes_tool_then_returns_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "lumon"
            workspace.mkdir(parents=True)
            first = {"id": "req-1", "choices": [{"message": {"role": "assistant", "tool_calls": [{"id": "call-1", "type": "function", "function": {"name": "write_file", "arguments": json.dumps({"path": "repo/result.txt", "content": "done"})}}]}}]}
            second = {"id": "req-2", "choices": [{"message": {"role": "assistant", "content": "Finished the change."}}]}
            args = SimpleNamespace(
                workspace=workspace,
                agent_id="mark",
                project="test",
                prompt="make the change",
                output_format="stream-json",
                timeout=5,
            )
            output = io.StringIO()
            with mock.patch.object(workflow_agent, "chat_completion_messages", side_effect=[(first, "req-1"), (second, "req-2")]), contextlib.redirect_stdout(output):
                self.assertEqual(0, workflow_agent.run_api({"provider": "deepseek", "model": "deepseek-v4-flash", "base_url": "", "api_key_env": ""}, args))
            self.assertEqual("done", (workspace.parent / "repo" / "result.txt").read_text(encoding="utf-8"))
            self.assertIn('"subtype": "started"', output.getvalue())
            self.assertIn("Finished the change.", output.getvalue())

    def test_provider_aliases_are_normalized(self) -> None:
        self.assertEqual("cursor_cli", workflow_agent.normalize_provider("cursor"))
        self.assertEqual("deepseek", workflow_agent.normalize_provider("deepseek_api"))
        self.assertEqual("openai_compatible", workflow_agent.normalize_provider("openai"))


if __name__ == "__main__":
    unittest.main()
