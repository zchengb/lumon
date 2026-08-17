from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from agents.runtime.cursor_runtime import create_agent_runtime  # noqa: E402
from agents.runtime.opencode_runtime import OpenCodeAgentRuntime, parse_opencode_json_text  # noqa: E402


class OpenCodeRuntimeTests(unittest.TestCase):
    def test_parser_collects_session_text_and_tools(self) -> None:
        payload = "\n".join(
            json.dumps(event)
            for event in (
                {"type": "step_start", "sessionID": "ses-1"},
                {"type": "tool_use", "sessionID": "ses-1", "part": {"type": "tool", "tool": "read", "callID": "call-1"}},
                {"type": "text", "sessionID": "ses-1", "part": {"type": "text", "text": "OK"}},
                {"type": "step_finish", "sessionID": "ses-1"},
            )
        )
        result = parse_opencode_json_text(payload)
        self.assertEqual("ses-1", result.provider_session_id)
        self.assertEqual("OK", result.text)
        self.assertEqual("succeeded", result.status)
        self.assertEqual("read", result.tool_events[0].tool_type)

    def test_factory_routes_deepseek_alias_to_opencode(self) -> None:
        runtime = create_agent_runtime(provider="deepseek", model="deepseek-v4-flash")
        self.assertIsInstance(runtime, OpenCodeAgentRuntime)
        self.assertTrue(runtime.supports_resume)

    def test_deepseek_runtime_uses_max_reasoning_effort(self) -> None:
        config = json.loads(OpenCodeAgentRuntime(model="deepseek-v4-flash", base_url="https://api.deepseek.com", api_key_env="DEEPSEEK_API_KEY")._config_content())
        model = config["provider"]["deepseek"]["models"]["deepseek-v4-flash"]
        self.assertEqual("max", model["options"]["reasoningEffort"])

    def test_local_qwen_runtime_uses_openai_compatible_provider_without_key(self) -> None:
        runtime = OpenCodeAgentRuntime(
            model="qwen/qwen3.8-27b-mlx",
            base_url="http://127.0.0.1:1234/v1",
            api_key_env="",
        )
        config = json.loads(runtime._config_content())
        self.assertEqual("qwen/qwen3.8-27b-mlx", config["model"])
        self.assertEqual("http://127.0.0.1:1234/v1", config["provider"]["qwen"]["options"]["baseURL"])
        self.assertEqual("local", config["provider"]["qwen"]["options"]["apiKey"])
        self.assertEqual({}, config["provider"]["qwen"]["models"]["qwen3.8-27b-mlx"]["options"])

    def test_workspace_context_contains_readable_safety_files(self) -> None:
        runtime = OpenCodeAgentRuntime(agent_id="mark")
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            runtime._ensure_workspace_context(workspace)
            self.assertTrue((workspace / ".lumon" / "blacklist.md").is_file())
            self.assertTrue((workspace / ".lumon" / "responsibilities" / "mark.md").is_file())
            self.assertTrue((workspace / ".lumon" / "protocol.md").is_file())
            self.assertIn("Common hard blacklist", (workspace / ".lumon" / "blacklist.md").read_text(encoding="utf-8"))

    def test_hard_timeout_discards_partial_text(self) -> None:
        class Stream:
            def __init__(self, line: str = "") -> None:
                self.line = line

            def readline(self) -> str:
                line, self.line = self.line, ""
                return line

            def read(self) -> str:
                return ""

        class Process:
            def __init__(self) -> None:
                self.stdout = Stream(json.dumps({"type": "text", "part": {"type": "text", "text": "partial"}}) + "\n")
                self.stderr = Stream()

            def terminate(self) -> None:
                pass

            def wait(self, timeout: int = 0) -> None:
                pass

            def kill(self) -> None:
                pass

            def poll(self) -> None:
                return None

        runtime = OpenCodeAgentRuntime(hard_timeout_seconds=1)
        process = Process()
        clock = iter((0.0, 0.0, 2.0, 2.0))
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(runtime, "_env", return_value={}):
                with mock.patch.object(runtime, "_agent_bin", return_value="opencode"):
                    with mock.patch("agents.runtime.opencode_runtime.subprocess.Popen", return_value=process):
                        with mock.patch("agents.runtime.opencode_runtime.select.select", return_value=([process.stdout], [], [])):
                            with mock.patch(
                                "agents.runtime.opencode_runtime.time.time",
                                side_effect=lambda: next(clock, 2.0),
                            ):
                                result = runtime.run(workspace=Path(tmp), prompt="test")
        self.assertEqual("timed_out", result.status)
        self.assertEqual("", result.text)

    def test_jira_read_grant_allows_only_the_matching_direct_twg_verb(self) -> None:
        runtime = OpenCodeAgentRuntime(
            agent_id="milchick",
            jira_read_actions=frozenset({"jira.workitem.get"}),
        )
        bash = runtime._permission_config()["bash"]
        self.assertEqual("allow", bash["twg jira workitem get *"])
        self.assertNotIn("twg jira workitem query *", bash)
        self.assertNotIn("twg jira workitem create *", bash)
        self.assertNotIn("twg jira workitem update *", bash)
        self.assertNotIn("twg jira workitem get *", OpenCodeAgentRuntime()._permission_config()["bash"])


if __name__ == "__main__":
    unittest.main()
