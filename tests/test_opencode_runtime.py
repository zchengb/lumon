from __future__ import annotations

import json
import sys
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


if __name__ == "__main__":
    unittest.main()
