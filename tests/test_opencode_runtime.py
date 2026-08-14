from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

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

    def test_workspace_context_contains_readable_safety_files(self) -> None:
        runtime = OpenCodeAgentRuntime(agent_id="mark")
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            runtime._ensure_workspace_context(workspace)
            self.assertTrue((workspace / ".lumon" / "blacklist.md").is_file())
            self.assertTrue((workspace / ".lumon" / "responsibilities" / "mark.md").is_file())
            self.assertTrue((workspace / ".lumon" / "protocol.md").is_file())
            self.assertIn("Common hard blacklist", (workspace / ".lumon" / "blacklist.md").read_text(encoding="utf-8"))

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
