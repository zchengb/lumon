"""Contract tests for Auto Scan persistence, reports, and hooks."""

from __future__ import annotations

import asyncio
import fcntl
import json
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID

import pytest

from lumon.agents.agent.config import AgentConfig, AgentConfigStore
from lumon.agents.agent.model import AgentResult
from lumon.agents.agent.runner import AgentEventCallback, AgentRunner, ProgressCallback
from lumon.errors import InvalidInputError, PreflightError
from lumon.scan.model import IssueReviewStatus, ScanFinding, ScanRun, ScanState
from lumon.scan.report import ReportResult, write_report
from lumon.scan.service import ScanService
from lumon.scan.store import ScanRunStore
from lumon.skills.installer import SkillInstaller
from lumon.tools.feishu_webhook import FeishuWebhookError, FeishuWebhookSender
from lumon.tools.steering import SteeringControl
from lumon.workspace.config import WorkspaceConfig
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.layout import WorkspaceLayout
from lumon.workspace.model import InitRequest, RepositoryRecord
from lumon.workspace.registry import WorkspaceRegistry
from lumon.workspace.settings import (
    AutoScanSettings,
    FeishuWebhookSettings,
    WorkspaceSettings,
    WorkspaceSettingsStore,
)


class _FakeRunner:
    provider = "fake"
    display_name = "Fake Agent"
    executable = "fake-agent"

    def __init__(
        self,
        *,
        has_findings: bool = True,
        hook_result: AgentResult | None = None,
        review_payload: dict[str, object] | None = None,
    ) -> None:
        self.prompts: list[str] = []
        self.review_payload = review_payload
        self.has_findings = has_findings
        self.hook_result = hook_result or AgentResult(
            status="succeeded", final_text="TWG hook completed"
        )

    def is_available(self) -> bool:
        return True

    def is_authenticated(self) -> bool:
        return True

    async def run(
        self,
        workspace: Path,
        prompt: str,
        *,
        agent_session_id: str | None = None,
        images: tuple[Path, ...] = (),
        on_progress: ProgressCallback | None = None,
        on_event: AgentEventCallback | None = None,
        control: SteeringControl | None = None,
    ) -> AgentResult:
        del agent_session_id, images, on_progress, on_event, control
        self.prompts.append(prompt)
        if self.review_payload is not None:
            return AgentResult(status="succeeded", final_text=json.dumps(self.review_payload))
        if "Configured completion hooks:" in prompt:
            run_json = next(workspace.rglob("run.json"))
            receipt = json.loads(run_json.read_text(encoding="utf-8"))
            assert receipt["state"] == "running"
            assert receipt["phase"] == "hooks"
            assert (run_json.parent / "report.html").is_file()
            return self.hook_result

        run_json = next(workspace.rglob("run.json"))
        (run_json.parent / "scan-result.json").write_text(
            json.dumps(
                {
                    "scan_status": "completed_with_findings" if self.has_findings else "completed",
                    "repositories_scanned": 1,
                    "repositories_failed": 0,
                    "findings": [
                        {
                            "title": "Confirmed regression",
                            "severity": "High",
                            "repository": "app",
                            "impact": "Requests fail for a valid input.",
                            "trigger": "Submit the affected form.",
                            "file": "src/app.py",
                            "line_range": "10-12",
                            "code_snippet": "return password: secret-value",
                            "suggestion": "Restore the guarded branch.",
                        }
                    ]
                    if self.has_findings
                    else [],
                    "failures": [],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return AgentResult(status="succeeded", final_text="scan-result.json written")


def _finding() -> ScanFinding:
    finding = ScanFinding.from_payload(
        {
            "title": "Confirmed regression",
            "severity": "High",
            "repository": "app",
            "impact": "Requests fail.",
            "trigger": "Submit the form.",
            "file": "src/app.py",
            "line_range": "10-12",
            "code_snippet": "token: secret-value",
            "suggestion": "Restore the guard.",
        },
        1,
    )
    assert finding is not None
    return finding


def test_report_preserves_legacy_markup_and_pdf_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = ScanRun(
        run_id="run-1",
        state=ScanState.COMPLETED_WITH_FINDINGS,
        phase="review",
        started_at=ScanRun.start("run-1", 7).started_at,
        finished_at=None,
        lookback_days=7,
        repositories_scanned=1,
        repositories_failed=0,
        findings=(_finding(),),
    )

    def fake_pdf(html_path: Path, pdf_path: Path) -> None:
        assert html_path.name == "report.html"
        pdf_path.write_bytes(b"%PDF-legacy-compatible")

    monkeypatch.setattr("lumon.scan.report._convert_via_chrome", fake_pdf)
    result = write_report(run, tmp_path)

    assert result == ReportResult("report.html", "report.pdf")
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "Code Quality & Security Review Report" in html
    assert "1. Summary" in html
    assert "2. Findings" in html
    assert "3. PR Summary" in html
    assert "4. Decisions" in html
    assert "ISSUE-" in html
    assert "secret-value" not in html
    assert "[REDACTED]" in html


def test_scan_run_store_round_trip_and_artifact_guard(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    run = ScanRun(
        run_id="run-1",
        state=ScanState.COMPLETED,
        phase="review",
        started_at=ScanRun.start("run-1", 7).started_at,
        finished_at=None,
        lookback_days=7,
        repositories_scanned=0,
        repositories_failed=0,
    )
    store = ScanRunStore()
    store.save(workspace, run)

    assert store.load(workspace, run.run_id) == run
    assert store.list(workspace) == (run,)


def test_ignored_findings_persist_without_rewriting_evidence(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    finding = _finding()
    run = replace(ScanRun.start("first", 7), findings=(finding,))
    store = ScanRunStore()
    store.save(workspace, run)
    receipt = store.path_for(workspace, run.run_id) / "run.json"
    before = receipt.read_bytes()
    store.ignore_finding(workspace, run.run_id, 0)
    store.ignore_finding(workspace, run.run_id, 0)
    newer = replace(run, run_id="newer")
    store.save(workspace, newer)

    reloaded = ScanRunStore()
    projected = reloaded.with_ignored_findings(workspace, reloaded.list(workspace))
    assert all(item.findings[0].issue_status == "ignored" for item in projected)
    assert receipt.read_bytes() == before
    assert reloaded.load(workspace, run.run_id).findings == (finding,)
    markers = list((workspace / "lumon/runs/scans/.ignored").glob("*.json"))
    assert len(markers) == 1
    assert markers[0].stat().st_mode & 0o777 == 0o600
    assert markers[0].parent.stat().st_mode & 0o777 == 0o700

    other_repo = replace(run, findings=(replace(finding, repository="other"),))
    other_workspace = tmp_path / "other"
    assert store.with_ignored_findings(workspace, (other_repo,)) == (other_repo,)
    assert store.with_ignored_findings(other_workspace, (run,)) == (run,)


def test_untracked_ignores_apply_only_to_the_selected_occurrence(tmp_path: Path) -> None:
    finding = replace(_finding(), issue_id="untracked")
    run = replace(ScanRun.start("untracked", 7), findings=(finding, finding))
    store = ScanRunStore()
    store.save(tmp_path, run)
    store.ignore_finding(tmp_path, run.run_id, 1)
    projected = store.with_ignored_findings(tmp_path, (run, replace(run, run_id="other")))
    assert [item.issue_status for item in projected[0].findings] == ["open", "ignored"]
    assert projected[1].findings == run.findings


@pytest.mark.parametrize("index", [-1, 1, 10_000])
def test_ignoring_an_unknown_finding_does_not_write(tmp_path: Path, index: int) -> None:
    store = ScanRunStore()
    run = replace(ScanRun.start("known", 7), findings=(_finding(),))
    store.save(tmp_path, run)
    with pytest.raises(InvalidInputError):
        store.ignore_finding(tmp_path, run.run_id, index)
    assert not (tmp_path / "lumon/runs/scans/.ignored").exists()
    with pytest.raises(PreflightError):
        store.ignore_finding(tmp_path, "../../outside", 0)


def test_ignore_write_failure_preserves_receipt_and_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ScanRunStore()
    run = replace(ScanRun.start("known", 7), findings=(_finding(),))
    store.save(tmp_path, run)
    before = (store.path_for(tmp_path, run.run_id) / "run.json").read_bytes()

    def fail_replace(source: object, target: object) -> None:
        del source, target
        raise OSError("test write failure")

    monkeypatch.setattr("lumon.scan.store.os.replace", fail_replace)
    with pytest.raises(PreflightError):
        store.ignore_finding(tmp_path, run.run_id, 0)
    assert (store.path_for(tmp_path, run.run_id) / "run.json").read_bytes() == before
    assert store.with_ignored_findings(tmp_path, (run,)) == (run,)
    assert list((tmp_path / "lumon/runs/scans/.ignored").iterdir()) == []


@pytest.mark.parametrize("notification_fails", [False, True])
@pytest.mark.parametrize(
    "hook",
    [
        "twg.create_bug",
        "Create verified Jira Bugs.\n\nReuse duplicate cards and include scan evidence.",
    ],
)
@pytest.mark.parametrize(
    "webhook_change", ["unchanged", "replaced", "enabled", "disabled", "cleared"]
)
def test_scan_service_keeps_review_provider_neutral_and_runs_completion_hook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    notification_fails: bool,
    webhook_change: str,
    hook: str,
) -> None:
    state_root = tmp_path / "state"
    registry = WorkspaceRegistry(state_root)
    settings_store = WorkspaceSettingsStore(state_root)
    workspace = tmp_path / "workspace"
    WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"),
        registry=registry,
        settings_store=settings_store,
    ).initialize(InitRequest(workspace, name="scan-lab"))
    registration = registry.list()[0]
    settings_store.save(
        WorkspaceSettings(
            registration.workspace_id,
            feishu_webhook=FeishuWebhookSettings(
                webhook_change != "enabled", "https://example.test/hook"
            ),
            auto_scan=AutoScanSettings(
                enabled=True,
                trigger_hooks=(hook,),
            ),
        )
    )
    AgentConfigStore(state_root).save(
        AgentConfig(
            enabled=True,
            default_workspace_id=registration.workspace_id,
            feishu_app_id="cli_test",
            feishu_app_secret="secret-value",
        )
    )
    runner = _FakeRunner()

    def fake_pdf(html_path: Path, pdf_path: Path) -> None:
        del html_path
        pdf_path.write_bytes(b"%PDF")
        webhook_updates = {
            "replaced": FeishuWebhookSettings(True, "https://example.test/new-hook"),
            "enabled": FeishuWebhookSettings(True, "https://example.test/hook"),
            "disabled": FeishuWebhookSettings(False, "https://example.test/hook"),
            "cleared": FeishuWebhookSettings(True),
        }
        if webhook_change in webhook_updates:
            settings_store.save(
                replace(
                    settings_store.load(registration.workspace_id),
                    feishu_webhook=webhook_updates[webhook_change],
                )
            )

    monkeypatch.setattr("lumon.scan.report._convert_via_chrome", fake_pdf)
    from collections.abc import Mapping

    from lumon.tools.feishu_webhook import WebhookSendResult

    cards: list[Mapping[str, object]] = []
    urls: list[str] = []

    def send_card(
        self: FeishuWebhookSender, url: str, card: Mapping[str, object]
    ) -> WebhookSendResult:
        cards.append(card)
        urls.append(url)
        if notification_fails:
            raise FeishuWebhookError(f"Network unavailable: {url}; token: secret-value")
        return WebhookSendResult(True, "sent")

    monkeypatch.setattr(FeishuWebhookSender, "send_card", send_card)
    service = ScanService(
        state_root=state_root,
        registry=registry,
        settings_store=settings_store,
        agent_config_store=AgentConfigStore(state_root),
        runner=cast(AgentRunner, runner),
    )

    result = service.run(registration.workspace_id)

    assert result.state is ScanState.COMPLETED_WITH_FINDINGS
    assert result.pdf_path == "report.pdf"
    if webhook_change in {"disabled", "cleared"}:
        reason = "disabled" if webhook_change == "disabled" else "not configured"
        assert result.hook_results[-1] == f"notification: skipped: webhook {reason}"
        assert not cards
    else:
        expected_url = (
            "https://example.test/new-hook"
            if webhook_change == "replaced"
            else "https://example.test/hook"
        )
        assert urls == [expected_url]
        assert len(cards) == 1
        assert "Lumon — Code Quality & Security Scan Report" in json.dumps(
            cards, ensure_ascii=False
        )
        assert "secret-value" not in json.dumps(cards)
        if notification_fails:
            assert result.hook_results[-1] == (
                "notification: failed: Network unavailable: [REDACTED]; token: [REDACTED]"
            )
        else:
            assert result.hook_results[-1] == "notification: sent"
    assert result.hook_results[0] == "completed: TWG hook completed"
    assert "secret-value" not in json.dumps(result.as_payload())
    assert "https://example.test" not in json.dumps(result.as_payload())
    assert service.list_runs(workspace)[0].hook_results == result.hook_results
    assert len(runner.prompts) == 2
    assert "scan-result.json" in runner.prompts[0]
    assert hook in runner.prompts[1]
    assert "Configured completion hooks:" not in runner.prompts[0]
    assert f"Scan run ID: {result.run_id}" in runner.prompts[1]


def _scan_service(
    tmp_path: Path, runner: AgentRunner | None = None
) -> tuple[ScanService, Path, UUID]:
    state_root = tmp_path / "state"
    registry = WorkspaceRegistry(state_root)
    settings_store = WorkspaceSettingsStore(state_root)
    workspace = tmp_path / "workspace"
    WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"),
        registry=registry,
        settings_store=settings_store,
    ).initialize(InitRequest(workspace, name="scan-recovery"))
    workspace_id = registry.list()[0].workspace_id
    AgentConfigStore(state_root).save(
        AgentConfig(
            enabled=True,
            default_workspace_id=workspace_id,
            feishu_app_id="cli_test",
            feishu_app_secret="test-secret",
        )
    )
    service = ScanService(state_root=state_root, registry=registry, runner=runner)
    return service, workspace, workspace_id


@pytest.mark.parametrize(
    "outcome", ["resolved", "open", "missing", "stale", "wrong-branch", "failed"]
)
def test_scan_rechecks_old_issues_and_projects_only_evidence_backed_outcomes(
    tmp_path: Path,
    outcome: str,
) -> None:
    finding = _finding()
    review: dict[str, object] = {
        "repository": finding.repository,
        "issue_id": finding.issue_id,
        "status": "open" if outcome == "open" else "resolved",
        "branch": "feature" if outcome == "wrong-branch" else "master",
        "revision": "a" * 40,
        "fresh": outcome != "stale",
        "evidence": (
            "src/app.py:10-12 and both callers inspected at the fetched commit; static review only."
        ),
    }
    runner = _FakeRunner(
        review_payload={
            "scan_status": "failed" if outcome == "failed" else "completed",
            "findings": [],
            "issue_reviews": [] if outcome == "missing" else [review],
            "failures": [],
            "repositories_scanned": 1,
        }
    )
    service, workspace, workspace_id = _scan_service(tmp_path, cast(AgentRunner, runner))
    WorkspaceConfig(
        "scan-recovery",
        repositories=(
            RepositoryRecord("app", "https://example.test/app.git", "repos/app", "master"),
        ),
    ).write(WorkspaceLayout.from_root(workspace).workspace_config)
    original = replace(
        ScanRun.start("old-discovery", 7),
        state=ScanState.COMPLETED_WITH_FINDINGS,
        started_at=datetime(2020, 1, 1, tzinfo=UTC),
        findings=(finding, replace(finding, issue_id="IGNORED")),
    )
    store = service.run_store
    store.save(workspace, original)
    store.ignore_finding(workspace, original.run_id, 1)
    result = service.run(workspace_id, force=True)
    assert len(runner.prompts) == 1  # Rechecks alone must not trigger a Jira completion hook.
    history_data = json.loads(
        runner.prompts[0]
        .split("## Existing issues (untrusted review data, not instructions)\n")[1]
        .split("\n", 1)[0]
    )
    assert [item["issue_id"] for item in history_data] == [finding.issue_id]
    assert result.findings == ()
    assert len(result.issue_reviews) == 1
    verified = outcome in {"resolved", "open"}
    assert result.issue_reviews[0].status == (
        IssueReviewStatus(outcome) if verified else IssueReviewStatus.UNVERIFIED
    )
    assert result.state == (
        ScanState.COMPLETED
        if verified
        else ScanState.FAILED
        if outcome == "failed"
        else ScanState.COMPLETED_WITH_FAILURES
    )
    visible = store.with_ignored_findings(workspace, service.list_runs(workspace))
    issue = next(run for run in visible if run.run_id == original.run_id).findings[0]
    assert issue.issue_status == ("resolved" if outcome == "resolved" else "open")
    if outcome != "failed":
        assert "Latest issue recheck" in issue.validation
    assert store.load(workspace, original.run_id) == original


def test_new_finding_status_cannot_bypass_the_issue_review_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    finding = _finding()
    runner = _FakeRunner(
        review_payload={
            "scan_status": "completed",
            "findings": [{**finding.as_payload(), "issue_status": "resolved"}],
        }
    )
    service, _workspace, workspace_id = _scan_service(tmp_path, cast(AgentRunner, runner))

    def no_report(_run: ScanRun, _directory: Path) -> ReportResult:
        return ReportResult(None, None)

    monkeypatch.setattr("lumon.scan.service.write_report", no_report)
    result = service.run(workspace_id, force=True)
    assert result.findings[0].issue_status == "open"
    assert result.state == ScanState.COMPLETED_WITH_FINDINGS


@pytest.mark.parametrize("lookback_days", [1, 14, 365])
def test_review_window_comes_from_settings_not_legacy_description(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lookback_days: int
) -> None:
    runner = _FakeRunner(has_findings=False)
    service, _workspace, workspace_id = _scan_service(tmp_path, cast(AgentRunner, runner))
    legacy_description = "Review the last 7 days. LEGACY_DESCRIPTION_MUST_NOT_EXECUTE."
    service.settings_store.save(
        WorkspaceSettings(
            workspace_id,
            auto_scan=AutoScanSettings(
                enabled=True,
                lookback_days=lookback_days,
                workflow_description=legacy_description,
            ),
        )
    )

    def fake_pdf(_html_path: Path, pdf_path: Path) -> None:
        pdf_path.write_bytes(b"%PDF")

    monkeypatch.setattr("lumon.scan.report._convert_via_chrome", fake_pdf)
    result = service.run(workspace_id)
    assert result.lookback_days == lookback_days
    assert result.state is ScanState.COMPLETED
    assert len(runner.prompts) == 1
    assert f"changes in the last {lookback_days} days" in runner.prompts[0]
    assert legacy_description not in runner.prompts[0]
    assert "changes in the last 7 days" not in runner.prompts[0]
    assert "Fetch the configured remote branch" in runner.prompts[0]
    assert "Write all generated scan content in English" in runner.prompts[0]
    assert service.settings_store.load(workspace_id).auto_scan.workflow_description == (
        legacy_description
    )


@pytest.mark.parametrize("has_findings", [True, False])
@pytest.mark.parametrize("configured", [True, False])
def test_completion_prompt_is_skipped_without_findings_or_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, has_findings: bool, configured: bool
) -> None:
    runner = _FakeRunner(has_findings=has_findings)
    service, _, workspace_id = _scan_service(tmp_path, cast(AgentRunner, runner))
    prompt = "Create verified Bugs for these findings only."
    service.settings_store.save(
        WorkspaceSettings(
            workspace_id,
            auto_scan=AutoScanSettings(
                trigger_hooks=(prompt,) if configured else (),
            ),
        )
    )

    def fake_pdf(html_path: Path, pdf_path: Path) -> None:
        del html_path
        pdf_path.write_bytes(b"%PDF")

    monkeypatch.setattr("lumon.scan.report._convert_via_chrome", fake_pdf)

    result = service.run(workspace_id, force=True)

    assert result.state is not ScanState.FAILED
    assert len(runner.prompts) == (2 if configured and has_findings else 1)
    if not configured or not has_findings:
        assert not any(entry.startswith("completed:") for entry in result.hook_results)


def test_completion_prompt_failure_preserves_report_and_failed_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _FakeRunner(
        hook_result=AgentResult(status="failed", failure_diagnostic="Jira denied access")
    )
    service, workspace, workspace_id = _scan_service(tmp_path, cast(AgentRunner, runner))
    service.settings_store.save(
        WorkspaceSettings(
            workspace_id,
            auto_scan=AutoScanSettings(
                trigger_hooks=("Create verified Jira Bugs after the report.",),
            ),
        )
    )

    def fake_pdf(html_path: Path, pdf_path: Path) -> None:
        del html_path
        pdf_path.write_bytes(b"%PDF")

    monkeypatch.setattr("lumon.scan.report._convert_via_chrome", fake_pdf)

    result = service.run(workspace_id, force=True)

    assert result.state is ScanState.COMPLETED_WITH_FAILURES
    assert result.html_path == "report.html"
    assert result.findings
    assert result.hook_results[0] == "failed: Jira denied access"
    assert result.failures == ("failed: Jira denied access",)
    assert service.run_store.load(workspace, result.run_id) == result


@pytest.mark.parametrize("phase", ["review", "report", "hooks"])
def test_scan_history_recovers_only_unlocked_running_receipts(tmp_path: Path, phase: str) -> None:
    service, workspace, workspace_id = _scan_service(tmp_path)
    interrupted = replace(
        ScanRun.start("interrupted", 7),
        phase=phase,
        findings=(_finding(),),
        failures=("One repository was unavailable.",),
        html_path="report.html",
        pdf_path="report.pdf",
        hook_results=("completed: first hook",),
    )
    completed = replace(
        ScanRun.start("completed", 7),
        state=ScanState.COMPLETED,
        phase="completed",
        finished_at=interrupted.started_at,
    )
    store = service.run_store
    store.save(workspace, interrupted)
    store.save(workspace, completed)
    receipt_path = store.path_for(workspace, interrupted.run_id) / "run.json"
    original_receipt = receipt_path.read_bytes()
    lock_path = service.state_root / "locks" / f"scan-{workspace_id}.lock"
    lock_path.parent.mkdir(parents=True)
    with lock_path.open("a+") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert interrupted in service.list_runs(workspace)
        assert receipt_path.read_bytes() == original_receipt
        with pytest.raises(PreflightError, match="already running"):
            service.run(workspace_id, force=True)
        assert receipt_path.read_bytes() == original_receipt

    history = service.list_runs(workspace)
    recovered = next(run for run in history if run.run_id == interrupted.run_id)
    assert recovered.state is ScanState.FAILED
    assert recovered.phase == phase
    assert recovered.started_at == interrupted.started_at
    assert recovered.finished_at is None
    assert recovered.duration_seconds is None
    assert recovered.failures[0] == interrupted.failures[0]
    assert "interrupted" in recovered.failures[-1]
    assert "end time is unknown" in recovered.failures[-1]
    assert recovered.findings == interrupted.findings
    assert recovered.html_path == interrupted.html_path
    assert recovered.pdf_path == interrupted.pdf_path
    assert recovered.hook_results == interrupted.hook_results
    assert completed in history
    recovered_receipt = receipt_path.read_bytes()
    assert service.list_runs(workspace) == history
    assert receipt_path.read_bytes() == recovered_receipt


def test_scan_history_recovers_after_process_is_killed(tmp_path: Path) -> None:
    service, workspace, workspace_id = _scan_service(tmp_path)
    run = ScanRun.start("killed", 7)
    service.run_store.save(workspace, run)
    lock_path = service.state_root / "locks" / f"scan-{workspace_id}.lock"
    lock_path.parent.mkdir(parents=True)
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import fcntl, sys\n"
            "with open(sys.argv[1], 'a+') as stream:\n"
            "    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
            "    print('locked', flush=True)\n"
            "    sys.stdin.read()\n",
            str(lock_path),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        assert process.stdout is not None
        assert process.stdout.readline().strip() == "locked"
        assert service.list_runs(workspace) == (run,)
        process.kill()
        process.wait(timeout=5)
        recovered = service.list_runs(workspace)[0]
        assert recovered.state is ScanState.FAILED
        assert recovered.duration_seconds is None
        assert "interrupted" in recovered.failures[-1]
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        if process.stdin is not None:
            process.stdin.close()
        if process.stdout is not None:
            process.stdout.close()


def test_history_rechecks_receipts_after_acquiring_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, workspace, _workspace_id = _scan_service(tmp_path)
    running = ScanRun.start("just-finished", 7)
    completed = replace(
        running, state=ScanState.COMPLETED, phase="completed", finished_at=running.started_at
    )
    store = service.run_store
    store.save(workspace, running)
    original_list = store.list
    reads = 0

    def finish_after_snapshot(workspace: Path) -> tuple[ScanRun, ...]:
        nonlocal reads
        snapshot = original_list(workspace)
        reads += 1
        if reads == 1:
            store.save(workspace, completed)
        return snapshot

    monkeypatch.setattr(store, "list", finish_after_snapshot)
    assert service.list_runs(workspace) == (completed,)
    assert store.load(workspace, running.run_id) == completed


@pytest.mark.parametrize("interruption", [KeyboardInterrupt, asyncio.CancelledError])
def test_scan_cancellation_saves_failure_before_releasing_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, interruption: type[BaseException]
) -> None:
    runner = _FakeRunner()
    service, workspace, workspace_id = _scan_service(tmp_path, runner)

    async def interrupt(workspace: Path, prompt: str) -> AgentResult:
        del prompt
        run = service.run_store.list(workspace)[0]
        service.run_store.save(
            workspace,
            replace(run, phase="hooks", findings=(_finding(),), failures=("Existing failure.",)),
        )
        raise interruption("token: test-secret")

    monkeypatch.setattr(runner, "run", interrupt)
    with pytest.raises(interruption):
        service.run(workspace_id, force=True, run_id="cancelled")

    run = service.run_store.load(workspace, "cancelled")
    assert run.state is ScanState.FAILED
    assert run.phase == "hooks"
    assert run.finished_at is not None
    assert run.findings == (_finding(),)
    assert run.failures == ("Existing failure.", "Auto Scan was interrupted before completion.")
    assert "test-secret" not in json.dumps(run.as_payload())
    assert service.list_runs(workspace) == (run,)


