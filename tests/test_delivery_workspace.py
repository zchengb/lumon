from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import importlib.util
import unittest
import threading
import urllib.error
import urllib.request
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "lib" / "scripts"
REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_REGISTRY = SCRIPTS / "projects_registry.py"
sys.path.insert(0, str(SCRIPTS))

from delivery_workspace import (  # noqa: E402
    RepoTarget,
    StoryContext,
    discover_git_repos,
    ensure_feature_worktree,
    frontend_delivery_disabled_reasons,
    frontend_repository_names,
    load_workspace_config,
    story_worktrees_dir,
    validate_story_gates,
)
from render_delivery_dashboard import render  # noqa: E402
from init_delivery_docs import init_docs, sync_guidance  # noqa: E402
from install_agent_skills import install as install_agent_skills  # noqa: E402
from sync_workspace_repositories import sync as sync_scan_repositories  # noqa: E402
from delivery_scheduler import current_jira_status, normalize_statuses, story_candidates  # noqa: E402
from delivery_launchd import interval_minutes_from_cron  # noqa: E402
from scan_launchd import launchd_schedule_from_cron  # noqa: E402
from cleanup_delivery_worktrees import cleanup as cleanup_delivery_worktrees  # noqa: E402
from compose_delivery_prompt import compose_delivery_prompt, compose_snippets  # noqa: E402
from delivery_progress import finish_progress, print_progress_report, set_phase  # noqa: E402
from compose_scan_prompt import compose_prompt  # noqa: E402
from dashboard_server import (  # noqa: E402
    DashboardServer,
    clone_repository,
    delivery_payload,
    delivery_stages,
    feishu_notifications_enabled,
    list_observatory_stories,
    observatory_story_content,
    patch_payload,
    repository_branches,
    save_delivery_steps,
    save_feishu_notifications,
    save_observatory_story_content,
    save_publish_policy,
    save_repositories,
)
import dashboard_server  # noqa: E402
from capture_jira_context import image_urls, values_for_keys  # noqa: E402
import import_jira_story  # noqa: E402
from jira_delivery_sync import completion_comment  # noqa: E402
from auto_fix_sync import extract_pr_url, record_merge_success  # noqa: E402
from finalize_delivery import branch_has_commits  # noqa: E402
from run_delivery_verification import java_gradle_steps, resolve_codeartifact_token, run_command, verification_steps  # noqa: E402
from delivery_preflight import requires_docker_verification  # noqa: E402
from delivery_runtime import runtime_values  # noqa: E402


