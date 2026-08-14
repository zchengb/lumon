from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

LIB_DIR = Path(__file__).resolve().parents[1] / "lib" / "scripts"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

import finalize_delivery as finalize  # noqa: E402
import write_delivery_failure as failure_writer  # noqa: E402
from delivery_result_merge import merge_repos_touched  # noqa: E402


class FinalizeDeliveryTests(unittest.TestCase):
    def test_commit_subject_normalizes_agent_subject_to_lumon_format(self) -> None:
        result = {
            "repos_touched": [
                {"name": "mbpass-app", "commit_subject": "feat: add article recommendations"},
            ]
        }
        self.assertEqual(
            "[lumon] #MBPAS-1503 feat: add article recommendations",
            finalize.commit_subject(result, "mbpass-app", "MBPAS-1503"),
        )

    def test_publish_retriable_detects_transient_errors(self) -> None:
        self.assertTrue(finalize.publish_retriable("git push failed: connection reset by peer"))
        self.assertFalse(finalize.publish_retriable("Agent did not provide commit_subject for mbpass-app"))

    def test_open_pr_with_retry_succeeds_on_second_attempt(self) -> None:
        repo = Path("/tmp/repo")
        calls = {"count": 0}

        def fake_open_pr(*_args, **_kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("mbpass-app: git push failed: connection reset by peer")
            return "https://example.test/pr/1"

        with patch.object(finalize, "open_pr", side_effect=fake_open_pr), patch.object(finalize, "time") as time_mock:
            url = finalize.open_pr_with_retry(repo, "feature/test", "main", "title", "body", "mbpass-app")
        self.assertEqual(url, "https://example.test/pr/1")
        self.assertEqual(2, calls["count"])
        time_mock.sleep.assert_called_once()

    def test_failure_payload_preserves_finalize_detail(self) -> None:
        existing = {
            "run_id": "20260720-112850",
            "failures": [{"stage": "finalize", "detail": "mbpass-app: Agent did not provide commit_subject"}],
            "verification_results": [{"status": "passed"}],
        }
        payload = failure_writer.build_failure_payload(
            None,
            "20260720-112850",
            "finalize",
            "Delivery finalization failed. See log: /tmp/run.log",
            "2026-07-20T11:28:50Z",
            existing,
        )
        self.assertEqual("mbpass-app: Agent did not provide commit_subject", payload["failures"][0]["detail"])
        self.assertEqual([{"status": "passed"}], payload["verification_results"])

    def test_merge_repos_touched_restores_missing_repositories(self) -> None:
        baseline = [
            {"name": "mbpass-app", "commit_subject": "[lumon] #MBPAS-1331 feat: app heartbeat"},
            {"name": "mbpass-business", "commit_subject": "[lumon] #MBPAS-1331 feat: business changes"},
        ]
        current = [
            {
                "name": "mbpass-business",
                "commit_subject": "[lumon] #MBPAS-1331 fix: remediate migration",
                "files_changed": ["src/main/resources/db/migration/foo.sql"],
            }
        ]
        merged = merge_repos_touched(current, baseline)
        names = [item["name"] for item in merged]
        self.assertEqual(["mbpass-app", "mbpass-business"], names)
        self.assertEqual("[lumon] #MBPAS-1331 feat: app heartbeat", merged[0]["commit_subject"])
        self.assertEqual("[lumon] #MBPAS-1331 fix: remediate migration", merged[1]["commit_subject"])


if __name__ == "__main__":
    unittest.main()