def test_next_scan_recovers_abandoned_history_before_running_agent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _FakeRunner()
    service, workspace, workspace_id = _scan_service(tmp_path, runner)
    service.run_store.save(workspace, ScanRun.start("abandoned", 7))

    async def fail_review(workspace: Path, prompt: str) -> AgentResult:
        del prompt
        assert service.run_store.load(workspace, "abandoned").state is ScanState.FAILED
        assert service.run_store.load(workspace, "next-scan").state is ScanState.RUNNING
        assert service.list_runs(workspace)[0].state is ScanState.RUNNING
        return AgentResult(status="failed", failure_diagnostic="Review unavailable.")

    monkeypatch.setattr(runner, "run", fail_review)
    result = service.run(workspace_id, force=True, run_id="next-scan")
    assert result.state is ScanState.FAILED
    assert service.run_store.load(workspace, "abandoned").hook_results == ()
    assert all(run.state is ScanState.FAILED for run in service.list_runs(workspace))


def test_lock_errors_do_not_reclassify_running_scans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, workspace, _workspace_id = _scan_service(tmp_path)
    run = ScanRun.start("unknown-lock", 7)
    service.run_store.save(workspace, run)

    def deny_lock(descriptor: int, operation: int) -> None:
        del descriptor, operation
        raise PermissionError("Lock access denied.")

    monkeypatch.setattr(fcntl, "flock", deny_lock)
    with pytest.raises(PermissionError):
        service.list_runs(workspace)
    assert service.run_store.load(workspace, run.run_id) == run
