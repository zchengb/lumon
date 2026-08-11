from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "lib" / "scripts"))

from deployment_tracking import normalized_config, poll_github, prepare_tracking


class DeploymentTrackingTests(unittest.TestCase):
    def test_provider_config_is_normalized_without_secrets(self) -> None:
        config = normalized_config(
            {
                "deployment_tracking": {
                    "enabled": True,
                    "provider": "github_actions",
                    "poll_interval_seconds": 1,
                    "github_actions": {"repository": "acme/app", "workflow": "deploy.yml"},
                }
            }
        )
        self.assertTrue(config["enabled"])
        self.assertEqual(5, config["poll_interval_seconds"])
        self.assertEqual("acme/app", config["github_actions"]["repository"])
        self.assertNotIn("token", json.dumps(config).lower())

    def test_prepare_tracking_moves_published_result_to_awaiting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result_path = Path(directory) / "result.json"
            result_path.write_text(
                json.dumps(
                    {
                        "run_id": "quick-1",
                        "status": "completed",
                        "delivery_status": "completed",
                        "commits": [{"sha": "abc123"}],
                        "pr_urls": [],
                    }
                ),
                encoding="utf-8",
            )
            deployment = prepare_tracking(
                result_path,
                normalized_config({"deployment_tracking": {"enabled": True, "provider": "jenkins", "jenkins": {"job": "deploy"}}}),
                "quick_change",
            )
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual("queued", deployment["status"] if deployment else None)
            self.assertEqual("awaiting_deploy", payload["delivery_status"])
            self.assertEqual("abc123", payload["deployment"]["commit_sha"])

    def test_github_actions_completed_success_is_normalized(self) -> None:
        original_run = subprocess.run

        def fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(
                args[0],
                0,
                stdout=json.dumps(
                    [
                        {
                            "databaseId": 42,
                            "status": "completed",
                            "conclusion": "success",
                            "url": "https://github.example/run/42",
                            "workflowName": "Deploy",
                            "headSha": "abc123",
                            "headBranch": "main",
                        }
                    ]
                ),
                stderr="",
            )

        try:
            subprocess.run = fake_run
            result = poll_github(
                normalized_config({"deployment_tracking": {"enabled": True, "provider": "github_actions", "github_actions": {"repository": "acme/app"}}}),
                {"commit_sha": "abc123"},
            )
        finally:
            subprocess.run = original_run
        self.assertEqual("succeeded", result["status"])
        self.assertEqual("42", result["run_id"])


if __name__ == "__main__":
    unittest.main()
