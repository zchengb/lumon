#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from agents.runtime.cursor_runtime import CursorAgentRuntime
from agents.security.actions import ActionRequest
from agents.security.authorization import is_mutation_authorized
from agents.security.broker import CapabilityBroker
from agents.security.env import build_agent_env, env_contains_secrets
from agents.security.preflight import run_security_check
from agents.security.resources import assert_within_workspace, is_forbidden_host_path


class AgentSecurityTests(unittest.TestCase):
    def test_runtime_defaults_use_the_agent_world_boundary(self) -> None:
        runtime = CursorAgentRuntime()
        self.assertEqual(runtime.sandbox, "unrestricted")
        self.assertFalse(runtime.force)
        self.assertEqual(CursorAgentRuntime(sandbox="disabled").sandbox, "unrestricted")
        self.assertEqual(CursorAgentRuntime(force=True).sandbox, "unrestricted")

    def test_agent_env_isolates_secrets(self) -> None:
        source = {
            "PATH": "/usr/bin",
            "HOME": "/tmp",
            "CURSOR_API_KEY": "cursor-key",
            "FEISHU_MARK_APP_SECRET": "mark-secret",
            "FEISHU_DYLAN_APP_SECRET": "dylan-secret",
            "JIRA_TOKEN": "jira",
            "GITHUB_TOKEN": "gh",
            "AWS_SECRET_ACCESS_KEY": "aws",
            "SSH_AUTH_SOCK": "/tmp/ssh.sock",
        }
        env = build_agent_env(agent_id="dylan", project="mbpass", source=source)
        self.assertEqual(env.get("CURSOR_API_KEY"), "cursor-key")
        self.assertEqual(env.get("LUMEN_AGENT_ID"), "dylan")
        self.assertNotIn("FEISHU_MARK_APP_SECRET", env)
        self.assertNotIn("JIRA_TOKEN", env)
        self.assertNotIn("GITHUB_TOKEN", env)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", env)
        self.assertEqual(env_contains_secrets(env), [])

    def test_host_paths_denied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "ok.txt").write_text("ok\n", encoding="utf-8")
            assert_within_workspace(workspace / "ok.txt", workspace)
            with self.assertRaises(PermissionError):
                assert_within_workspace(Path.home() / "Desktop" / "1.png", workspace)
            self.assertTrue(is_forbidden_host_path(Path.home() / ".ssh" / "id_rsa"))
            self.assertTrue(is_forbidden_host_path(Path.home() / "Library" / "LaunchAgents" / "evil.plist"))
            link = workspace / "escape"
            try:
                link.symlink_to(Path.home() / "Desktop")
            except OSError:
                self.skipTest("symlink unavailable")
            with self.assertRaises(PermissionError):
                assert_within_workspace(link, workspace)

    def test_unknown_action_denied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            receipt = CapabilityBroker(config={"access": {"mutation_allowed_user_ids": ["ou_owner"]}}).execute(
                ActionRequest(
                    agent_id="dylan",
                    action="filesystem.delete",
                    project_slug="mbpass",
                    actor_user_id="ou_owner",
                    chat_id="oc1",
                    thread_id="",
                    source_message_id="om1",
                    trace_id="tr1",
                    explicit_authorization=True,
                )
            )
            self.assertEqual(receipt.status, "denied")
            self.assertEqual(receipt.error_code, "CAPABILITY_DENIED")

    def test_mutation_policy_fail_closed(self) -> None:
        self.assertFalse(
            is_mutation_authorized(
                user_id="ou_anyone",
                chat_id="oc1",
                action="risk.resolve",
                config={"access": {}},
            )
        )
        self.assertTrue(
            is_mutation_authorized(
                user_id="ou_owner",
                chat_id="oc1",
                action="risk.resolve",
                config={"access": {"mutation_allowed_user_ids": ["ou_owner"]}},
            )
        )
        self.assertFalse(
            is_mutation_authorized(
                user_id="ou_guest",
                chat_id="oc1",
                action="delivery.start",
                config={"access": {"mutation_allowed_user_ids": ["ou_owner"]}},
            )
        )

    def test_security_check_passes_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            with mock.patch("agents.security.preflight._cursor_available", return_value=True):
                result = run_security_check(agent_id="dylan", project="mbpass", config={"access": {}})
            self.assertEqual(result["status"], "pass")
            self.assertTrue(result["sandbox"])
            self.assertEqual(result["workspace_escape"], "blocked")
            self.assertEqual(result["host_write"], "blocked")
            self.assertEqual(result["secret_env"], "isolated")
            self.assertEqual(result["broker"], "active")


if __name__ == "__main__":
    unittest.main()
