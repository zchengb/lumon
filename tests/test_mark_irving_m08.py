#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
SCRIPTS = LIB / "scripts"
for item in (LIB, SCRIPTS):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from agents.definitions import ensure_definitions_loaded, get_definition
from agents.dylan.permission_policy import write_workspace_write_permission_profile
from agents.irving.session_bootstrap import build_bootstrap_prompt as build_irving_prompt
from agents.mark.session_bootstrap import build_bootstrap_prompt as build_mark_prompt
from agents.runtime.autonomous import _action_results_need_continuation
from agents.runtime.interaction import action_missing_fields, normalize_conversation_decision
from agents.security.tools import host_tool_specs


class MarkIrvingM08Tests(unittest.TestCase):
    def test_mark_and_irving_are_write_capable(self) -> None:
        ensure_definitions_loaded()
        mark = get_definition("mark")
        irving = get_definition("irving")
        assert mark is not None and irving is not None
        for definition in (mark, irving):
            self.assertTrue(definition.capabilities.direct_workspace_write)
            self.assertEqual("workspace_write", definition.capabilities.filesystem_mode)
            self.assertEqual("workspace_write", definition.permission_profile)

    def test_prompts_prefer_natural_output_and_native_editing(self) -> None:
        mark_prompt = build_mark_prompt(
            project_slug="mbpass",
            workspace_path="/tmp/mbpass",
            user_message="把版本更新到 6.0",
        )
        irving_prompt = build_irving_prompt(
            project_slug="mbpass",
            workspace_path="/tmp/mbpass",
            user_message="把版本更新到 6.0",
        )
        self.assertIn("native Read/Edit/Shell/Build/Test", mark_prompt)
        self.assertIn("feishu.say", mark_prompt)
        self.assertNotIn("Never modify business source code", mark_prompt)
        self.assertNotIn("internal host execution channel", mark_prompt)
        self.assertIn("native tools", irving_prompt)
        self.assertIn("feishu.say", irving_prompt)
        self.assertNotIn("hidden delivery worker", irving_prompt.lower())
        self.assertNotIn("ACTION_REQUEST", mark_prompt)
        self.assertNotIn("ACTION_REQUEST", irving_prompt)

    def test_feishu_say_is_canonical_and_minimal(self) -> None:
        names = {item.name for item in host_tool_specs()}
        self.assertIn("feishu.say", names)
        self.assertEqual([], action_missing_fields("feishu.say", arguments={"message": "已找到原因"}))
        self.assertEqual(["message"], action_missing_fields("feishu.say", arguments={}))

    def test_action_results_continue_unless_explicitly_terminal(self) -> None:
        self.assertTrue(
            _action_results_need_continuation(
                [{"action": "jira.workitem.get", "status": "succeeded", "result": {"issue_key": "MBPAS-1"}}]
            )
        )
        self.assertTrue(
            _action_results_need_continuation(
                [{"action": "new.future.action", "status": "failed", "result": {"code": "E_FAIL"}}]
            )
        )
        self.assertFalse(
            _action_results_need_continuation(
                [{"action": "deployment.start", "status": "succeeded", "result": {"started": True, "detached": True}}]
            )
        )

    def test_suppress_final_reply_is_agent_owned_metadata(self) -> None:
        decision = normalize_conversation_decision(
            {
                "mode": "normal",
                "route": "answer",
                "suppress_final_reply": True,
            }
        )
        self.assertIsNotNone(decision)
        self.assertTrue(decision["suppress_final_reply"])

    def test_workspace_write_profile_keeps_secret_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_workspace_write_permission_profile(Path(tmp))
            permissions = json.loads(path.read_text(encoding="utf-8"))["permissions"]
            self.assertIn("Write(**)", permissions["allow"])
            self.assertNotIn("Write(**)", permissions["deny"])
            self.assertIn("Read(**/.env*)", permissions["deny"])
            self.assertIn("Shell(git push)", permissions["deny"])


if __name__ == "__main__":
    unittest.main()