def load_delivery_notification_renderer():
    path = SCRIPTS / "render-delivery-and-notify.py"
    spec = importlib.util.spec_from_file_location("delivery_notification_renderer_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load delivery notification renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_patch_runner():
    path = SCRIPTS / "patch_runner.py"
    spec = importlib.util.spec_from_file_location("patch_runner_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load patch runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_scan_notification_renderer():
    path = SCRIPTS / "render-report-and-notify.py"
    spec = importlib.util.spec_from_file_location("scan_notification_renderer_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load scan notification renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_delivery_failure_writer():
    path = SCRIPTS / "write_delivery_failure.py"
    spec = importlib.util.spec_from_file_location("delivery_failure_writer_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load delivery failure writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(path: Path, *args: str) -> None:
    completed = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True)
    if completed.returncode != 0:
        raise AssertionError(completed.stderr or completed.stdout)


class DeliveryWorkspaceTests(unittest.TestCase):
    def test_sync_guidance_refreshes_loop_docs_and_keeps_story_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "README.md").write_text("# Old Docs\n", encoding="utf-8")
            (root / "AGENTS.md").write_text("old agent guide\n", encoding="utf-8")
            (root / "standards" / "development-loop.md").parent.mkdir(parents=True)
            (root / "standards" / "development-loop.md").write_text("old development loop\n", encoding="utf-8")
            story = root / "stories" / "MBPAS-1" / "story.md"
            story.parent.mkdir(parents=True)
            story.write_text("user story\n", encoding="utf-8")

            sync_guidance(root, "Example Docs", root / "backup")

            self.assertIn("# Example Docs", (root / "README.md").read_text(encoding="utf-8"))
            self.assertIn("# Example Docs Agent Guide", (root / "AGENTS.md").read_text(encoding="utf-8"))
            self.assertIn("lumen delivery run", (root / "standards" / "development-loop.md").read_text(encoding="utf-8"))
            self.assertEqual("user story\n", story.read_text(encoding="utf-8"))
            self.assertEqual("# Old Docs\n", (root / "backup" / "README.md").read_text(encoding="utf-8"))

    def test_delivery_failure_discards_previous_run_identity_and_outputs(self) -> None:
        writer = load_delivery_failure_writer()
        renderer = load_delivery_notification_renderer()
        docs = Path("/tmp/docs")
        context = SimpleNamespace(
            docs_dir=docs,
            workspace_root=docs,
            story_dir=docs / "stories" / "MBPAS-1527-new-delivery",
            metadata={"storyId": "MBPAS-1527", "jiraKey": "MBPAS-1527"},
            branch_name="feature/MBPAS-1527-new-delivery",
            repos=[SimpleNamespace(name="digital-platform-admin")],
        )
        delivery = writer.build_failure_payload(
            context, "20260719-073633", "preflight", "Contract incomplete", "2026-07-19T07:36:33Z"
        )
        delivery["finished_at"] = "2026-07-19T07:37:33Z"
        card = renderer.build_delivery_feishu_card("delivery.failed", delivery, {"title": "New delivery"}, docs)
        rendered = json.dumps(card, ensure_ascii=False)

        self.assertEqual("MBPAS-1527 · New delivery", card["card"]["header"]["subtitle"]["content"])
        self.assertIn("feature/MBPAS-1527-new-delivery", rendered)
        self.assertIn("**Duration:**  1m 00s", rendered)
        self.assertNotIn("MBPAS-1342", rendered)
        self.assertNotIn("/pull/", rendered)

    def test_delivery_payload_keeps_the_latest_progress_when_result_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "lumen"
            results = workspace / "results"
            results.mkdir(parents=True)
            (results / "delivery-progress.json").write_text(json.dumps({
                "run_id": "new-run", "delivery_status": "failed", "story_id": "NEW-1", "docs_dir": str(Path(temp)),
            }), encoding="utf-8")
            (results / "delivery-result.json").write_text(json.dumps({
                "run_id": "old-run", "delivery_status": "failed", "story_id": "OLD-1",
            }), encoding="utf-8")

            self.assertEqual("NEW-1", delivery_payload(workspace)["current"]["story_id"])

    def test_retry_delivery_starts_the_failed_story_without_deleting_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            docs = Path(temp) / "docs"
            workspace = docs / "lumen"
            results = workspace / "results"
            results.mkdir(parents=True)
            story = docs / "stories" / "DEMO-1"
            story.mkdir(parents=True)
            metadata_path = story / "metadata.json"
            metadata_path.write_text(json.dumps({"jiraKey": "DEMO-1", "deliveryStatus": "blocked", "deliveryBranch": "feature/old", "prUrl": "https://example.test/pr/1"}), encoding="utf-8")
            (results / "delivery-progress.json").write_text(json.dumps({
                "delivery_status": "failed", "story_id": "DEMO-1", "docs_dir": str(docs),
            }), encoding="utf-8")
            server = object.__new__(DashboardServer)
            server.lumen_bin = "/test/lumen"
            server.lumen_home = "/test/lumen-home"
            context = SimpleNamespace(docs_dir=docs, workspace_root=docs, story_dir=story, metadata_path=metadata_path, metadata={"jiraKey": "DEMO-1"})

            with patch.object(dashboard_server, "load_story_context", return_value=context), patch.object(dashboard_server, "should_sync_jira", return_value=(False, "not configured")), patch.object(dashboard_server, "cleanup_delivery_worktrees", return_value=["repo: removed"]), patch.object(dashboard_server.subprocess, "Popen") as launch:
                retry = server.retry_delivery(workspace)

            self.assertEqual("DEMO-1", retry["story"])
            self.assertEqual(
                ["/test/lumen", "delivery", "run", str(docs.resolve()), "--story", "DEMO-1"],
                launch.call_args.args[0],
            )
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual("not_started", metadata["deliveryStatus"])
            self.assertNotIn("deliveryBranch", metadata)
            self.assertNotIn("prUrl", metadata)
            self.assertFalse((workspace / "history").exists())

    def test_retry_delivery_recovers_an_orphaned_in_progress_story(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            docs = Path(temp) / "docs"
            workspace = docs / "lumen"
            results = workspace / "results"
            results.mkdir(parents=True)
            story = docs / "stories" / "DEMO-ORPHAN"
            story.mkdir(parents=True)
            metadata_path = story / "metadata.json"
            metadata_path.write_text(json.dumps({"jiraKey": "DEMO-ORPHAN", "deliveryStatus": "in_progress"}), encoding="utf-8")
            (results / "delivery-progress.json").write_text(json.dumps({
                "delivery_status": "in_progress", "story_id": "DEMO-ORPHAN", "docs_dir": str(docs),
            }), encoding="utf-8")
            server = object.__new__(DashboardServer)
            server.lumen_bin = "/test/lumen"
            server.lumen_home = "/test/lumen-home"
            context = SimpleNamespace(docs_dir=docs, workspace_root=docs, story_dir=story, metadata_path=metadata_path, metadata={"jiraKey": "DEMO-ORPHAN"})

            with patch.object(dashboard_server, "load_story_context", return_value=context), patch.object(dashboard_server, "should_sync_jira", return_value=(False, "not configured")), patch.object(dashboard_server, "cleanup_delivery_worktrees", return_value=[]), patch.object(dashboard_server.subprocess, "Popen") as launch:
                retry = server.retry_delivery(workspace)

            self.assertEqual("DEMO-ORPHAN", retry["story"])
            self.assertEqual("DEMO-ORPHAN", launch.call_args.args[0][-1])

    def test_retry_delivery_rejects_restarting_completed_story(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            docs = Path(temp) / "docs"
            workspace = docs / "lumen"
            results = workspace / "results"
            results.mkdir(parents=True)
            (results / "delivery-progress.json").write_text(json.dumps({
                "delivery_status": "completed", "story_id": "DEMO-1", "jira_key": "DEMO-1", "docs_dir": str(docs),
            }), encoding="utf-8")
            server = object.__new__(DashboardServer)
            with self.assertRaisesRegex(ValueError, "Only a stopped, failed, blocked, or not-started"):
                server.retry_delivery(workspace, "DEMO-1")

    def test_stop_delivery_finalizes_blocked_progress_and_archives_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            docs = Path(temp) / "docs"
            workspace = docs / "lumen"
            story = docs / "stories" / "DEMO-STOP"
            results = workspace / "results"
            lock = workspace / "locks" / "delivery-run"
            story.mkdir(parents=True)
            results.mkdir(parents=True)
            lock.mkdir(parents=True)
            (story / "metadata.json").write_text(json.dumps({"storyId": "DEMO-STOP", "jiraKey": "DEMO-STOP", "deliveryStatus": "in_progress"}), encoding="utf-8")
            (workspace / "config").mkdir(parents=True)
            (workspace / "config" / "delivery.json").write_text(json.dumps({"jira": {"enabled": False}}), encoding="utf-8")
            (workspace / "logs" / "delivery").mkdir(parents=True)
            log = workspace / "logs" / "delivery" / "run-stop.log"
            log.write_text("stopped\n", encoding="utf-8")
            (lock / "pid").write_text("999999\n", encoding="utf-8")
            (results / "delivery-progress.json").write_text(json.dumps({
                "run_id": "run-stop", "delivery_status": "in_progress", "story_id": "DEMO-STOP", "story_path": "stories/DEMO-STOP",
                "jira_key": "DEMO-STOP", "docs_dir": str(docs), "workspace_root": str(workspace), "branch": "feature/DEMO-STOP",
                "started_at": "2026-07-23T10:00:00Z", "log_file": str(log), "phases": [{"id": "agent", "status": "in_progress", "attempts": [{"started_at": "2026-07-23T10:00:00Z", "finished_at": ""}]}],
                "repositories": [], "verification": [],
            }), encoding="utf-8")
            server = object.__new__(DashboardServer)
            with patch.object(dashboard_server, "terminate_process_tree"), patch.object(dashboard_server, "should_sync_jira", return_value=(False, "disabled")), patch.object(dashboard_server, "cleanup_delivery_worktrees", return_value=[]):
                server.stop_delivery(workspace)

            progress = json.loads((results / "delivery-progress.json").read_text(encoding="utf-8"))
            metadata = json.loads((story / "metadata.json").read_text(encoding="utf-8"))
            result = json.loads((results / "delivery-result.json").read_text(encoding="utf-8"))
            self.assertEqual("blocked", progress["delivery_status"])
            self.assertEqual("blocked", progress["phases"][0]["status"])
            self.assertEqual("blocked", result["delivery_status"])
            self.assertTrue((workspace / "history" / "delivery" / "run-stop.json").is_file())
            self.assertEqual("blocked", metadata["deliveryStatus"])
            self.assertFalse(lock.exists())

    def test_delivery_runtime_parses_flags_and_resolves_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            docs = Path(temp)
            (docs / "stories").mkdir()
            (docs / "lumen" / "config").mkdir(parents=True)
            (docs / "lumen" / "config" / "workspace.json").write_text('{"workspace_root":"."}\n', encoding="utf-8")

            values = runtime_values([str(docs), "--story", "DEMO-1", "--dry-run"])

        self.assertEqual(str(docs.resolve()), values["DOCS_DIR"])
        self.assertEqual("DEMO-1", values["STORY_REF"])
        self.assertEqual("1", values["DRY_RUN"])
        self.assertEqual("lumen", values["WORKSPACE_DIR_NAME"])

    def test_plain_gradle_project_does_not_require_docker(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            (repo / "build.gradle").write_text("plugins { id 'java' }\n", encoding="utf-8")

            steps = java_gradle_steps(repo)

        self.assertFalse(next(step for step in steps if step["id"] == "test_suite")["requires_docker"])

    def test_testcontainers_gradle_project_requires_docker(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            (repo / "build.gradle").write_text("testImplementation 'org.testcontainers:junit-jupiter:1.20.0'\n", encoding="utf-8")

            steps = java_gradle_steps(repo)

        self.assertTrue(next(step for step in steps if step["id"] == "test_suite")["requires_docker"])

    def test_repository_verification_can_run_compile_without_tests(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            (repo / "build.gradle").write_text("plugins { id 'java' }\n", encoding="utf-8")

            compile_only = verification_steps({}, repo, mode="auto", compile_enabled=True, tests_enabled=False)
            tests_only = verification_steps({}, repo, mode="auto", compile_enabled=False, tests_enabled=True)
            skipped = verification_steps({}, repo, mode="skip")

        self.assertEqual(["language_grammar"], [step["id"] for step in compile_only])
        self.assertEqual(["test_suite"], [step["id"] for step in tests_only])
        self.assertEqual([], skipped)

    def test_preflight_detects_automatic_testcontainers_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            (repo / "build.gradle").write_text("testImplementation 'org.testcontainers:junit-jupiter:1.20.0'\n", encoding="utf-8")

            required = requires_docker_verification({}, [SimpleNamespace(path=repo)])

        self.assertTrue(required)

    def test_preflight_does_not_require_docker_when_repository_tests_are_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            (repo / "build.gradle").write_text("testImplementation 'org.testcontainers:junit-jupiter:1.20.0'\n", encoding="utf-8")

            required = requires_docker_verification(
                {},
                [SimpleNamespace(name="service", path=repo)],
                {"service": {"verification": {"mode": "auto", "tests": False}}},
            )

        self.assertFalse(required)

    def test_docker_gradle_command_uses_a_fresh_daemon(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            (repo / "gradlew").write_text("#!/bin/sh\n", encoding="utf-8")
            completed = SimpleNamespace(returncode=0, stdout="", stderr="")
            with patch("run_delivery_verification.subprocess.run", return_value=completed) as run:
                run_command(repo, ["./gradlew", "test"], {"DOCKER_HOST": "unix:///docker.sock"}, isolated=True)

        self.assertEqual([str(repo / "gradlew"), "--no-daemon", "test"], run.call_args.args[0])

    def test_codeartifact_gradle_command_uses_a_fresh_daemon(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            (repo / "gradlew").write_text("#!/bin/sh\n", encoding="utf-8")
            completed = SimpleNamespace(returncode=0, stdout="", stderr="")
            with patch("run_delivery_verification.subprocess.run", return_value=completed) as run:
                run_command(repo, ["./gradlew", "compileJava"], {"CODEARTIFACT_AUTH_TOKEN": "token"})

        self.assertEqual([str(repo / "gradlew"), "--no-daemon", "compileJava"], run.call_args.args[0])

    def test_codeartifact_token_uses_repository_helper_without_running_shell_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            (repo / "acquire-code-artifact-token.sh").write_text(
                "token=$(aws codeartifact get-authorization-token --domain mbpass --domain-owner 943884814247 --query authorizationToken --output text)\n",
                encoding="utf-8",
            )
            completed = SimpleNamespace(returncode=0, stdout="token-value\n", stderr="")
            with patch("run_delivery_verification.subprocess.run", return_value=completed) as run:
                token_env, detail = resolve_codeartifact_token({}, repo)

        self.assertEqual({"CODEARTIFACT_AUTH_TOKEN": "token-value"}, token_env)
        self.assertIn("repository helper", detail)
        self.assertEqual(
            [
                "aws",
                "codeartifact",
                "get-authorization-token",
                "--domain",
                "mbpass",
                "--domain-owner",
                "943884814247",
                "--query",
                "authorizationToken",
                "--output",
                "text",
            ],
            run.call_args.args[0],
        )
        self.assertFalse(run.call_args.kwargs["shell"])

    def test_branch_commit_check_ignores_clean_feature_branch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "service"
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
            git(repo, "config", "user.email", "lumen@example.test")
            git(repo, "config", "user.name", "Lumen Test")
            (repo / "README.md").write_text("base\n", encoding="utf-8")
            git(repo, "add", "README.md")
            git(repo, "commit", "-m", "initial")
            git(repo, "remote", "add", "origin", str(repo))
            git(repo, "fetch", "origin", "main:refs/remotes/origin/main")
            git(repo, "switch", "-c", "feature/DEMO-1")

            self.assertFalse(branch_has_commits(repo, "main"))

            (repo / "README.md").write_text("changed\n", encoding="utf-8")
            git(repo, "commit", "-am", "change")
            self.assertTrue(branch_has_commits(repo, "main"))

    def test_pr_url_extraction_rejects_gh_help_and_accepts_pull_request_urls(self) -> None:
        help_output = "Read the manual at https://cli.github.com/manual\n"
        self.assertEqual("", extract_pr_url(help_output))
        self.assertEqual(
            "https://git.example.test/team/service/pull/42",
            extract_pr_url("https://git.example.test/team/service/pull/42\n"),
        )

    def test_scan_notification_recovers_jira_link_from_published_story(self) -> None:
        renderer = load_scan_notification_renderer()
        with tempfile.TemporaryDirectory() as temp:
            docs = Path(temp)
            story = docs / "stories" / "demo"
            story.mkdir(parents=True)
            (story / "metadata.json").write_text(
                json.dumps({"jiraUrl": "https://example.atlassian.net/browse/DEMO-1"}),
                encoding="utf-8",
            )
            card = renderer.build_feishu_card(
                {"findings": [{"title": "Demo", "severity": "High", "jira_key": "DEMO-42"}]},
                common={"execution": {"model": "cursor-grok-4.5-high"}},
                docs_root=docs,
            )
        rendered = json.dumps(card)
        self.assertIn("[DEMO-42](https://example.atlassian.net/browse/DEMO-42)", rendered)
        self.assertIn("**Model:**  `cursor-grok-4.5-high`", rendered)

    def test_archived_scan_result_keeps_jira_links_from_processed_result(self) -> None:
        renderer = load_scan_notification_renderer()
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            results = workspace / "results"
            results.mkdir()
            archived = results / "scan-result-20260728-040521.json"
            archived.write_text(
                json.dumps(
                    {
                        "started_at": "2026-07-28T03:58:00Z",
                        "findings": [{"title": "Demo", "severity": "Medium"}],
                    }
                ),
                encoding="utf-8",
            )
            renderer.sync_archived_scan_results(
                workspace,
                {
                    "started_at": "2026-07-28T03:58:00Z",
                    "findings": [
                        {
                            "title": "Demo",
                            "severity": "Medium",
                            "issue_id": "ISSUE-demo",
                            "jira_key": "DEMO-1",
                            "jira_url": "https://example.atlassian.net/browse/DEMO-1",
                        }
                    ],
                    "report": {"status": "generated"},
                    "jira": {"status": "synced", "created": 1},
                },
            )
            result = json.loads(archived.read_text(encoding="utf-8"))
        self.assertEqual("DEMO-1", result["findings"][0]["jira_key"])
        self.assertEqual("ISSUE-demo", result["findings"][0]["issue_id"])

    def test_scan_without_findings_skips_report_artifacts(self) -> None:
        renderer = load_scan_notification_renderer()
        self.assertFalse(renderer.has_findings({"findings": []}))
        self.assertTrue(renderer.has_findings({"findings": [{"title": "Demo"}]}))
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            result = workspace / "results" / "scan-result.json"
            result.parent.mkdir()
            result.write_text(json.dumps({"started_at": "2026-07-16T04:00:00Z", "findings": []}), encoding="utf-8")

            subprocess.run(
                [sys.executable, str(SCRIPTS / "render-report-and-notify.py"), str(result)],
                check=True,
                capture_output=True,
                text=True,
                env={**os.environ, "FEISHU_WEBHOOK_URL": ""},
            )

            self.assertEqual("not_generated", json.loads(result.read_text(encoding="utf-8"))["report"]["status"])
            self.assertFalse((workspace / "reports").exists())

    def test_agent_feishu_placeholder_still_publishes(self) -> None:
        renderer = load_scan_notification_renderer()
        self.assertTrue(renderer._feishu_needs_publish({}))
        self.assertTrue(renderer._feishu_needs_publish({"feishu": {"status": "not_sent", "error": None}}))
        self.assertTrue(renderer._feishu_needs_publish({"feishu": {"status": "pending"}}))
        self.assertFalse(renderer._feishu_needs_publish({"feishu": {"status": "sent", "error": None}}))
        self.assertFalse(renderer._feishu_needs_publish({"feishu": {"status": "failed", "error": "boom"}}))
        self.assertFalse(renderer._feishu_needs_publish({"feishu": {"status": "skipped"}}))
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            result = workspace / "results" / "scan-result.json"
            result.parent.mkdir()
            result.write_text(
                json.dumps(
                    {
                        "started_at": "2026-08-05T04:00:00Z",
                        "findings": [],
                        "feishu": {"status": "not_sent", "error": None},
                    }
                ),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [sys.executable, str(SCRIPTS / "render-report-and-notify.py"), str(result)],
                check=True,
                capture_output=True,
                text=True,
                env={**os.environ, "FEISHU_WEBHOOK_URL": ""},
            )
            payload = json.loads(result.read_text(encoding="utf-8"))
            self.assertEqual("not_sent", payload["feishu"]["status"])
            self.assertIn("FEISHU_WEBHOOK_URL", str(payload["feishu"].get("error") or ""))
            self.assertIn("feishu_status", completed.stdout)

    def test_delivery_notification_uses_run_started_at_for_duration(self) -> None:
        renderer = load_delivery_notification_renderer()
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            results = workspace / "lumen" / "results"
            results.mkdir(parents=True)
            (results / "delivery-progress.json").write_text(
                json.dumps({"story_id": "DEMO-42", "started_at": "2026-07-15T16:55:46Z"}),
                encoding="utf-8",
            )
            delivery = {"story_id": "DEMO-42", "started_at": "2026-07-15T16:56:14Z", "finished_at": "2026-07-15T17:06:53Z"}
            renderer.align_delivery_timing(delivery, workspace)
        self.assertEqual("11m 07s", renderer.format_duration(delivery["started_at"], delivery["finished_at"]))

    def test_jira_completion_comment_includes_repo_named_prs_and_verification(self) -> None:
        comment = completion_comment(
            {
                "branch": "feature/NOVA-42-contract",
                "started_at": "2026-07-14T06:00:00Z",
                "finished_at": "2026-07-14T06:14:30Z",
                "repos_touched": [
                    {"name": "portal", "pr_url": "https://example.test/org/portal/pull/7"},
                    {"name": "service", "pr_url": "https://example.test/org/service/pull/9"},
                ],
                "verification_results": [{"status": "passed"}, {"status": "passed"}, {"status": "skipped"}],
            }
        )

        self.assertIn("Duration: 14m", comment)
        self.assertIn("Verification: 2 passed, 0 failed, 1 skipped", comment)
        self.assertIn("portal: https://example.test/org/portal/pull/7", comment)
        self.assertIn("service: https://example.test/org/service/pull/9", comment)

    def test_jira_context_extracts_nested_comments_and_image_urls(self) -> None:
        payload = {
            "fields": {
                "comments": [{"body": "A decision"}],
                "attachments": [{"content": "https://example.test/diagram.png"}],
            }
        }

        self.assertEqual([[{"body": "A decision"}]], values_for_keys(payload, {"comments", "comment"}))
        self.assertEqual(["https://example.test/diagram.png"], image_urls(payload))

    def test_dashboard_current_delivery_prefers_terminal_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            results = workspace / "results"
            results.mkdir()
            (results / "delivery-progress.json").write_text(
                json.dumps({
                    "run_id": "run-42",
                    "delivery_status": "in_progress",
                    "current_phase": "notify",
                    "story_id": "NOVA-42",
                    "started_at": "2026-07-14T05:50:00Z",
                }),
                encoding="utf-8",
            )
            (results / "delivery-result.json").write_text(
                json.dumps(
                    {
                        "delivery_status": "completed",
                        "story_id": "NOVA-42",
                        "started_at": "2026-07-14T05:50:00Z",
                        "finished_at": "2026-07-14T06:00:00Z",
                        "verification_results": [{"status": "passed"}],
                    }
                ),
                encoding="utf-8",
            )

            current = delivery_payload(workspace)["current"]

            self.assertEqual("completed", current["delivery_status"])
            self.assertEqual("completed", current["current_phase"])
            self.assertEqual("2026-07-14T06:00:00Z", current["finished_at"])
            self.assertEqual("passed", current["verification"][0]["status"])

    def test_finish_progress_keeps_terminal_status_when_detail_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            docs = Path(temp)
            results = docs / "lumen" / "results"
            results.mkdir(parents=True)
            (results / "delivery-progress.json").write_text(
                json.dumps({"run_id": "run-43", "delivery_status": "in_progress", "messages": []}),
                encoding="utf-8",
            )

            finish_progress(docs, "completed", "Delivery run finished")
            progress = json.loads((results / "delivery-progress.json").read_text(encoding="utf-8"))

            self.assertEqual("completed", progress["delivery_status"])
            self.assertTrue(progress["finished_at"])
            self.assertEqual("", progress["current_phase"])
            self.assertEqual("", progress["current_step"])
            self.assertEqual("Delivery run finished", progress["messages"][-1]["message"])

    def test_dashboard_exposes_active_remediation_and_restarts_phase_timer(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            docs = Path(temp)
            lumen = docs / "lumen"
            results = lumen / "results"
            results.mkdir(parents=True)
            progress = {
                "run_id": "20260718-010000",
                "story_id": "DEMO-1",
                "delivery_status": "in_progress",
                "phases": [
                    {"id": "agent", "status": "completed", "started_at": "2026-07-18T01:00:00Z", "finished_at": "2026-07-18T01:02:00Z"},
                    {"id": "verification", "status": "failed", "started_at": "2026-07-18T01:02:00Z", "finished_at": "2026-07-18T01:03:00Z", "detail": "Verification failed"},
                ],
            }
            (results / "delivery-progress.json").write_text(json.dumps(progress), encoding="utf-8")
            (results / "delivery-remediation.json").write_text(json.dumps({"run_id": progress["run_id"], "story_id": "DEMO-1", "attempt": 2, "max_attempts": 3, "status": "in_progress"}), encoding="utf-8")

            set_phase(docs, "agent", "in_progress", "Remediation attempt 2/3")
            updated = json.loads((results / "delivery-progress.json").read_text(encoding="utf-8"))
            agent = next(phase for phase in updated["phases"] if phase["id"] == "agent")
            self.assertEqual("", agent["finished_at"])
            self.assertEqual("in_progress", updated["delivery_status"])

            current = delivery_payload(lumen)["current"]
            self.assertEqual(2, current["remediation"]["attempt"])
            self.assertEqual("in_progress", next(stage for stage in current["stages"] if stage["id"] == "implement")["status"])
            self.assertEqual("failed", next(stage for stage in current["stages"] if stage["id"] == "verification")["status"])

    def test_dashboard_ignores_remediation_from_another_delivery_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "lumen"
            results = workspace / "results"
            results.mkdir(parents=True)
            (results / "delivery-progress.json").write_text(json.dumps({
                "run_id": "current-run", "delivery_status": "in_progress", "story_id": "MBPAS-1276",
            }), encoding="utf-8")
            (results / "delivery-remediation.json").write_text(json.dumps({
                "run_id": "old-run", "story_id": "MBPAS-1276", "attempt": 2, "max_attempts": 2, "status": "in_progress",
            }), encoding="utf-8")

            current = delivery_payload(workspace)["current"]

            self.assertNotIn("remediation", current)

    def test_phase_attempts_preserve_remediation_timing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            docs = Path(temp)
            results = docs / "lumen" / "results"
            results.mkdir(parents=True)
            (results / "delivery-progress.json").write_text(json.dumps({
                "phases": [{"id": "agent", "status": "completed", "started_at": "2026-07-18T01:00:00Z", "finished_at": "2026-07-18T01:02:00Z"}],
            }), encoding="utf-8")
            import delivery_progress
            from unittest.mock import patch
            with patch.object(delivery_progress, "utc_now", return_value="2026-07-18T01:03:00Z"):
                set_phase(docs, "agent", "in_progress")
            with patch.object(delivery_progress, "utc_now", return_value="2026-07-18T01:04:00Z"):
                set_phase(docs, "agent", "completed")
            agent = json.loads((results / "delivery-progress.json").read_text(encoding="utf-8"))["phases"][0]
            self.assertEqual(2, len(agent["attempts"]))
            stage = next(item for item in delivery_stages([agent]) if item["id"] == "implement")
            self.assertEqual("3m 00s", stage["duration"])
            self.assertEqual("active", stage["duration_kind"])

    def test_dashboard_serves_report_artifacts_without_exposing_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            reports = workspace / "reports"
            reports.mkdir()
            (reports / "scan.html").write_text("<h1>Scan report</h1>", encoding="utf-8")
            (reports / "scan.pdf").write_bytes(b"%PDF-demo")
            (workspace / "config").mkdir()
            (workspace / "config" / "common.json").write_text("{}\n", encoding="utf-8")
            (workspace / "config" / "repos.json").write_text('{"repositories": []}\n', encoding="utf-8")
            server = DashboardServer(("127.0.0.1", 0), workspace, "demo", "lumen", str(REPO_ROOT))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base_url = f"http://127.0.0.1:{server.server_port}"
                with urllib.request.urlopen(f"{base_url}/reports/scan.html") as response:
                    self.assertEqual("text/html", response.headers.get_content_type())
                    self.assertIn("Scan report", response.read().decode("utf-8"))
                with urllib.request.urlopen(f"{base_url}/reports/scan.pdf") as response:
                    self.assertEqual("application/pdf", response.headers.get_content_type())
                    self.assertEqual(b"%PDF-demo", response.read())
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(f"{base_url}/reports/../config/common.json")
                self.assertEqual(404, error.exception.code)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_delivery_log_endpoint_returns_live_uncached_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            log = workspace / "logs" / "delivery" / "run-live.log"
            log.parent.mkdir(parents=True)
            log.write_text("first line\n", encoding="utf-8")
            (workspace / "results").mkdir()
            (workspace / "results" / "delivery-progress.json").write_text(
                json.dumps({"run_id": "live", "delivery_status": "in_progress", "log_file": str(log)}),
                encoding="utf-8",
            )
            (workspace / "config").mkdir()
            (workspace / "config" / "common.json").write_text("{}\n", encoding="utf-8")
            (workspace / "config" / "repos.json").write_text('{"repositories": []}\n', encoding="utf-8")
            server = DashboardServer(("127.0.0.1", 0), workspace, "demo", "lumen", str(REPO_ROOT))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/api/delivery/log?run_id=live"
                with urllib.request.urlopen(url) as response:
                    self.assertEqual("no-store", response.headers["Cache-Control"])
                    self.assertIn("first line", response.read().decode("utf-8"))
                log.write_text("first line\nsecond line\n", encoding="utf-8")
                with urllib.request.urlopen(url) as response:
                    self.assertIn("second line", response.read().decode("utf-8"))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_dashboard_ignore_api_updates_only_local_issue_registry(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            (workspace / "config").mkdir()
            (workspace / "state").mkdir()
            (workspace / "config" / "common.json").write_text(
                json.dumps({"paths": {"issue_registry": "state/issue-registry.json"}}),
                encoding="utf-8",
            )
            (workspace / "config" / "repos.json").write_text('{"repositories": []}\n', encoding="utf-8")
            (workspace / "state" / "issue-registry.json").write_text(
                json.dumps({"issues": [{"id": "ISSUE-1", "status": "open", "title": "Demo"}]}),
                encoding="utf-8",
            )
            server = DashboardServer(("127.0.0.1", 0), workspace, "demo", "lumen", str(REPO_ROOT))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                request = urllib.request.Request(
                    f"http://127.0.0.1:{server.server_port}/api/issue/ignore",
                    data=json.dumps({"issue_id": "ISSUE-1", "reason": "Not applicable"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

            self.assertEqual("ignored", payload["issue"]["status"])
            registry = json.loads((workspace / "state" / "issue-registry.json").read_text(encoding="utf-8"))
            self.assertEqual("ignored", registry["issues"][0]["status"])
            self.assertEqual("Not applicable", registry["issues"][0]["ignore_reason"])

    def test_repository_and_publish_configuration_persist_in_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            remote = root / "remote.git"
            docs = root / "docs"
            workspace = docs / "lumen"
            repository = root / "service"
            subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
            subprocess.run(["git", "init", "-b", "main", str(docs)], check=True, capture_output=True)
            git(docs, "config", "user.email", "lumen@example.test")
            git(docs, "config", "user.name", "Lumen Test")
            subprocess.run(["git", "init", str(repository)], check=True, capture_output=True)
            config = workspace / "config"
            config.mkdir(parents=True)
            (config / "common.json").write_text(json.dumps({"execution": {"model": "scan-custom-model"}}) + "\n", encoding="utf-8")
            (config / "delivery.json").write_text(json.dumps({"execution": {"model": "delivery-custom-model", "patch_model": "patch-custom-model"}}) + "\n", encoding="utf-8")
            (config / "runtime-profiles.json").write_text(
                json.dumps({"local-java-review-only": {"language": "java", "validation": "review only"}}),
                encoding="utf-8",
            )
            (config / "repos.json").write_text(json.dumps({"repositories": []}), encoding="utf-8")
            (config / "workspace.json").write_text(json.dumps({"docs_repo": str(docs)}), encoding="utf-8")
            git(docs, "add", "lumen/config")
            git(docs, "commit", "-m", "Initialize config")
            git(docs, "remote", "add", "origin", str(remote))
            git(docs, "push", "-u", "origin", "main")

            payload = save_repositories(workspace, [{
                "name": "service",
                "path": str(repository),
                "default_branch": "main",
                "runtime_profile": "local-java-review-only",
                "allow_auto_fix": True,
                "allow_pr": True,
            }])
            self.assertEqual("service", payload["repositories"][0]["name"])
            save_delivery_steps(workspace, "service", ["./gradlew test", "./gradlew pmdMain"])
            payload = save_publish_policy(workspace, "pr", "merge", "direct")

            delivery = json.loads((config / "delivery.json").read_text(encoding="utf-8"))
            common = json.loads((config / "common.json").read_text(encoding="utf-8"))
            self.assertEqual(["./gradlew", "test"], delivery["verification"]["steps"]["service"][0]["command"])
            self.assertEqual("merge", delivery["publish"]["mode"])
            self.assertEqual("delivery-custom-model", delivery["execution"]["model"])
            self.assertEqual("patch-custom-model", delivery["execution"]["patch_model"])
            self.assertEqual("direct", delivery["publish"]["auto_patch"]["mode"])
            self.assertEqual("pr", common["auto_fix"]["publish_mode"])
            self.assertEqual("scan-custom-model", common["execution"]["model"])
            self.assertEqual("direct", payload["publish"]["patch"])
            with self.assertRaisesRegex(ValueError, "Auto Scan supports only PR or Merge"):
                save_publish_policy(workspace, "direct", "merge", "direct", push=False)
            log = subprocess.run(
                ["git", "-C", str(docs), "log", "-1", "--format=%s"],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual("[lumon] #N/A feat: update delivery config", log.stdout.strip())

    def test_auto_fix_merge_resolves_the_tracked_finding(self) -> None:
        finding = {"issue_id": "ISSUE-42", "auto_fix": {"status": "pr_open"}, "issue_status": "pr_open"}
        registry = {"issues": [{"id": "ISSUE-42", "status": "pr_open"}]}

        record_merge_success(finding, registry, "2026-07-16T12:00:00Z")

        self.assertEqual("merged", finding["auto_fix"]["status"])
        self.assertEqual("resolved", finding["issue_status"])
        self.assertEqual("resolved", registry["issues"][0]["status"])

    def test_clone_repository_registers_in_docs_repos_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace = root / "docs" / "lumen"
            remote = root / "service.git"
            docs_remote = root / "docs.git"
            subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
            subprocess.run(["git", "init", "--bare", str(docs_remote)], check=True, capture_output=True)
            subprocess.run(["git", "init", "-b", "main", str(root / "docs")], check=True, capture_output=True)
            git(root / "docs", "config", "user.email", "lumen@example.test")
            git(root / "docs", "config", "user.name", "Lumen Test")
            (workspace / "config").mkdir(parents=True)
            (workspace / "config" / "common.json").write_text("{}\n", encoding="utf-8")
            (workspace / "config" / "delivery.json").write_text("{}\n", encoding="utf-8")
            (workspace / "config" / "repos.json").write_text(json.dumps({"repositories": []}), encoding="utf-8")
            (workspace / "config" / "workspace.json").write_text(json.dumps({"docs_repo": str(root / "docs")}), encoding="utf-8")
            (workspace / "config" / "runtime-profiles.json").write_text(
                json.dumps({"local-generic-review-only": {"language": "generic", "validation": "review only"}}),
                encoding="utf-8",
            )
            git(root / "docs", "add", "lumen/config")
            git(root / "docs", "commit", "-m", "Initialize docs")
            git(root / "docs", "remote", "add", "origin", str(docs_remote))
            git(root / "docs", "push", "-u", "origin", "main")

            payload = clone_repository(workspace, str(remote))

            repository = payload["repositories"][0]
            self.assertEqual("service", repository["name"])
            self.assertTrue((root / "docs" / "repos" / "service" / ".git").exists())
            log = subprocess.run(
                ["git", "-C", str(root / "docs"), "log", "-1", "--format=%s"],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual("[lumon] #N/A feat: update delivery config", log.stdout.strip())

    def test_repository_branch_options_include_local_and_remote_refs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repository = Path(temp) / "service"
            subprocess.run(["git", "init", "-b", "main", str(repository)], check=True, capture_output=True)
            git(repository, "config", "user.email", "lumen@example.test")
            git(repository, "config", "user.name", "Lumen Test")
            (repository / "README.md").write_text("base\n", encoding="utf-8")
            git(repository, "add", "README.md")
            git(repository, "commit", "-m", "initial")
            git(repository, "branch", "release")

            self.assertEqual(["main", "release"], repository_branches(repository, "main"))

    def test_delivery_report_prefers_terminal_result_over_stale_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            results = workspace / "lumen" / "results"
            results.mkdir(parents=True)
            (results / "delivery-progress.json").write_text(
                json.dumps(
                    {
                        "run_id": "20260714-040321",
                        "delivery_status": "in_progress",
                        "current_phase": "verification",
                        "current_step": "old failed test",
                        "verification": [{"label": "Old Test", "status": "failed"}],
                    }
                ),
                encoding="utf-8",
            )
            (results / "delivery-result.json").write_text(
                json.dumps(
                    {
                        "delivery_status": "completed",
                        "finished_at": "2026-07-14T05:42:59Z",
                        "verification_results": [{"label": "Full Test Suite", "status": "passed"}],
                    }
                ),
                encoding="utf-8",
            )

            output = StringIO()
            with redirect_stdout(output):
                print_progress_report(workspace)

            report = output.getvalue()
            self.assertIn("Status:      completed", report)
            self.assertIn("✓ [] Full Test Suite", report)
            self.assertNotIn("Current:", report)
            self.assertNotIn("Old Test", report)

    def test_delivery_prompt_is_separate_from_scan_prompt_assets(self) -> None:
        delivery_prompt = compose_snippets()
        scan_manifest = json.loads(
            (REPO_ROOT / "lib" / "templates" / "prompts" / "scan" / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertIn("# Delivery Agent", delivery_prompt)
        self.assertIn("# Delivery Prompt Catalog", delivery_prompt)
        self.assertNotIn("# Implementation Rules", delivery_prompt)
        scan_files = [
            *(scan_manifest.get("inline") or []),
            *[
                entry if isinstance(entry, str) else entry.get("file", "")
                for entry in (scan_manifest.get("catalog") or scan_manifest.get("snippets") or [])
            ],
        ]
        for scan_snippet in scan_files:
            if scan_snippet:
                self.assertNotIn(scan_snippet, delivery_prompt)

    def test_delivery_prompt_catalog_marks_visual_snippet_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            story_dir = workspace / "stories" / "MBPAS-101-visual"
            story_dir.mkdir(parents=True)
            plan = story_dir / "technical-plan.md"
            plan.write_text(
                "# Plan\n\n## Visual Delivery Contract\n\n### Visual State Matrix\n\n"
                "| Screen | State | Fixture | Reference | Stable marker |\n"
                "|---|---|---|---|---|\n"
                "| Dealer | Disabled | /mbtw/message/create | assets/disabled.png | dealer-filter-section |\n\n"
                "### Visual Verification\n\n"
                "| Screen | State | Comparison | Maximum difference |\n"
                "|---|---|---|---|\n"
                "| Dealer | Disabled | Full content area | 1% |\n\n"
                "### Design Source\n\n"
                "| Screen | Figma file | Node ID | Approved reference | Design context snapshot |\n"
                "|---|---|---|---|---|\n"
                "| Dealer | https://www.figma.com/design/demo | `12:34` | assets/ref.png | assets/ref.context.json |\n\n"
                "### Figma-to-Code Component Mapping\n\n"
                "| Figma component | Code component | Notes |\n"
                "|---|---|---|\n"
                "| Tag | DealerTag | reuse |\n\n"
                "### Platform Rules\n\nUse web.\n\n"
                "### Runtime\n\n"
                "| Property | Value |\n|---|---|\n"
                "| repository | digital-platform-admin |\n"
                "| runtime_profile | web-review-only |\n"
                "| platform | web |\n"
                "| navigation | /mbtw/message/create |\n"
                "| authentication | fake login |\n",
                encoding="utf-8",
            )
            context = StoryContext(
                docs_dir=workspace,
                workspace_root=workspace,
                story_dir=story_dir,
                story_md=story_dir / "story.md",
                technical_plan=plan,
                metadata_path=story_dir / "metadata.json",
                metadata={},
                repos=[],
                branch_name="feature/MBPAS-101-visual",
                delivery_config={},
                workspace_config={},
            )
            prompt = compose_delivery_prompt(context)
            self.assertIn("# Frontend Delivery Policy", prompt)
            self.assertNotIn("05-visual-delivery.md", prompt)
            self.assertNotIn("# Visual State Matrix (verify every row)", prompt)
            self.assertNotIn("# Visual QA", prompt)
            self.assertNotIn("# Implementation Rules", prompt.split("# Delivery Context")[0])

    def test_generic_ui_delivery_prompt_applies_without_visual_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            story_dir = workspace / "stories" / "DEMO-ui"
            story_dir.mkdir(parents=True)
            (workspace / "lumen" / "config").mkdir(parents=True)
            (workspace / "lumen" / "config" / "repos.json").write_text(
                json.dumps({"repositories": [{"name": "portal", "runtime": {"platform": "web"}}]}),
                encoding="utf-8",
            )
            plan = story_dir / "technical-plan.md"
            plan.write_text("# Plan\n\nImplement the page.\n", encoding="utf-8")
            context = StoryContext(
                docs_dir=workspace,
                workspace_root=workspace,
                story_dir=story_dir,
                story_md=story_dir / "story.md",
                technical_plan=plan,
                metadata_path=story_dir / "metadata.json",
                metadata={},
                repos=[RepoTarget("portal", workspace / "repo", workspace / "worktree")],
                branch_name="feature/DEMO-ui",
                delivery_config={},
                workspace_config={},
            )

            prompt = compose_delivery_prompt(context)

            self.assertIn("# Frontend Delivery Policy", prompt)
            self.assertNotIn("05-visual-delivery.md", prompt)
            self.assertNotIn("# Visual QA", prompt)

    def test_frontend_delivery_scope_is_identified_for_skipping(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            story_dir = workspace / "stories" / "DEMO-ui"
            story_dir.mkdir(parents=True)
            (workspace / "lumen" / "config").mkdir(parents=True)
            (workspace / "lumen" / "config" / "repos.json").write_text(
                json.dumps({"repositories": [{"name": "portal", "runtime": {"platform": "web"}}]}),
                encoding="utf-8",
            )
            context = StoryContext(
                docs_dir=workspace,
                workspace_root=workspace,
                story_dir=story_dir,
                story_md=story_dir / "story.md",
                technical_plan=story_dir / "technical-plan.md",
                metadata_path=story_dir / "metadata.json",
                metadata={},
                repos=[RepoTarget("portal", workspace / "repo", workspace / "worktree")],
                branch_name="feature/DEMO-ui",
                delivery_config={},
                workspace_config={},
            )

            reasons = frontend_delivery_disabled_reasons(context)

            self.assertEqual(["repository 'portal' uses web"], reasons)
            self.assertEqual({"portal"}, frontend_repository_names(context))

    def test_workspace_prompt_overrides_are_mode_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            scan_dir = workspace / "lumen" / "prompts" / "scan"
            delivery_dir = workspace / "lumen" / "prompts" / "delivery"
            scan_dir.mkdir(parents=True)
            delivery_dir.mkdir(parents=True)
            (workspace / "lumen" / "config").mkdir(exist_ok=True)
            (workspace / "lumen" / "config" / "common.json").write_text("{}\n", encoding="utf-8")
            (scan_dir / "manifest.json").write_text('{"snippets":["scan.md"]}\n', encoding="utf-8")
            (scan_dir / "scan.md").write_text("# Workspace Scan Prompt\n", encoding="utf-8")
            (delivery_dir / "manifest.json").write_text('{"snippets":["delivery.md"]}\n', encoding="utf-8")
            (delivery_dir / "delivery.md").write_text("# Workspace Delivery Prompt\n", encoding="utf-8")

            context = StoryContext(
                docs_dir=workspace,
                workspace_root=workspace,
                story_dir=workspace / "stories" / "demo",
                story_md=workspace / "stories" / "demo" / "story.md",
                technical_plan=workspace / "stories" / "demo" / "technical-plan.md",
                metadata_path=workspace / "stories" / "demo" / "metadata.json",
                metadata={},
                repos=[],
                branch_name="feature/DEMO-1",
                delivery_config={},
                workspace_config={},
            )

            self.assertIn("# Workspace Scan Prompt", compose_prompt(workspace / "lumen"))
            self.assertNotIn("Delivery Prompt", compose_prompt(workspace / "lumen"))
            self.assertEqual("# Workspace Delivery Prompt", compose_snippets(context))

    def test_scan_prompt_catalog_is_used_instead_of_full_inline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "lumen"
            scan_dir = workspace / "prompts" / "scan"
            scan_dir.mkdir(parents=True)
            (workspace / "config").mkdir(parents=True)
            (workspace / "config" / "common.json").write_text("{}\n", encoding="utf-8")
            (scan_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "inline": ["01-role-and-mission.md"],
                        "catalog": [
                            {
                                "file": "09-severity-guideline.md",
                                "title": "Severity guideline",
                                "description": "High Medium Low rules",
                                "when": "required",
                            },
                            {
                                "file": "02-pipeline.md",
                                "title": "Pipeline",
                                "description": "Scan sequence",
                                "when": "always",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (scan_dir / "01-role-and-mission.md").write_text("# Role And Mission\n\nScan role.\n", encoding="utf-8")
            (scan_dir / "09-severity-guideline.md").write_text("## Severity Guideline\n\nHigh only.\n", encoding="utf-8")
            (scan_dir / "02-pipeline.md").write_text("## Pipeline\n\nStep one.\n", encoding="utf-8")

            prompt = compose_prompt(workspace)
            self.assertIn("# Role And Mission", prompt)
            self.assertIn("# Scan Prompt Catalog", prompt)
            self.assertIn("09-severity-guideline.md", prompt)
            self.assertIn("REQUIRED", prompt)
            self.assertIn("Read when needed", prompt)
            self.assertNotIn("## Severity Guideline", prompt)
            self.assertNotIn("## Pipeline", prompt)

    def test_workspace_coding_guideline_overrides_cli_default_for_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            story_dir = workspace / "stories" / "NOVA-101-demo"
            story_dir.mkdir(parents=True)
            (workspace / "lumen" / "prompts" / "delivery").mkdir(parents=True)
            (workspace / "lumen" / "prompts" / "delivery" / "coding-guideline.md").write_text(
                "# Workspace Coding Guideline\n\nUse the local rule.\n",
                encoding="utf-8",
            )
            story_md = story_dir / "story.md"
            plan = story_dir / "technical-plan.md"
            metadata = story_dir / "metadata.json"
            story_md.write_text("# Story\n", encoding="utf-8")
            plan.write_text("# Plan\n", encoding="utf-8")
            metadata.write_text("{}\n", encoding="utf-8")
            context = StoryContext(
                docs_dir=workspace,
                workspace_root=workspace,
                story_dir=story_dir,
                story_md=story_md,
                technical_plan=plan,
                metadata_path=metadata,
                metadata={},
                repos=[],
                branch_name="feature/NOVA-101-demo",
                delivery_config={},
                workspace_config={},
            )

            from compose_delivery_prompt import render_context_block

            self.assertIn("Use the local rule.", render_context_block(context))

    def test_remediation_prompt_contains_only_failed_verification_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            story_dir = workspace / "stories" / "MBPAS-100-demo"
            story_dir.mkdir(parents=True)
            story_md = story_dir / "story.md"
            plan = story_dir / "technical-plan.md"
            metadata = story_dir / "metadata.json"
            story_md.write_text("# Story\n\nContext\n", encoding="utf-8")
            plan.write_text("# Plan\n\nApproved work\n", encoding="utf-8")
            metadata.write_text("{}\n", encoding="utf-8")
            result = workspace / "lumen" / "results" / "delivery-result.json"
            result.parent.mkdir(parents=True)
            result.write_text(
                json.dumps(
                    {
                        "remediation": {"attempt": 1, "max_attempts": 2},
                        "verification_results": [
                            {"label": "Full test suite", "status": "failed", "summary": "Context failed"},
                            {"label": "PMD", "status": "passed", "summary": "Passed"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            context = StoryContext(
                docs_dir=workspace,
                workspace_root=workspace,
                story_dir=story_dir,
                story_md=story_md,
                technical_plan=plan,
                metadata_path=metadata,
                metadata={},
                repos=[],
                branch_name="feature/MBPAS-100-demo",
                delivery_config={},
                workspace_config={},
            )

            prompt = compose_delivery_prompt(context, remediation=True)
            self.assertIn("# Verification Remediation Context", prompt)
            self.assertIn("Full test suite", prompt)
            self.assertNotIn('"label": "PMD"', prompt)

    def test_figma_mcp_is_disabled_even_when_explicitly_approved(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            story_dir = workspace / "stories" / "MBPAS-101-figma"
            story_dir.mkdir(parents=True)
            story_md, plan, metadata = story_dir / "story.md", story_dir / "technical-plan.md", story_dir / "metadata.json"
            story_md.write_text("# Story\n", encoding="utf-8")
            plan.write_text(
                "# Plan\n\n## Visual Delivery Contract\n\n### Design Source\n\n"
                "| Screen | Figma file | Node ID | Design context snapshot |\n"
                "|---|---|---|---|\n"
                "| Home | https://www.figma.com/design/demo | `12:34` | `assets/home.context.json` |\n",
                encoding="utf-8",
            )
            metadata.write_text("{}\n", encoding="utf-8")
            context = StoryContext(
                docs_dir=workspace, workspace_root=workspace, story_dir=story_dir, story_md=story_md,
                technical_plan=plan, metadata_path=metadata, metadata={}, repos=[], branch_name="feature/MBPAS-101-figma",
                delivery_config={"execution": {"approve_mcps": True}}, workspace_config={},
            )
            prompt = compose_delivery_prompt(context)
            self.assertIn("# Frontend Delivery Policy", prompt)
            self.assertNotIn("# Approved Figma Design Context", prompt)
            self.assertNotIn("Figma MCP access is explicitly approved for this delivery.", prompt)
            context.delivery_config = {"execution": {"approve_mcps": False}}
            self.assertNotIn("Figma MCP access is explicitly approved for this delivery.", compose_delivery_prompt(context))

    def test_quick_login_block_is_disabled_for_frontend_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            lumen = workspace / "lumen" / "config"
            lumen.mkdir(parents=True)
            (lumen / "repos.json").write_text(
                json.dumps(
                    {
                        "repositories": [
                            {
                                "name": "digital-platform-admin",
                                "path": str(workspace / "repos" / "digital-platform-admin"),
                                "runtime_profile": "web-review-only",
                                "runtime": {
                                    "platform": "web",
                                    "start_command": "yarn start:dev",
                                    "base_url": "http://127.0.0.1:3000",
                                    "auth_login_path": "/oauth-proxy-api/auth/admin/fake",
                                    "auth_login_field": "wiw",
                                    "visual_auth_credential": "TEST-WIW",
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            story_dir = workspace / "stories" / "MBPAS-200-login"
            story_dir.mkdir(parents=True)
            story_md = story_dir / "story.md"
            plan = story_dir / "technical-plan.md"
            metadata = story_dir / "metadata.json"
            story_md.write_text("# Story\n", encoding="utf-8")
            plan.write_text("# Plan\n", encoding="utf-8")
            metadata.write_text("{}\n", encoding="utf-8")
            context = StoryContext(
                docs_dir=workspace,
                workspace_root=workspace,
                story_dir=story_dir,
                story_md=story_md,
                technical_plan=plan,
                metadata_path=metadata,
                metadata={},
                repos=[RepoTarget("digital-platform-admin", workspace / "repos" / "digital-platform-admin", workspace / "lumen" / "worktrees" / "demo" / "digital-platform-admin", "master")],
                branch_name="feature/MBPAS-200-login",
                delivery_config={},
                workspace_config={},
            )
            prompt = compose_delivery_prompt(context)
            self.assertIn("# Frontend Delivery Policy", prompt)
            self.assertNotIn("# Quick Login", prompt)
            self.assertNotIn("POST http://127.0.0.1:3000/oauth-proxy-api/auth/admin/fake", prompt)
            self.assertNotIn("TEST-WIW", prompt)
            self.assertNotIn("LUMEN_VISUAL_AUTH_DIGITAL_PLATFORM_ADMIN", prompt)

    def test_remediation_attempt_archives_previous_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = Path(temp) / "delivery-result.json"
            result.write_text(
                json.dumps(
                    {
                        "delivery_status": "ready_for_finalize",
                        "run_id": "run-1",
                        "story_id": "DEMO-1",
                        "verification_results": [{"label": "Tests", "status": "failed"}],
                    }
                ),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "prepare_delivery_remediation.py"),
                    "--result",
                    str(result),
                    "--attempt",
                    "1",
                    "--max-attempts",
                    "2",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.read_text(encoding="utf-8"))
            self.assertEqual("in_progress", payload["delivery_status"])
            self.assertEqual([], payload["verification_results"])
            self.assertEqual("in_progress", payload["remediation"]["status"])
            self.assertEqual("run-1", payload["remediation"]["run_id"])
            self.assertEqual("DEMO-1", payload["remediation"]["story_id"])
            self.assertEqual("Tests", payload["remediation"]["attempts"][0]["failed_verification"][0]["label"])

            result.write_text(json.dumps({"delivery_status": "ready_for_finalize"}), encoding="utf-8")
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "prepare_delivery_remediation.py"),
                    "--result",
                    str(result),
                    "--restore",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            restored = json.loads(result.read_text(encoding="utf-8"))
            self.assertEqual(1, restored["remediation"]["attempt"])

    def test_remediation_prompt_reads_archived_failures_after_prepare(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            story_dir = workspace / "stories" / "MBPAS-100-demo"
            story_dir.mkdir(parents=True)
            story_md = story_dir / "story.md"
            plan = story_dir / "technical-plan.md"
            metadata = story_dir / "metadata.json"
            story_md.write_text("# Story\n\nContext\n", encoding="utf-8")
            plan.write_text("# Plan\n\nApproved work\n", encoding="utf-8")
            metadata.write_text("{}\n", encoding="utf-8")
            result = workspace / "lumen" / "results" / "delivery-result.json"
            result.parent.mkdir(parents=True)
            result.write_text(
                json.dumps(
                    {
                        "delivery_status": "ready_for_finalize",
                        "verification_results": [
                            {
                                "repository": "mbpass-data-proxy",
                                "label": "Language Grammar Check",
                                "status": "failed",
                                "summary": "compileJava FAILED",
                            },
                            {"repository": "mbpass-admin", "label": "PMD", "status": "passed"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "prepare_delivery_remediation.py"),
                    "--result",
                    str(result),
                    "--attempt",
                    "1",
                    "--max-attempts",
                    "2",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.read_text(encoding="utf-8"))
            self.assertEqual([], payload["verification_results"])

            context = StoryContext(
                docs_dir=workspace,
                workspace_root=workspace,
                story_dir=story_dir,
                story_md=story_md,
                technical_plan=plan,
                metadata_path=metadata,
                metadata={},
                repos=[],
                branch_name="feature/MBPAS-100-demo",
                delivery_config={},
                workspace_config={},
            )
            prompt = compose_delivery_prompt(context, remediation=True)
            self.assertIn("Language Grammar Check", prompt)
            self.assertIn("mbpass-data-proxy", prompt)
            self.assertNotIn('"label": "PMD"', prompt)

    def test_delivery_docs_sync_commits_only_story_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            remote = root / "remote.git"
            docs = root / "docs"
            subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
            subprocess.run(["git", "init", "-b", "main", str(docs)], check=True, capture_output=True)
            git(docs, "config", "user.email", "lumen@example.test")
            git(docs, "config", "user.name", "Lumen Test")
            (docs / ".gitignore").write_text("repos/\n", encoding="utf-8")
            story = docs / "stories" / "MBPAS-100-demo"
            story.mkdir(parents=True)
            (story / "story.md").write_text("# Story\n", encoding="utf-8")
            (story / "technical-plan.md").write_text("# Plan\n", encoding="utf-8")
            metadata = story / "metadata.json"
            metadata.write_text(
                json.dumps({"jiraKey": "MBPAS-100", "deliveryStatus": "not_started", "linkedRepos": ["service"]}),
                encoding="utf-8",
            )
            git(docs, "add", ".")
            git(docs, "commit", "-m", "Initialize story")
            git(docs, "remote", "add", "origin", str(remote))
            git(docs, "push", "-u", "origin", "main")

            service = docs / "repos" / "service"
            subprocess.run(["git", "init", "-b", "main", str(service)], check=True, capture_output=True)
            git(service, "config", "user.email", "lumen@example.test")
            git(service, "config", "user.name", "Lumen Test")
            (service / "README.md").write_text("service\n", encoding="utf-8")
            git(service, "add", "README.md")
            git(service, "commit", "-m", "Initialize service")
            metadata.write_text(
                json.dumps({"jiraKey": "MBPAS-100", "deliveryStatus": "dev_done", "linkedRepos": ["service"]}),
                encoding="utf-8",
            )
            unrelated = docs / "notes.md"
            unrelated.write_text("Leave me alone\n", encoding="utf-8")
            subprocess.run(
                [sys.executable, str(SCRIPTS / "sync_delivery_docs.py"), str(docs), "--story", "MBPAS-100-demo"],
                check=True,
                capture_output=True,
                text=True,
            )
            log = subprocess.run(
                ["git", "-C", str(docs), "log", "-1", "--format=%s"],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual("[lumon] #MBPAS-100 feat: update MBPAS-100 delivery status", log.stdout.strip())
            status = subprocess.run(
                ["git", "-C", str(docs), "status", "--short"],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual("?? notes.md", status.stdout.strip())

    def test_observatory_lists_all_stories_and_saves_story_docs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            remote = root / "remote.git"
            docs = root / "docs"
            workspace = docs / "lumen"
            subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
            subprocess.run(["git", "init", "-b", "main", str(docs)], check=True, capture_output=True)
            git(docs, "config", "user.email", "lumen@example.test")
            git(docs, "config", "user.name", "Lumen Test")
            (workspace / "config").mkdir(parents=True)
            (workspace / "config" / "workspace.json").write_text(json.dumps({"docs_repo": str(docs)}), encoding="utf-8")
            draft = docs / "stories" / "DRAFT-1"
            ready = docs / "stories" / "READY-1"
            snapshot = docs / "lumen" / "context" / "READY-1" / "jira-import.json"
            snapshot.parent.mkdir(parents=True)
            snapshot.write_text(
                json.dumps({"jira_key": "READY-1", "workitem": {"assignee": {"displayName": "Ada Lovelace"}}}),
                encoding="utf-8",
            )
            for story_dir, meta in (
                (draft, {"jiraKey": "DRAFT-1", "title": "Draft story", "businessStatus": "draft", "technicalStatus": "draft", "deliveryStatus": "not_started", "updatedAt": "2026-07-10", "jiraImportedAt": "2026-07-10T08:00:00Z"}),
                (ready, {"jiraKey": "READY-1", "title": "Ready story", "businessStatus": "ready", "technicalStatus": "approved", "deliveryStatus": "not_started", "linkedRepos": ["service"], "updatedAt": "2026-07-22T08:45:45Z", "jiraImportedAt": "2026-07-22T08:45:45Z", "jiraSnapshotFile": "lumen/context/READY-1/jira-import.json"}),
            ):
                story_dir.mkdir(parents=True)
                (story_dir / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
                (story_dir / "story.md").write_text("# Story\n\nHello\n", encoding="utf-8")
                (story_dir / "technical-plan.md").write_text("# Plan\n\nSteps\n", encoding="utf-8")
            unrelated = docs / "notes.md"
            unrelated.write_text("Leave me alone\n", encoding="utf-8")
            git(docs, "add", "stories", "lumen/config/workspace.json", "lumen/context")
            git(docs, "commit", "-m", "Initialize stories")
            git(docs, "remote", "add", "origin", str(remote))
            git(docs, "push", "-u", "origin", "main")

            listed = list_observatory_stories(workspace)
            self.assertEqual(["READY-1", "DRAFT-1"], [item["story"] for item in listed])
            by_story = {item["story"]: item for item in listed}
            self.assertEqual("2026-07-10", by_story["DRAFT-1"]["updatedAt"])
            self.assertEqual("2026-07-10T08:00:00Z", by_story["DRAFT-1"]["createdAt"])
            self.assertEqual("", by_story["DRAFT-1"]["assignee"])
            self.assertEqual("2026-07-22", by_story["READY-1"]["updatedAt"])
            self.assertEqual("Ada Lovelace", by_story["READY-1"]["assignee"])
            content = observatory_story_content(workspace, "DRAFT-1")
            self.assertIn("Hello", content["story_markdown"])
            result = save_observatory_story_content(workspace, "DRAFT-1", "# Story\n\nUpdated\n", "# Plan\n\nDone\n")
            self.assertTrue(result["ok"])
            self.assertEqual("[lumon] #DRAFT-1 feat: update DRAFT-1 story docs", result["subject"])
            log = subprocess.run(["git", "-C", str(docs), "log", "-1", "--format=%s"], check=True, capture_output=True, text=True)
            self.assertEqual("[lumon] #DRAFT-1 feat: update DRAFT-1 story docs", log.stdout.strip())
            status = subprocess.run(["git", "-C", str(docs), "status", "--short"], check=True, capture_output=True, text=True)
            self.assertEqual("?? notes.md", status.stdout.strip())
            self.assertEqual("# Story\n\nUpdated\n", (draft / "story.md").read_text(encoding="utf-8"))

    def test_docs_dir_resolves_relative_docs_repo_against_workspace_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "mbpass-workspace"
            workspace = root / "lumen"
            stories = root / "stories" / "DEMO-1"
            stories.mkdir(parents=True)
            (workspace / "config").mkdir(parents=True)
            (workspace / "config" / "workspace.json").write_text(
                json.dumps({"workspace_root": str(root), "docs_repo": ".", "layout": "nested"}),
                encoding="utf-8",
            )
            (stories / "metadata.json").write_text(
                json.dumps({"jiraKey": "DEMO-1", "title": "Demo", "businessStatus": "draft"}),
                encoding="utf-8",
            )
            previous = Path.cwd()
            try:
                os.chdir(temp)
                self.assertEqual(root.resolve(), dashboard_server.docs_dir_for_workspace(workspace))
                listed = list_observatory_stories(workspace)
            finally:
                os.chdir(previous)
            self.assertEqual(["DEMO-1"], [item["story"] for item in listed])

    def test_delivery_notification_uses_a_card_level_jira_link(self) -> None:
        renderer = load_delivery_notification_renderer()
        card = renderer.build_delivery_feishu_card(
            "delivery.started",
            {
                "jira_key": "MBPAS-1456",
                "delivery_status": "in_progress",
                "model": "cursor-grok-4.5-high",
                "branch": "feature/MBPAS-1456-demo",
                "repos_touched": [{"name": "mbpass-admin"}],
            },
            {
                "title": "Tailor-made audience setting",
                "jiraUrl": "https://inspire.atlassian.net/browse/MBPAS-1456",
            },
            Path("/tmp"),
        )
        rendered = json.dumps(card, ensure_ascii=False)
        self.assertEqual("MBPAS-1456 · Tailor-made audience setting", card["card"]["header"]["subtitle"]["content"])
        self.assertEqual(
            {"url": "https://inspire.atlassian.net/browse/MBPAS-1456"},
            card["card"]["card_link"],
        )
        self.assertIn("**Status:**", rendered)
        self.assertIn("**Model:**  `cursor-grok-4.5-high`", rendered)
        self.assertIn("**Scope:**", rendered)
        self.assertIn("**Branch:**", rendered)
        self.assertNotIn("Open MBPAS-1456", rendered)

    def test_completed_delivery_notification_includes_duration(self) -> None:
        renderer = load_delivery_notification_renderer()
        card = renderer.build_delivery_feishu_card(
            "delivery.dev_done",
            {
                "delivery_status": "completed",
                "started_at": "2026-07-13T11:35:00Z",
                "finished_at": "2026-07-13T11:49:25Z",
                "repos_touched": [],
            },
            {"title": "Demo"},
            Path("/tmp"),
        )
        overview = card["card"]["body"]["elements"][0]["content"]
        self.assertIn("**Duration:**  14m 25s", overview)

    def test_delivery_completion_keeps_completed_event_when_tracking_is_unconfigured(self) -> None:
        renderer = load_delivery_notification_renderer()
        with tempfile.TemporaryDirectory() as temp:
            docs = Path(temp) / "docs"
            workspace = docs / "lumen"
            story = docs / "stories" / "DEMO-127"
            (workspace / "config").mkdir(parents=True)
            (workspace / "results").mkdir(parents=True)
            story.mkdir(parents=True)
            (workspace / "config" / "delivery.json").write_text(
                json.dumps(
                    {
                        "notifications": {"feishu": {"enabled": True}},
                        "deployment_tracking": {"enabled": True, "provider": "jenkins", "jenkins": {"job": ""}},
                    }
                ),
                encoding="utf-8",
            )
            (story / "metadata.json").write_text(
                json.dumps({"jiraKey": "DEMO-127", "title": "Demo", "deliveryStatus": "in_progress"}),
                encoding="utf-8",
            )
            result = workspace / "results" / "delivery-result.json"
            result.write_text(
                json.dumps(
                    {
                        "workspace_root": str(docs),
                        "docs_dir": str(docs),
                        "story_path": "stories/DEMO-127",
                        "story_id": "DEMO-127",
                        "jira_key": "DEMO-127",
                        "delivery_status": "completed",
                    }
                ),
                encoding="utf-8",
            )
            events: list[str] = []

            def publish(**kwargs):
                events.append(str(kwargs.get("event_type")))
                return {"status": "sent"}

            with patch.dict(os.environ, {"FEISHU_WEBHOOK_URL": "https://example.test/hook"}), \
                    patch.object(renderer, "sync_delivery_jira", return_value={"status": "skipped"}), \
                    patch.object(renderer, "_publish_workflow_feishu", side_effect=publish), \
                    patch.object(sys, "argv", ["render-delivery-and-notify.py", str(result), "--event", "delivery.dev_done"]):
                self.assertEqual(0, renderer.main())

            self.assertEqual(["delivery.dev_done"], events)
            payload = json.loads(result.read_text(encoding="utf-8"))
            self.assertEqual("completed", payload["delivery_status"])

    def test_patch_started_notification_uses_runtime_context(self) -> None:
        renderer = load_delivery_notification_renderer()
        card = renderer.build_patch_feishu_card(
            "patch.started",
            {
                "jira_key": "MBPAS-1548",
                "jira_summary": "AMG PL system bug collection",
                "patch_status": "running",
                "model": "cursor-grok-4.5-high",
                "jira_status": "In Progress",
                "current_phase": "context",
            },
        )
        rendered = json.dumps(card, ensure_ascii=False)
        self.assertEqual("MBPAS-1548 · AMG PL system bug collection", card["card"]["header"]["subtitle"]["content"])
        self.assertEqual("Lumen Auto Patch · Started", card["card"]["header"]["title"]["content"])
        self.assertIn("**Model:**  `cursor-grok-4.5-high`", rendered)
        self.assertIn("Jira context", rendered)
        self.assertIn("bounded functional changes with explicit acceptance criteria", rendered)
        self.assertNotIn("No repository recorded", rendered)

    def test_patch_completed_notification_includes_changes_checks_and_publish(self) -> None:
        renderer = load_delivery_notification_renderer()
        card = renderer.build_patch_feishu_card(
            "patch.completed",
            {
                "jira_key": "MBPAS-1552",
                "jira_summary": "Assign the next order column",
                "patch_status": "completed",
                "model": "cursor-grok-4.5-high",
                "jira_status": "Done",
                "current_phase": "jira_notify",
                "branch": "patch/MBPAS-1552-order-column",
                "summary": "Use the next published order column.",
                "repos_touched": [{"name": "mbpass-business", "files_changed": ["src/OrderService.java"]}],
                "self_checks": [
                    {"label": "targeted test", "status": "passed", "summary": "Passed"},
                    {"label": "full suite", "status": "skipped", "summary": "Out of scope"},
                ],
                "publish_mode": "pr",
                "pr_urls": ["https://git.example.test/pull/14"],
            },
        )
        rendered = json.dumps(card, ensure_ascii=False)
        self.assertIn("**Change summary**", rendered)
        self.assertIn("src/OrderService.java", rendered)
        self.assertIn("✓ 1 passed · ✕ 0 failed · ⊘ 1 skipped", rendered)
        self.assertIn("[Open pull request](https://git.example.test/pull/14)", rendered)
        self.assertNotIn("Preparing", rendered)
        self.assertIn("wide_screen_mode", rendered)

    def test_patch_completed_notification_uses_progress_repositories_when_result_is_empty(self) -> None:
        renderer = load_delivery_notification_renderer()
        card = renderer.build_patch_feishu_card(
            "patch.completed",
            {
                "patch_status": "completed",
                "repos_touched": [],
                "repositories": [{"name": "mbpass-business"}],
            },
        )
        rendered = json.dumps(card, ensure_ascii=False)
        self.assertIn("mbpass-business", rendered)
        self.assertNotIn("Preparing", rendered)

    def test_patch_skipped_notification_is_not_presented_as_completed(self) -> None:
        renderer = load_delivery_notification_renderer()
        card = renderer.build_patch_feishu_card(
            "patch.skipped",
            {
                "jira_key": "MBPAS-1548",
                "jira_summary": "Bounded multi-repository change",
                "patch_status": "skipped",
                "summary": "No code change was made.",
                "repositories": [{"name": "mbpass-admin"}],
            },
        )
        rendered = json.dumps(card, ensure_ascii=False)
        self.assertEqual("Lumen Auto Patch · Skipped", card["card"]["header"]["title"]["content"])
        self.assertIn("**Reason**", rendered)
        self.assertIn("No code was changed", rendered)
        self.assertNotIn("Lumen Auto Patch · Completed", rendered)

    def test_patch_blocked_notification_makes_question_prominent(self) -> None:
        renderer = load_delivery_notification_renderer()
        card = renderer.build_patch_feishu_card(
            "patch.blocked",
            {
                "jira_key": "MBPAS-1548",
                "jira_summary": "AMG PL system bug collection",
                "patch_status": "blocked",
                "jira_status": "Block (migrated)",
                "current_phase": "repository",
                "summary": "Jira context does not identify exactly one registered repository.",
                "question": "Which registered repository should Auto Patch modify?",
            },
        )
        rendered = json.dumps(card, ensure_ascii=False)
        self.assertIn("Action required", rendered)
        self.assertIn("**Question**", rendered)
        self.assertIn("Which registered repository should Auto Patch modify?", rendered)
        self.assertIn("Reply in Jira", rendered)

    def test_patch_notification_persists_feishu_result_to_history(self) -> None:
        renderer = load_delivery_notification_renderer()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lumen = root / "lumen"
            results = lumen / "results"
            history = lumen / "history" / "patch"
            results.mkdir(parents=True)
            history.mkdir(parents=True)
            (results / "patch-progress.json").write_text(json.dumps({
                "run_id": "20260803-135213",
                "jira_key": "MBPAS-1548",
                "jira_summary": "AMG PL system bug collection",
                "current_phase": "repository",
                "patch_status": "blocked",
            }), encoding="utf-8")
            result = results / "patch-result.json"
            result.write_text(json.dumps({
                "schema_version": "1.0",
                "patch_status": "blocked",
                "jira_key": "MBPAS-1548",
                "summary": "Repository mapping is ambiguous.",
                "question": "Which repository should be modified?",
            }), encoding="utf-8")
            history_file = history / "20260803-135213.json"
            history_file.write_text(json.dumps({"progress": {}, "patch": {}}), encoding="utf-8")

            with patch.dict(os.environ, {"LUMEN_DRY_RUN": "1"}), patch.object(
                sys, "argv", ["render-delivery-and-notify.py", str(result), "--event", "patch.blocked"]
            ):
                self.assertEqual(0, renderer.main())

            self.assertEqual("dry_run", json.loads(result.read_text(encoding="utf-8"))["feishu"]["status"])
            saved_history = json.loads(history_file.read_text(encoding="utf-8"))
            self.assertEqual("dry_run", saved_history["patch"]["feishu"]["status"])
            self.assertEqual("dry_run", json.loads((results / "patch-progress.json").read_text(encoding="utf-8"))["feishu"]["status"])

    def test_patch_history_exposes_jira_card_title(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            history = workspace / "history" / "patch"
            history.mkdir(parents=True)
            (history / "run-1.json").write_text(json.dumps({
                "progress": {"jira_summary": "AMG PL system bug collection"},
                "patch": {"jira_key": "MBPAS-1548", "summary": "Repository mapping is ambiguous.", "patch_status": "blocked"},
            }), encoding="utf-8")

            runs = patch_payload(workspace)["runs"]

            self.assertEqual("MBPAS-1548", runs[0]["jira_key"])
            self.assertEqual("AMG PL system bug collection", runs[0]["jira_summary"])

    def test_patch_current_falls_back_to_latest_history_when_idle(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            history = workspace / "history" / "patch"
            results = workspace / "results"
            history.mkdir(parents=True)
            results.mkdir()
            phases = [{"id": "capture", "label": "Capture", "status": "completed", "detail": "Captured"}]
            (history / "run-1.json").write_text(json.dumps({
                "progress": {"jira_key": "MBPAS-1552", "jira_summary": "Offline publish order collision", "phases": phases},
                "patch": {"patch_status": "completed", "summary": "Assigned the next banner order."},
            }), encoding="utf-8")
            (results / "patch-progress.json").write_text(json.dumps({"patch_status": "idle"}), encoding="utf-8")
            (results / "patch-result.json").write_text(json.dumps({"patch_status": "idle"}), encoding="utf-8")

            current = patch_payload(workspace)["current"]

            self.assertEqual("MBPAS-1552", current["jira_key"])
            self.assertEqual("completed", current["patch_status"])
            self.assertEqual("completed", current["stages"][0]["status"])

    def test_patch_history_delete_removes_record_and_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "lumen"
            history = workspace / "history" / "patch"
            log = workspace / "logs" / "patch" / "run-1.log"
            history.mkdir(parents=True)
            log.parent.mkdir(parents=True)
            log.write_text("agent output\n", encoding="utf-8")
            history_file = history / "run-1.json"
            history_file.write_text(json.dumps({"progress": {"log_file": str(log)}, "patch": {"jira_key": "DEMO-1"}}), encoding="utf-8")

            server = DashboardServer.__new__(DashboardServer)
            removed = server.delete_patch_history(workspace, "run-1")

            self.assertEqual("run-1", removed["run_id"])
            self.assertFalse(history_file.exists())
            self.assertFalse(log.exists())

    def test_patch_block_writes_comment_even_when_transition_is_unavailable(self) -> None:
        runner = load_patch_runner()
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            progress = {"run_id": "run-1", "jira_key": "MBPAS-1548", "phases": [], "failures": []}
            with patch.object(runner, "transition_issue", side_effect=RuntimeError("transition unavailable")), \
                    patch.object(runner, "add_comment") as add_comment, \
                    patch.object(runner, "notify"), \
                    patch.object(runner, "remove_worktrees"):
                runner.block(workspace, progress, "Which repository?", "Repository mapping is ambiguous")

            add_comment.assert_called_once()
            self.assertEqual("failed", progress["jira"]["transition"])
            self.assertEqual("sent", progress["jira"]["comment"])

    def test_patch_repository_mapping_uses_unique_local_code_match(self) -> None:
        runner = load_patch_runner()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            payments = root / "payments-service"
            profile = root / "profile-service"
            payments.mkdir()
            profile.mkdir()
            (payments / "GatewayTimeout.java").write_text(
                "payment gateway timeout retry authorization\n", encoding="utf-8"
            )
            repositories = [
                {"name": "payments-service", "path": str(payments)},
                {"name": "profile-service", "path": str(profile)},
            ]
            item = {"key": "MBPAS-2000", "fields": {
                "summary": "Payment gateway timeout during authorization",
                "description": "Retry the authorization request after a gateway timeout.",
            }}
            with patch.object(runner, "repo_registry", return_value=repositories):
                selected, reason = runner.select_repository(root, item)

            self.assertEqual("payments-service", selected["name"])
            self.assertIn("local code match", reason)
            self.assertIn("payment", reason)

    def test_patch_repository_mapping_blocks_tied_local_matches_with_candidates(self) -> None:
        runner = load_patch_runner()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / "payments-service"
            second = root / "orders-service"
            first.mkdir()
            second.mkdir()
            for repository in (first, second):
                (repository / "gateway.txt").write_text("payment gateway timeout\n", encoding="utf-8")
            repositories = [
                {"name": "payments-service", "path": str(first)},
                {"name": "orders-service", "path": str(second)},
            ]
            item = {"key": "MBPAS-2001", "fields": {
                "summary": "Payment gateway timeout",
                "description": "The gateway timeout affects the payment flow.",
            }}
            with patch.object(runner, "repo_registry", return_value=repositories):
                selected, reason = runner.select_repository(root, item)

            self.assertIsNone(selected)
            self.assertIn("high-confidence", reason)
            self.assertIn("payments-service", reason)
            self.assertIn("orders-service", reason)
            self.assertIn("payments-service", runner.blocked_comment(reason, "Which repository should be modified?"))

    def test_patch_repository_mapping_accepts_multiple_repositories_from_latest_human_reply(self) -> None:
        runner = load_patch_runner()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repositories = [
                {"name": "digital-platform-admin", "path": str(root / "digital-platform-admin")},
                {"name": "mbpass-admin", "path": str(root / "mbpass-admin")},
                {"name": "mbpass-data-proxy", "path": str(root / "mbpass-data-proxy")},
            ]
            item = {"key": "MBPAS-1548", "fields": {"summary": "Existing bug collection", "comment": {"comments": [
                {"body": "Lumen Auto Patch · Blocked"},
                {"body": "digital-platform-admin\nmbpass-admin\nmbpass-data-proxy"},
                {"body": "Lumen Auto Patch · Blocked"},
            ]}}}
            with patch.object(runner, "repo_registry", return_value=repositories):
                selected, reason = runner.select_repositories(root, item)

            self.assertEqual(
                ["digital-platform-admin", "mbpass-admin", "mbpass-data-proxy"],
                [repository["name"] for repository in selected],
            )
            self.assertIn("Latest human Jira reply explicitly selected", reason)

    def test_installer_copies_delivery_coding_guideline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lumen_home = root / "lumen-home"
            bin_dir = root / "bin"
            completed = subprocess.run(
                ["bash", str(REPO_ROOT / "install.sh")],
                check=True,
                capture_output=True,
                text=True,
                env={**os.environ, "LUMEN_HOME": str(lumen_home), "LUMEN_BIN_DIR": str(bin_dir)},
            )
            self.assertEqual(0, completed.returncode)
            self.assertTrue((lumen_home / "lib" / "standards" / "coding-guideline.md").is_file())

    def test_scheduled_delivery_selects_only_ready_and_approved_unstarted_stories(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            stories = Path(temp) / "stories"
            ready = stories / "MBPAS-100-ready"
            changed = stories / "MBPAS-101-changed"
            active = stories / "MBPAS-102-active"
            for directory, metadata in (
                (ready, {"jiraKey": "MBPAS-100", "businessStatus": "ready", "technicalStatus": "approved", "deliveryStatus": "not_started"}),
                (changed, {"jiraKey": "MBPAS-101", "businessStatus": "changed", "technicalStatus": "approved", "deliveryStatus": "not_started"}),
                (active, {"jiraKey": "MBPAS-102", "businessStatus": "ready", "technicalStatus": "approved", "deliveryStatus": "in_progress"}),
            ):
                directory.mkdir(parents=True)
                (directory / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

            selected = story_candidates(Path(temp))
            self.assertEqual([ready], [story for story, _ in selected])

    def test_scheduler_reads_twg_list_shaped_workitem_status(self) -> None:
        import delivery_scheduler

        original_ready = delivery_scheduler.twg_ready
        original_run = delivery_scheduler.run_twg
        original_refresh = delivery_scheduler.refresh_twg_auth
        try:
            delivery_scheduler.twg_ready = lambda: (True, "")
            delivery_scheduler.refresh_twg_auth = lambda force=True: (True, "")
            delivery_scheduler.run_twg = lambda _args: (
                0,
                json.dumps({"data": [{"key": "MBPAS-100", "status": {"name": "Ready for Dev"}}]}),
            )
            self.assertEqual("Ready for Dev", current_jira_status("MBPAS-100"))
        finally:
            delivery_scheduler.twg_ready = original_ready
            delivery_scheduler.refresh_twg_auth = original_refresh
            delivery_scheduler.run_twg = original_run

    def test_scheduler_reads_status_field_from_twg_workitem(self) -> None:
        import delivery_scheduler

        original_ready = delivery_scheduler.twg_ready
        original_run = delivery_scheduler.run_twg
        original_refresh = delivery_scheduler.refresh_twg_auth
        try:
            delivery_scheduler.twg_ready = lambda: (True, "")
            delivery_scheduler.refresh_twg_auth = lambda force=True: (True, "")
            delivery_scheduler.run_twg = lambda _args: (
                0,
                json.dumps({"data": [{"key": "MBPAS-1491", "fields": {"status": {"name": "In Progress"}}}]}),
            )
            self.assertEqual("In Progress", current_jira_status("MBPAS-1491"))
        finally:
            delivery_scheduler.twg_ready = original_ready
            delivery_scheduler.refresh_twg_auth = original_refresh
            delivery_scheduler.run_twg = original_run

    def test_schedule_cli_forwards_all_jira_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lumen_home = root / "lumen-home"
            scripts = lumen_home / "lib" / "scripts"
            scripts.mkdir(parents=True)
            shutil.copy2(REPO_ROOT / "lib" / "scripts" / "projects_registry.py", scripts / "projects_registry.py")

            docs = root / "docs"
            (docs / "lumen" / "config").mkdir(parents=True)
            (docs / "lumen" / "config" / "common.json").write_text(json.dumps({"project": {"display_name": "Demo"}}), encoding="utf-8")
            (lumen_home / "projects.json").write_text(json.dumps({"projects": [{"slug": "demo", "workspace": str(docs / "lumen")}]}) + "\n", encoding="utf-8")

            captured = root / "scheduler-args.json"
            (scripts / "delivery_scheduler.py").write_text(
                "import json, os, sys\nfrom pathlib import Path\nPath(os.environ['CAPTURE']).write_text(json.dumps(sys.argv[1:]))\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "bin" / "lumen"),
                    "delivery",
                    "schedule",
                    "run",
                    "--project",
                    "demo",
                    "--jira-status",
                    "Backlog",
                    "--jira-status",
                    "To Do",
                    "--jira-status",
                    "In Progress",
                ],
                check=False,
                capture_output=True,
                text=True,
                env={**os.environ, "LUMEN_HOME": str(lumen_home), "CAPTURE": str(captured)},
            )
            self.assertEqual(0, completed.returncode, completed.stderr or completed.stdout)
            args = json.loads(captured.read_text(encoding="utf-8"))
            self.assertEqual(
                ["Backlog", "To Do", "In Progress"],
                [args[index + 1] for index, value in enumerate(args) if value == "--jira-status"],
            )

    def test_delivery_statuses_support_multiple_values_and_legacy_csv(self) -> None:
        self.assertEqual(["To Do", "Backlog", "In Progress"], normalize_statuses(["To Do", "Backlog", "In Progress"]))
        self.assertEqual(["To Do", "Backlog"], normalize_statuses("To Do,Backlog", ()))
        self.assertEqual(["To Do"], normalize_statuses(["To Do", "to do"], ()))

    def test_launchd_interval_accepts_every_n_minutes_cron(self) -> None:
        self.assertEqual(5, interval_minutes_from_cron("*/5 * * * *"))
        self.assertIsNone(interval_minutes_from_cron("0 9 * * *"))

    def test_scan_launchd_translates_common_cron_expressions(self) -> None:
        self.assertEqual(
            ({"StartInterval": 300}, "every 5 minutes"),
            launchd_schedule_from_cron("*/5 * * * *"),
        )
        self.assertEqual(
            ({"StartCalendarInterval": {"Minute": 0, "Hour": 9}}, "daily at 09:00"),
            launchd_schedule_from_cron("0 9 * * *"),
        )

    def test_completed_delivery_worktrees_are_removed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            repo = workspace / "repos" / "service"
            remote = workspace / "remote.git"
            subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
            git(repo, "config", "user.email", "lumen@example.test")
            git(repo, "config", "user.name", "Lumen Test")
            (repo / "README.md").write_text("base\n", encoding="utf-8")
            git(repo, "add", "README.md")
            git(repo, "commit", "-m", "initial commit")
            git(repo, "remote", "add", "origin", str(remote))
            git(repo, "push", "-u", "origin", "main")
            story_dir = workspace / "stories" / "MBPAS-999-cleanup"
            story_dir.mkdir(parents=True)
            (story_dir / "story.md").write_text("# Story\n\n" + "Business context. " * 10, encoding="utf-8")
            (story_dir / "technical-plan.md").write_text("# Plan\n\n" + "Implementation detail. " * 10, encoding="utf-8")
            (story_dir / "metadata.json").write_text(
                json.dumps(
                    {
                        "jiraKey": "MBPAS-999",
                        "businessStatus": "ready",
                        "technicalStatus": "approved",
                        "linkedRepos": ["service"],
                    }
                ),
                encoding="utf-8",
            )
            context = load_workspace_config(workspace)
            self.assertEqual(workspace.resolve(), context[0])
            target = RepoTarget("service", repo, workspace / "lumen" / "worktrees" / "MBPAS-999" / "service")
            ok, detail = ensure_feature_worktree(target, "feature/MBPAS-999-cleanup", workspace, {"jiraKey": "MBPAS-999"}, story_dir)
            self.assertTrue(ok, detail)
            self.assertTrue(target.worktree_path.exists())

            cleanup_delivery_worktrees(workspace, "MBPAS-999")
            self.assertFalse(target.worktree_path.exists())
            metadata = json.loads((story_dir / "metadata.json").read_text(encoding="utf-8"))
            self.assertIn("deliveryWorktreesCleanedAt", metadata)

    def test_project_registry_remove_clears_registration_and_default_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace = root / "project" / ".lumen"
            (workspace / "config").mkdir(parents=True)
            (workspace / "config" / "common.json").write_text(
                json.dumps({"project": {"display_name": "Legacy MBPass"}}), encoding="utf-8"
            )
            lumen_home = root / "lumen-home"
            env = {**os.environ, "LUMEN_HOME": str(lumen_home)}

            added = subprocess.run(
                [sys.executable, str(PROJECTS_REGISTRY), "add", str(workspace)],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            project = json.loads(added.stdout)
            subprocess.run(
                [sys.executable, str(PROJECTS_REGISTRY), "set-default", project["slug"]],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            subprocess.run(
                [sys.executable, str(PROJECTS_REGISTRY), "remove", project["slug"]],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )

            registry = json.loads((lumen_home / "projects.json").read_text(encoding="utf-8"))
            self.assertEqual([], registry["projects"])
            config = json.loads((lumen_home / "config.json").read_text(encoding="utf-8"))
            self.assertNotIn("default_project_id", config)
            self.assertTrue(workspace.exists())

    def test_project_registry_can_reclaim_a_slug_after_old_project_removal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lumen_home = root / "lumen-home"
            env = {**os.environ, "LUMEN_HOME": str(lumen_home)}
            workspaces = [root / "old" / ".lumen", root / "current" / ".lumen"]
            for workspace in workspaces:
                (workspace / "config").mkdir(parents=True)
                (workspace / "config" / "common.json").write_text(
                    json.dumps({"project": {"display_name": "MBPass"}}), encoding="utf-8"
                )

            old = subprocess.run(
                [sys.executable, str(PROJECTS_REGISTRY), "add", str(workspaces[0])],
                check=True, capture_output=True, text=True, env=env,
            )
            current = subprocess.run(
                [sys.executable, str(PROJECTS_REGISTRY), "add", str(workspaces[1])],
                check=True, capture_output=True, text=True, env=env,
            )
            old_project = json.loads(old.stdout)
            current_project = json.loads(current.stdout)
            self.assertEqual("mbpass-2", current_project["slug"])
            subprocess.run(
                [sys.executable, str(PROJECTS_REGISTRY), "remove", old_project["slug"]],
                check=True, capture_output=True, text=True, env=env,
            )
            renamed = subprocess.run(
                [sys.executable, str(PROJECTS_REGISTRY), "set-slug", current_project["slug"], "--slug", "mbpass"],
                check=True, capture_output=True, text=True, env=env,
            )
            self.assertEqual("mbpass", json.loads(renamed.stdout)["slug"])

    def test_metadata_is_the_single_delivery_gate_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            story = root / "story.md"
            plan = root / "technical-plan.md"
            story.write_text("# Story\n\n" + "Business context. " * 10, encoding="utf-8")
            plan.write_text("# Technical Plan\n\n" + "Implementation detail. " * 10, encoding="utf-8")
            errors = validate_story_gates(
                {"businessStatus": "ready", "technicalStatus": "approved"}, story, plan
            )
            self.assertEqual([], errors)

    def test_story_worktrees_support_parallel_stories_without_touching_dirty_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            remote = root / "remote.git"
            source = root / "source"
            workspace = root / "workspace"
            subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
            subprocess.run(["git", "init", "-b", "main", str(source)], check=True, capture_output=True)
            git(source, "config", "user.email", "lumen@example.test")
            git(source, "config", "user.name", "Lumen Test")
            (source / "README.md").write_text("base\n", encoding="utf-8")
            git(source, "add", "README.md")
            git(source, "commit", "-m", "initial commit")
            git(source, "remote", "add", "origin", str(remote))
            git(source, "push", "-u", "origin", "main")
            (source / "README.md").write_text("dirty local edit\n", encoding="utf-8")

            repo = RepoTarget("service", source, workspace / "lumen" / "worktrees" / "service")
            metadata = {"jiraKey": "DEMO-123"}
            story_dir = root / "stories" / "demo-story"
            story_dir.mkdir(parents=True)
            expected = story_worktrees_dir(workspace, metadata, story_dir) / "service"

            ok, detail = ensure_feature_worktree(
                repo,
                "feature/DEMO-123-demo",
                workspace,
                metadata,
                story_dir,
            )

            self.assertTrue(ok, detail)
            self.assertEqual(expected.resolve(), repo.worktree_path)
            self.assertEqual("dirty local edit\n", (source / "README.md").read_text(encoding="utf-8"))
            self.assertEqual("base\n", (repo.worktree_path / "README.md").read_text(encoding="utf-8"))
            self.assertTrue((repo.worktree_path / ".git").exists())

            second_repo = RepoTarget("service", source, workspace / "lumen" / "worktrees" / "service")
            second_metadata = {"jiraKey": "DEMO-124"}
            second_story = root / "stories" / "another-story"
            second_story.mkdir()
            ok, detail = ensure_feature_worktree(
                second_repo,
                "feature/DEMO-124-another",
                workspace,
                second_metadata,
                second_story,
            )

            self.assertTrue(ok, detail)
            self.assertNotEqual(repo.worktree_path, second_repo.worktree_path)
            self.assertTrue(second_repo.worktree_path.is_dir())
            self.assertEqual("dirty local edit\n", (source / "README.md").read_text(encoding="utf-8"))

    def test_reused_story_worktree_fast_forwards_to_latest_base_branch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            remote = root / "remote.git"
            source = root / "source"
            workspace = root / "workspace"
            subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
            subprocess.run(["git", "init", "-b", "main", str(source)], check=True, capture_output=True)
            git(source, "config", "user.email", "lumen@example.test")
            git(source, "config", "user.name", "Lumen Test")
            (source / "README.md").write_text("base-1\n", encoding="utf-8")
            git(source, "add", "README.md")
            git(source, "commit", "-m", "base 1")
            git(source, "remote", "add", "origin", str(remote))
            git(source, "push", "-u", "origin", "main")

            story_dir = root / "stories" / "DEMO-126"
            story_dir.mkdir(parents=True)
            metadata = {"jiraKey": "DEMO-126"}
            target = RepoTarget(
                "service",
                source,
                workspace / "lumen" / "worktrees" / "DEMO-126" / "service",
            )
            ok, detail = ensure_feature_worktree(
                target,
                "feature/DEMO-126-sync",
                workspace,
                metadata,
                story_dir,
            )
            self.assertTrue(ok, detail)

            (source / "README.md").write_text("base-2\n", encoding="utf-8")
            git(source, "commit", "-am", "base 2")
            git(source, "push", "origin", "main")

            reused = RepoTarget("service", source, target.worktree_path)
            ok, detail = ensure_feature_worktree(
                reused,
                "feature/DEMO-126-sync",
                workspace,
                metadata,
                story_dir,
            )
            self.assertTrue(ok, detail)
            self.assertIn("synced origin/main", detail)
            self.assertEqual("base-2\n", (reused.worktree_path / "README.md").read_text(encoding="utf-8"))

    def test_story_worktree_uses_explicit_base_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            workspace = root / "workspace"
            subprocess.run(["git", "init", "-b", "main", str(source)], check=True, capture_output=True)
            git(source, "config", "user.email", "lumen@example.test")
            git(source, "config", "user.name", "Lumen Test")
            (source / "README.md").write_text("baseline\n", encoding="utf-8")
            git(source, "add", "README.md")
            git(source, "commit", "-m", "baseline")
            baseline = subprocess.run(
                ["git", "-C", str(source), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            (source / "README.md").write_text("later\n", encoding="utf-8")
            git(source, "commit", "-am", "later")

            story_dir = root / "stories" / "DEMO-125"
            story_dir.mkdir(parents=True)
            target = RepoTarget("service", source, workspace / "lumen" / "worktrees" / "DEMO-125" / "service")
            ok, detail = ensure_feature_worktree(
                target,
                "feature/DEMO-125-baseline",
                workspace,
                {"jiraKey": "DEMO-125", "baseCommit": baseline},
                story_dir,
            )

            self.assertTrue(ok, detail)
            self.assertIn(baseline, detail)
            self.assertEqual(baseline, subprocess.run(
                ["git", "-C", str(target.worktree_path), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip())
            self.assertEqual("baseline\n", (target.worktree_path / "README.md").read_text(encoding="utf-8"))

    def test_delivery_notification_can_skip_feishu_for_one_run(self) -> None:
        renderer = load_delivery_notification_renderer()
        with tempfile.TemporaryDirectory() as temp:
            docs = Path(temp) / "docs"
            workspace = docs / "lumen"
            story = docs / "stories" / "DEMO-126"
            (workspace / "config").mkdir(parents=True)
            (workspace / "results").mkdir(parents=True)
            story.mkdir(parents=True)
            (workspace / "config" / "delivery.json").write_text(
                json.dumps({"notifications": {"feishu": {"enabled": True}}}), encoding="utf-8"
            )
            (story / "metadata.json").write_text(
                json.dumps({"jiraKey": "DEMO-126", "title": "Demo", "deliveryStatus": "in_progress"}),
                encoding="utf-8",
            )
            result = workspace / "results" / "delivery-result.json"
            result.write_text(json.dumps({
                "workspace_root": str(docs),
                "docs_dir": str(docs),
                "story_path": "stories/DEMO-126",
                "story_id": "DEMO-126",
                "jira_key": "DEMO-126",
                "delivery_status": "in_progress",
            }), encoding="utf-8")

            with patch.dict(os.environ, {"LUMEN_SKIP_FEISHU": "1", "FEISHU_WEBHOOK_URL": "https://example.test/hook"}), \
                    patch.object(renderer, "sync_delivery_jira", return_value={"status": "skipped"}), \
                    patch.object(renderer, "send_feishu") as send_feishu, \
                    patch.object(sys, "argv", ["render-delivery-and-notify.py", str(result)]):
                self.assertEqual(0, renderer.main())

            payload = json.loads(result.read_text(encoding="utf-8"))
            self.assertEqual("skipped", payload["feishu"]["status"])
            self.assertEqual("LUMEN_SKIP_FEISHU enabled", payload["feishu"]["detail"])
            send_feishu.assert_not_called()

    def test_docs_repo_is_the_default_workspace_and_discovers_repos_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            docs = root / "docs"
            repo = docs / "repos" / "service"
            (docs / "stories").mkdir(parents=True)
            (docs / "lumen" / "config").mkdir(parents=True)
            subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
            (docs / "lumen" / "config" / "workspace.json").write_text(
                """{
  "schema_version": "1.0",
  "layout": "nested",
  "workspace_root": ".",
  "docs_repo": ".",
  "repos_dir": "repos",
  "repositories": []
}
""",
                encoding="utf-8",
            )

            workspace_root, config = load_workspace_config(docs)
            repos = discover_git_repos(workspace_root, config)

            self.assertEqual(docs.resolve(), workspace_root)
            self.assertEqual("nested", config["layout"])
            self.assertEqual(repo.resolve(), repos["service"])

    def test_delivery_dashboard_renders_archived_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            history = workspace / "lumen" / "history" / "delivery"
            history.mkdir(parents=True)
            (history / "DEMO-1.json").write_text(
                """{
  "run_id": "DEMO-1",
  "delivery": {"delivery_status": "completed", "story_id": "DEMO-1", "pr_urls": []},
  "progress": {"delivery_status": "completed", "repositories": []},
  "log_file": ""
}
""",
                encoding="utf-8",
            )
            html, data = render(workspace)
            self.assertTrue(html.is_file())
            self.assertTrue(data.is_file())
            self.assertIn("DEMO-1", data.read_text(encoding="utf-8"))

    def test_delivery_dashboard_recovers_story_title_after_docs_workspace_moves(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            docs = Path(temp) / "docs"
            workspace = docs / "lumen"
            history = workspace / "history" / "delivery"
            story = docs / "stories" / "DEMO-1-example"
            history.mkdir(parents=True)
            story.mkdir(parents=True)
            (story / "metadata.json").write_text('{"title":"Example delivery story"}\n', encoding="utf-8")
            (history / "DEMO-1.json").write_text(
                json.dumps({
                    "delivery": {
                        "delivery_status": "completed",
                        "story_id": "DEMO-1",
                        "story_path": "stories/DEMO-1-example",
                        "docs_dir": "/obsolete/docs",
                    },
                    "progress": {},
                }),
                encoding="utf-8",
            )

            runs = delivery_payload(workspace)["runs"]

            self.assertEqual("Example delivery story", runs[0]["story_title"])

    def test_delivery_dashboard_prefers_progress_story_title_while_running(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            docs = Path(temp) / "docs"
            workspace = docs / "lumen"
            results = workspace / "results"
            story = docs / "stories" / "DEMO-2-example"
            results.mkdir(parents=True)
            story.mkdir(parents=True)
            (story / "metadata.json").write_text('{"title":"Running delivery story"}\n', encoding="utf-8")
            (results / "delivery-progress.json").write_text(
                json.dumps({
                    "run_id": "run-2",
                    "delivery_status": "in_progress",
                    "story_id": "DEMO-2",
                    "story_path": "stories/DEMO-2-example",
                    "story_title": "Running delivery story",
                    "jira_key": "DEMO-2",
                    "docs_dir": str(docs),
                    "started_at": "2026-07-25T03:00:00Z",
                }),
                encoding="utf-8",
            )
            (results / "delivery-result.json").write_text(
                json.dumps({
                    "delivery_status": "completed",
                    "story_id": "OLD-1",
                    "story_path": "stories/missing",
                    "docs_dir": str(docs),
                }),
                encoding="utf-8",
            )

            current = delivery_payload(workspace)["current"]

            self.assertEqual("DEMO-2", current["jira_key"])
            self.assertEqual("Running delivery story", current["story_title"])

    def test_feishu_notification_toggle_updates_common_and_delivery_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "lumen"
            (workspace / "config").mkdir(parents=True)
            (workspace / "config" / "common.json").write_text("{}\n", encoding="utf-8")
            (workspace / "config" / "delivery.json").write_text(
                json.dumps({"notifications": {"feishu": {"enabled": True}}}),
                encoding="utf-8",
            )

            payload = save_feishu_notifications(workspace, False)

            self.assertFalse(payload["feishu_notifications_enabled"])
            self.assertFalse(feishu_notifications_enabled(workspace))
            common = json.loads((workspace / "config" / "common.json").read_text(encoding="utf-8"))
            delivery = json.loads((workspace / "config" / "delivery.json").read_text(encoding="utf-8"))
            self.assertFalse(common["notifications"]["feishu"]["enabled"])
            self.assertFalse(delivery["notifications"]["feishu"]["enabled"])

    def test_dashboard_findings_are_sorted_by_creation_time_descending(self) -> None:
        path = SCRIPTS / "render-dashboard.py"
        spec = importlib.util.spec_from_file_location("render_dashboard_sort_test", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Unable to load dashboard renderer")
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)

        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "lumen"
            (workspace / "config").mkdir(parents=True)
            (workspace / "state").mkdir(parents=True)
            (workspace / "results").mkdir(parents=True)
            (workspace / "config" / "common.json").write_text("{}\n", encoding="utf-8")
            (workspace / "config" / "repos.json").write_text('{"repositories":[]}\n', encoding="utf-8")
            (workspace / "state" / "issue-registry.json").write_text(
                json.dumps({
                    "issues": [
                        {"id": "ISSUE-1", "title": "Older open", "status": "open", "first_seen_at": "2026-07-01T00:00:00Z", "last_seen_at": "2026-07-20T00:00:00Z"},
                        {"id": "ISSUE-2", "title": "Newest resolved", "status": "resolved", "first_seen_at": "2026-07-22T00:00:00Z", "last_seen_at": "2026-07-22T00:00:00Z"},
                        {"id": "ISSUE-3", "title": "Middle open", "status": "open", "first_seen_at": "2026-07-10T00:00:00Z", "last_seen_at": "2026-07-11T00:00:00Z"},
                        {"id": "ISSUE-4", "title": "Newest open", "status": "pr_open", "first_seen_at": "2026-07-20T00:00:00Z", "last_seen_at": "2026-07-21T00:00:00Z"},
                        {"id": "ISSUE-5", "title": "Ignored", "status": "ignored", "first_seen_at": "2026-07-21T00:00:00Z", "last_seen_at": "2026-07-21T00:00:00Z"},
                    ]
                }),
                encoding="utf-8",
            )

            issues = renderer.build_payload(workspace)["issues"]

            self.assertEqual(
                ["ISSUE-4", "ISSUE-3", "ISSUE-1", "ISSUE-2", "ISSUE-5"],
                [item["id"] for item in issues],
            )

    def test_init_merges_delivery_assets_into_an_existing_scan_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            common = workspace / "lumen" / "config" / "common.json"
            common.parent.mkdir(parents=True)
            common.write_text('{"scan": "preserved"}\n', encoding="utf-8")

            with redirect_stdout(StringIO()):
                init_docs(workspace, "Demo", "DEMO-001", force=False, merge=True, no_example=True)

            self.assertEqual('{"scan": "preserved"}\n', common.read_text(encoding="utf-8"))
            self.assertTrue((workspace / "AGENTS.md").is_file())
            self.assertFalse((workspace / "stories" / "mini-web-welcome").exists())
            self.assertTrue((workspace / "lumen" / "config" / "delivery.json").is_file())
            self.assertTrue((workspace / "lumen" / "config" / "delivery.example.json").is_file())
            ignore = (workspace / ".gitignore").read_text(encoding="utf-8")
            self.assertIn("lumen/config/delivery.json", ignore)

    def test_agent_skills_install_is_project_scoped_and_preserves_unmanaged_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            (workspace / "lumen" / "config").mkdir(parents=True)
            (workspace / "lumen" / "config" / "common.json").write_text("{}\n", encoding="utf-8")

            install_agent_skills(str(workspace), ["all"], force=False)

            self.assertTrue((workspace / "lumen" / "skills" / "lumen-business-loop" / "references" / "workflow.md").is_file())
            self.assertTrue((workspace / "lumen" / "skills" / "lumen-jira-story-import" / "SKILL.md").is_file())
            self.assertIn("allow_implicit_invocation: false", (workspace / ".agents" / "openai.yaml").read_text(encoding="utf-8"))
            self.assertFalse((workspace / ".cursor" / "commands" / "lumen-technical-loop.md").exists())

            install_agent_skills(str(workspace), ["cursor"], force=False)
            self.assertTrue((workspace / ".cursor" / "commands" / "lumen-technical-loop.md").exists())
            install_agent_skills(str(workspace), ["all"], force=False)
            self.assertFalse((workspace / ".cursor" / "commands" / "lumen-technical-loop.md").exists())

            unmanaged = workspace / ".claude" / "skills" / "lumen-business-loop" / "SKILL.md"
            unmanaged.write_text("my workflow\n", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                install_agent_skills(str(workspace), ["claude"], force=False)

    def test_import_jira_story_creates_a_draft_and_detects_jira_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            (workspace / "stories").mkdir(parents=True)
            (workspace / "templates").mkdir()
            (workspace / "templates" / "technical-plan.md").write_text("# Technical Plan: <Story Title>\n", encoding="utf-8")
            (workspace / "lumen" / "config").mkdir(parents=True)
            (workspace / "lumen" / "config" / "common.json").write_text('{"notifications":{"jira":{"site":"example.atlassian.net"}}}\n', encoding="utf-8")
            payload = {"data": {"key": "DEMO-123", "fields": {"summary": "Imported checkout", "description": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Existing Jira context."}]}]}, "issuetype": {"name": "Story"}, "updated": "2026-07-18T00:00:00Z"}}}
            original_ready, original_run = import_jira_story.twg_ready, import_jira_story.run_twg
            import_jira_story.twg_ready = lambda: (True, "")
            import_jira_story.run_twg = lambda args: (0, json.dumps(payload))
            try:
                story_dir = import_jira_story.import_story(workspace, "demo-123")
                metadata = json.loads((story_dir / "metadata.json").read_text(encoding="utf-8"))
                self.assertEqual("DEMO-123", metadata["jiraKey"])
                self.assertEqual("draft", metadata["businessStatus"])
                self.assertEqual("https://example.atlassian.net/browse/DEMO-123", metadata["jiraUrl"])
                self.assertIn("Existing Jira context.", (story_dir / "story.md").read_text(encoding="utf-8"))
                self.assertTrue((workspace / metadata["jiraSnapshotFile"]).is_file())
                metadata["businessStatus"] = "ready"
                metadata["technicalStatus"] = "approved"
                (story_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
                import_jira_story.import_story(workspace, "DEMO-123")
                unchanged = json.loads((story_dir / "metadata.json").read_text(encoding="utf-8"))
                self.assertEqual("ready", unchanged["businessStatus"])
                payload["data"]["fields"]["description"]["content"][0]["content"][0]["text"] = "Changed Jira context."
                import_jira_story.import_story(workspace, "DEMO-123")
                changed = json.loads((story_dir / "metadata.json").read_text(encoding="utf-8"))
                self.assertEqual("changed", changed["jiraSyncStatus"])
                self.assertEqual("ready", changed["businessStatus"])
                self.assertEqual("draft", changed["technicalStatus"])
                self.assertIn("Existing Jira context.", (story_dir / "story.md").read_text(encoding="utf-8"))
                import_jira_story.import_story(workspace, "DEMO-123")
                still_changed = json.loads((story_dir / "metadata.json").read_text(encoding="utf-8"))
                self.assertEqual("changed", still_changed["jiraSyncStatus"])
            finally:
                import_jira_story.twg_ready, import_jira_story.run_twg = original_ready, original_run

    def test_repos_directory_is_shared_with_auto_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            repo = workspace / "repos" / "service"
            (workspace / "lumen" / "config").mkdir(parents=True)
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)

            repositories = sync_scan_repositories(workspace)
            saved = json.loads((workspace / "lumen" / "config" / "repos.json").read_text(encoding="utf-8"))

            self.assertEqual("service", repositories[0]["name"])
            self.assertEqual(str(repo.resolve()), saved["repositories"][0]["path"])


if __name__ == "__main__":
    unittest.main()
