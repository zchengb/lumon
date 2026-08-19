#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from agents.soul_store import apply_agent_settings, agents_settings_payload, load_agent_soul
from agents.dylan.soul_loader import load_soul as load_dylan_soul


class AgentSettingsTests(unittest.TestCase):
    def test_save_soul_override_and_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            before = agents_settings_payload()
            self.assertFalse(before["enabled"])
            dylan = next(agent for agent in before["agents"] if agent["id"] == "dylan")
            self.assertTrue(dylan["soul"])
            self.assertEqual(dylan["soul_source"], "packaged")
            payload = apply_agent_settings(
                {
                    "enabled": True,
                    "access": {
                        "default_policy": "deny",
                        "allowed_chat_ids": ["oc_abcdef0123456789abcdef0123456789"],
                        "allowed_user_ids": ["ou_abcdef0123456789abcdef0123456789"],
                    },
                    "agents": [
                        {
                            "id": "dylan",
                            "conversation_enabled": True,
                            "model": "cursor-grok-4.5-medium",
                            "soft_timeout_seconds": 80,
                            "hard_timeout_seconds": 240,
                            "reaction_enabled": False,
                            "max_concurrent_jobs": 2,
                            "soul_version": "5",
                            "soul": "# Dylan override\n\nBe concise.\n",
                            "role": "scan",
                            "workflow": "auto_scan",
                        },
                        {
                            "id": "mark",
                            "conversation_enabled": True,
                            "model": "cursor-grok-4.5-medium",
                            "soft_timeout_seconds": 90,
                            "hard_timeout_seconds": 300,
                            "reaction_enabled": True,
                            "max_concurrent_jobs": 3,
                            "soul_version": "2",
                            "soul": "# Mark override\n\nStay calm.\n",
                            "role": "delivery",
                            "workflow": "auto_delivery",
                        },
                        {
                            "id": "irving",
                            "conversation_enabled": False,
                            "model": "cursor-grok-4.5-medium",
                            "soul_version": "1",
                            "soul": "# Irving override\n\nBe exact.\n",
                            "role": "patch",
                            "workflow": "auto_patch",
                        },
                        {
                            "id": "milchick",
                            "conversation_enabled": False,
                            "model": "cursor-grok-4.5-medium",
                            "soul_version": "1",
                            "soul": "# Milchick override\n\nStay composed.\n",
                            "role": "orchestrator",
                            "workflow": "operations",
                        },
                    ],
                }
            )
            self.assertTrue(payload["enabled"])
            self.assertEqual("deny", payload["access"]["default_policy"])
            self.assertEqual(
                ["oc_abcdef0123456789abcdef0123456789"],
                payload["access"]["allowed_chat_ids"],
            )
            dylan_after = next(agent for agent in payload["agents"] if agent["id"] == "dylan")
            self.assertTrue(dylan_after["conversation_enabled"])
            self.assertEqual(dylan_after["soft_timeout_seconds"], 80)
            self.assertFalse(dylan_after["reaction_enabled"])
            self.assertEqual(dylan_after["soul_source"], "override")
            self.assertIn("Dylan override", dylan_after["soul"])
            text, source = load_agent_soul("dylan")
            self.assertEqual(source, "override")
            self.assertIn("Dylan override", text)
            self.assertIn("Dylan override", load_dylan_soul())

    def test_save_feishu_credentials_to_env_local(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            os.environ["LUMEN_HOME"] = tmp
            apply_agent_settings(
                {
                    "enabled": True,
                    "agents": [
                        {
                            "id": "mark",
                            "conversation_enabled": True,
                            "model": "cursor-grok-4.5-medium",
                            "app_id": "cli_test_mark",
                            "app_secret": "secret_mark_value",
                            "soul": "# Mark\n",
                            "role": "delivery",
                            "workflow": "auto_delivery",
                        },
                        {
                            "id": "dylan",
                            "conversation_enabled": True,
                            "model": "cursor-grok-4.5-medium",
                            "soul": "# Dylan\n",
                            "role": "scan",
                            "workflow": "auto_scan",
                        },
                    ],
                }
            )
            payload = agents_settings_payload()
            mark = next(agent for agent in payload["agents"] if agent["id"] == "mark")
            self.assertEqual(mark["app_id"], "cli_test_mark")
            self.assertTrue(mark["app_secret_configured"])
            env_text = (Path(tmp) / ".env.local").read_text(encoding="utf-8")
            self.assertIn("FEISHU_MARK_APP_ID=cli_test_mark", env_text)
            self.assertIn("FEISHU_MARK_APP_SECRET=secret_mark_value", env_text)


if __name__ == "__main__":
    unittest.main()
