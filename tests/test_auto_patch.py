from __future__ import annotations

import argparse
import json
import plistlib
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

LIB_DIR = Path(__file__).resolve().parents[1] / "lib" / "scripts"
import sys

if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from patch_launchd import interval_minutes_from_cron, status as patch_schedule_status  # noqa: E402
from patch_jira import blocked_comment, skipped_comment  # noqa: E402
from capture_patch_context import related_candidates  # noqa: E402
from jira_sync import allowed_severities, resolve_board_id, workspace_jira_config  # noqa: E402
from patch_runtime import (  # noqa: E402
    blocked_statuses,
    candidate_jql,
    has_external_reply,
    jira_config,
    patch_branch,
    patch_worktree_path,
    query_candidates,
)
from patch_runner import select_repositories, skip  # noqa: E402
from compose_patch_prompt import compose  # noqa: E402


class AutoPatchTests(unittest.TestCase):
    def test_default_jira_sync_includes_all_supported_severities(self) -> None:
        self.assertEqual(["High", "Medium", "Low"], allowed_severities({}))

    def test_repository_mapping_prioritizes_labels_and_repository_field(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repos = [
                {"name": "digital-platform-admin", "path": str(root / "digital-platform-admin")},
                {"name": "mbpass-admin", "path": str(root / "mbpass-admin")},
            ]
            for repo in repos:
                Path(repo["path"]).mkdir()
            item = {
                "key": "MBPAS-1555",
                "fields": {
                    "summary": "Legacy BEV filter fallback",
                    "labels": ["mbpass-admin"],
                    "description": "Repository: mbpass-admin\nSuggestion: mirror the fallback in digital-platform-admin.",
                },
            }
            with patch("patch_runner.repo_registry", return_value=repos):
                selected, reason = select_repositories(root, item)
        self.assertEqual(["mbpass-admin"], [repo["name"] for repo in selected])
        self.assertIn("explicit Repository fields", reason)

    def test_repository_mapping_uses_related_jira_history_when_scope_is_not_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repos = [
                {"name": "service", "path": str(root / "service")},
                {"name": "web", "path": str(root / "web")},
            ]
            for repo in repos:
                Path(repo["path"]).mkdir()
            item = {"key": "MBPAS-1556", "fields": {"summary": "Related behavior regression", "description": "See MBPAS-1548."}}
            context = root / "context.json"
            context.write_text(json.dumps({"related_keys": ["MBPAS-1548"], "related_workitems": []}), encoding="utf-8")

            def history(repo: dict, keys: list[str]) -> dict:
                return {"jira_keys": ["MBPAS-1548"] if repo["name"] == "service" else [], "subjects": []}

            with patch("patch_runner.repo_registry", return_value=repos), patch(
                "patch_runner._repository_code_search", return_value={"keywords": [], "files": 0, "sample_files": []}
            ), patch("patch_runner._repository_history", side_effect=history):
                selected, reason = select_repositories(root, item, context)
        self.assertEqual(["service"], [repo["name"] for repo in selected])
        self.assertIn("MBPAS-1548", reason)

    def test_patch_prompt_allows_bounded_multi_repository_functional_changes(self) -> None:
        templates = Path(__file__).resolve().parents[1] / "lib" / "templates" / "prompts" / "patch"
        pipeline = (templates / "02-pipeline.md").read_text(encoding="utf-8")
        implementation = (templates / "05-patch-implementation.md").read_text(encoding="utf-8")
        self.assertIn("multiple registered repositories", pipeline)
        self.assertIn("functional change with explicit acceptance criteria", pipeline)
        self.assertIn("every selected repository", implementation)
        self.assertNotIn("Do not implement a feature", pipeline)
        output_contract = (templates / "09-output-contract.md").read_text(encoding="utf-8")
        self.assertIn("<workspace-root>/lumon/results/patch-result.json", output_contract)
        self.assertNotIn("<workspace-root>/lumen/results/patch-result.json", output_contract)

    def test_patch_prompt_normalizes_legacy_local_output_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            prompts = workspace / "lumon" / "prompts" / "patch"
            prompts.mkdir(parents=True)
            (prompts / "manifest.json").write_text(
                json.dumps({"inline": ["09-output-contract.md"], "catalog": []}), encoding="utf-8"
            )
            (prompts / "09-output-contract.md").write_text(
                'Write `<workspace-root>/lumen/results/patch-result.json` with `[lumen] #KEY`.', encoding="utf-8"
            )
            with patch("compose_patch_prompt.repo_registry", return_value=[]):
                prompt = compose(workspace, "DEMO-1", "Example", workspace / "context.json", [])
        self.assertIn("<workspace-root>/lumon/results/patch-result.json", prompt)
        self.assertIn("[lumon] #KEY", prompt)
        self.assertNotIn("<workspace-root>/lumen/results/patch-result.json", prompt)

    def test_candidate_jql_filters_configured_types_and_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            with patch("patch_runtime.jira_config", return_value={"project_key": "DEMO"}), patch(
                "patch_runtime.eligible_statuses", return_value=["To Do", "Ready"]
            ), patch("patch_runtime.issue_types", return_value=["Task", "Bug"]):
                query = candidate_jql(workspace, "10025")
        self.assertEqual(
            'project = DEMO AND sprint = 10025 AND issuetype in ("Task", "Bug") AND status in ("To Do", "Ready") AND labels = "lumon-auto-patch" ORDER BY priority DESC, updated ASC',
            query,
        )

    def test_blocked_jql_includes_jira_migrated_status_alias(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            with patch("patch_runtime.jira_config", return_value={"project_key": "DEMO"}), patch(
                "patch_runtime.eligible_statuses", return_value=["To Do"]
            ), patch("patch_runtime.issue_types", return_value=["Task", "Bug"]), patch(
                "patch_runtime.patch_config", return_value={"blocked_status": "Block"}
            ):
                query = candidate_jql(workspace, "10025", include_blocked=True)
        self.assertIn('status in ("To Do", "Block", "Block (migrated)")', query)
        self.assertEqual(["Block", "Block (migrated)"], blocked_statuses(workspace))

    def test_candidate_jql_rejects_missing_or_non_numeric_sprint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                candidate_jql(Path(directory), "")
            with self.assertRaises(ValueError):
                candidate_jql(Path(directory), "10025 OR sprint in openSprints()")

    def test_explicit_patch_key_can_bypass_the_scheduled_trigger_label(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            with patch("patch_runtime.jira_config", return_value={"project_key": "DEMO"}), patch(
                "patch_runtime.eligible_statuses", return_value=["To Do"]
            ), patch("patch_runtime.issue_types", return_value=["Task"]):
                query = candidate_jql(workspace, "10025", require_trigger=False)
        self.assertNotIn("labels =", query)

    def test_board_auto_detection_does_not_use_an_issue_from_another_sprint(self) -> None:
        with patch("jira_sync.twg_ready", return_value=(True, "")), patch(
            "jira_sync.run_twg",
            return_value=(0, json.dumps({"data": {"boards": [{"id": 186, "type": "scrum"}]}})),
        ):
            self.assertEqual("186", resolve_board_id({"project_key": "DEMO"}))

    def test_candidate_query_uses_board_current_sprint_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            with patch("patch_runtime.jira_config", return_value={"project_key": "DEMO"}), patch(
                "patch_runtime.twg_ready", return_value=(True, "")
            ), patch("patch_runtime.refresh_twg_auth", return_value=(True, "")), patch(
                "patch_runtime.resolve_active_sprint", return_value=("10025", "Current")
            ), patch("patch_runtime.run_twg", return_value=(0, json.dumps({"data": {"issues": []}}))) as run:
                self.assertEqual([], query_candidates(workspace))
        command = run.call_args.args[0]
        self.assertIn("sprint = 10025", command[command.index("--jql") + 1])
        self.assertNotIn("openSprints()", command[command.index("--jql") + 1])

    def test_jira_project_key_comes_from_shared_common_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "lumen" / "config").mkdir(parents=True)
            (root / "lumen" / "config" / "common.json").write_text(
                json.dumps({"notifications": {"jira": {"project_key": "COMMON"}}}), encoding="utf-8"
            )
            (root / "lumen" / "config" / "delivery.json").write_text(
                json.dumps({"jira": {"project_key": "LEGACY"}}), encoding="utf-8"
            )
            self.assertEqual("COMMON", jira_config(root)["project_key"])
            self.assertEqual("COMMON", workspace_jira_config(root)["project_key"])

    def test_blocked_card_requires_new_external_reply(self) -> None:
        item = {"fields": {"comment": {"comments": [
            {"body": "Lumen Auto Patch · Blocked", "created": "2026-07-30T10:00:00Z"},
            {"body": "I meant the API repository", "created": "2026-07-30T10:05:00Z"},
        ]}}}
        self.assertTrue(has_external_reply(item, {"blocked_at": "2026-07-30T10:01:00Z"}))
        self.assertFalse(has_external_reply(item, {"blocked_at": "2026-07-30T10:06:00Z"}))

    def test_skipped_comment_records_reason_and_no_publish(self) -> None:
        comment = skipped_comment("The current code already implements the reported behavior.", "DEV DONE")
        self.assertIn("Lumen Auto Patch", comment)
        self.assertIn("Skipped", comment)
        self.assertIn("current code already implements", comment)
        self.assertIn("No code, commit, or pull request was produced", comment)
        self.assertIn("moved to DEV DONE", comment)

    def test_skip_moves_jira_to_done_status_and_records_registry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            progress = {
                "run_id": "20260804-000001",
                "jira_key": "DEMO-1",
                "jira_status": "In Progress",
                "original_jira_status": "To Do",
                "repositories": [],
                "failures": [],
                "phases": [],
            }
            result = {"patch_status": "skipped", "summary": "Expected behavior", "self_checks": []}
            with patch("patch_runner.patch_config", return_value={"done_status": "DEV DONE"}), patch(
                "patch_runner.transition_issue", return_value="DEV DONE"
            ) as transition, patch(
                "patch_runner.add_comment"
            ) as comment, patch(
                "patch_runner.get_workitem", return_value={"fields": {"updated": "2026-08-04T00:00:00Z"}}
            ), patch("patch_runner.notify"), patch("patch_runner.remove_worktrees"):
                self.assertEqual(0, skip(workspace, progress, result))
            transition.assert_called_once_with(workspace, "DEMO-1", "DEV DONE")
            comment.assert_called_once()
            self.assertEqual("sent", progress["jira"]["comment"])
            registry = json.loads((workspace / "lumon" / "state" / "patch-registry.json").read_text(encoding="utf-8"))
            self.assertEqual("skipped", registry["issues"]["DEMO-1"]["status"])

    def test_context_captures_jira_keys_mentioned_in_description(self) -> None:
        item = {"key": "MBPAS-1555", "fields": {"summary": "Legacy filter regression", "description": "Follow MBPAS-1548 compatibility behavior."}}
        with patch("capture_patch_context.jira_config", return_value={"project_key": ""}):
            self.assertEqual(["MBPAS-1548"], related_candidates(Path("/tmp"), item))

    def test_blocked_reply_is_found_when_primary_comment_page_is_empty(self) -> None:
        item = {
            "fields": {"comment": {"comments": []}},
            "comments": [{"body": {"type": "doc", "content": [{"text": "I have allowed the related repositories to auto patch. Please try again."}]}, "created": "2026-08-03T11:11:00.000+0800"}],
        }
        self.assertTrue(has_external_reply(item, {"blocked_at": "2026-08-03T03:09:02Z"}))

    def test_blocked_comment_matches_jira_readable_format(self) -> None:
        comment = blocked_comment("Repository <service> is ambiguous", "Should we modify service & api?")
        self.assertIn("<strong><span style=\"color: #bf2600\">Blocked</span></strong>", comment)
        self.assertIn("<strong>Confirmed:</strong> Repository &lt;service&gt; is ambiguous", comment)
        self.assertIn("<strong>Question:</strong> Should we modify service &amp; api?", comment)
        self.assertIn("color: #97a0af", comment)
        self.assertNotIn("- Confirmed:", comment)

    def test_patch_branch_and_worktree_are_deterministic(self) -> None:
        self.assertEqual("patch/DEMO-123-fix-login-timeout", patch_branch("DEMO-123", "Fix login timeout"))
        self.assertEqual(Path("/tmp/lumon/patch/DEMO-123/service"), patch_worktree_path(Path("/tmp"), "DEMO-123", "service"))

    def test_launchd_interval_parser_is_strict(self) -> None:
        self.assertEqual(5, interval_minutes_from_cron("*/5 * * * *"))
        self.assertIsNone(interval_minutes_from_cron("5 * * * *"))
        self.assertIsNone(interval_minutes_from_cron("*/0 * * * *"))

    def test_launchd_status_reports_an_installed_patch_schedule_as_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "patch.plist"
            path.write_bytes(plistlib.dumps({"StartInterval": 300}))
            output = StringIO()
            with patch("patch_launchd.plist_path", return_value=path), redirect_stdout(output):
                self.assertEqual(0, patch_schedule_status(argparse.Namespace(project="demo")))
        self.assertTrue(json.loads(output.getvalue())["enabled"])


if __name__ == "__main__":
    unittest.main()
