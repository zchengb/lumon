#!/usr/bin/env python3
from __future__ import annotations

import sys
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from agents.role_policy import (
    build_role_guidance,
    has_role_policy,
    load_common_blacklist,
    load_role_policy,
    responsibility_document,
)
from agents.security.actions import ActionRequest
from agents.security.broker import CapabilityBroker
from agents.security.policy import is_action_allowed_for_agent, is_action_known
from agents.security.resources import is_forbidden_host_path


class RolePolicyTests(unittest.TestCase):
    def test_all_registered_agents_have_documented_responsibility(self) -> None:
        for agent_id in ("milchick", "mark", "dylan", "irving"):
            policy = load_role_policy(agent_id)
            self.assertTrue(has_role_policy(agent_id))
            self.assertIn("## Owns", policy.text)
            self.assertIn("## Forbidden actions", policy.text)
            self.assertTrue(policy.forbidden_actions)

    def test_agent_ownership_is_a_negative_document_blacklist(self) -> None:
        self.assertTrue(is_action_allowed_for_agent("milchick", "test_case.generate"))
        self.assertFalse(is_action_allowed_for_agent("milchick", "delivery.quick_change"))
        self.assertTrue(is_action_allowed_for_agent("mark", "delivery.quick_change"))
        self.assertTrue(is_action_allowed_for_agent("mark", "loop.business"))
        self.assertTrue(is_action_allowed_for_agent("mark", "loop.technical"))
        self.assertFalse(is_action_allowed_for_agent("mark", "test_case.generate"))
        self.assertTrue(is_action_allowed_for_agent("dylan", "jira.workitem.query"))
        self.assertTrue(is_action_allowed_for_agent("irving", "jira.workitem.update"))
        self.assertFalse(is_action_allowed_for_agent("unknown", "test_case.generate"))

    def test_unknown_actions_remain_unknown_and_guidance_includes_blacklist(self) -> None:
        self.assertFalse(is_action_known("filesystem.delete"))
        guidance = build_role_guidance("milchick")
        self.assertIn("responsibility document", guidance)
        self.assertIn("never attempt to bypass them", guidance)
        self.assertIn("Delete, move, or overwrite files outside", load_common_blacklist())
        self.assertIn("original user", responsibility_document("milchick"))

    def test_broker_enforces_role_blacklist_before_executor(self) -> None:
        calls: list[str] = []

        def executor(_request: ActionRequest) -> dict[str, str]:
            calls.append("called")
            return {"status": "unexpected"}

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"LUMEN_AGENTS_HOME": tmp}):
                receipt = CapabilityBroker(
                    config={"access": {}},
                    executors={"delivery.quick_change": executor},
                ).execute(
                    ActionRequest(
                        agent_id="milchick",
                        action="delivery.quick_change",
                        project_slug="mbpass",
                        actor_user_id="ou_owner",
                        chat_id="oc1",
                        thread_id="",
                        source_message_id="om1",
                        trace_id="tr1",
                        arguments={"chat_type": "group"},
                    )
                )

        self.assertEqual(receipt.status, "denied")
        self.assertEqual(receipt.error_code, "CAPABILITY_DENIED")
        self.assertIn("responsibility document", receipt.error or "")
        self.assertEqual(calls, [])

    def test_lumon_state_is_a_forbidden_host_root(self) -> None:
        self.assertTrue(is_forbidden_host_path(Path.home() / ".lumon" / "agents" / "config.json"))


if __name__ == "__main__":
    unittest.main()
