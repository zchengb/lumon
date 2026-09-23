"""Contract tests for Auto Scan persistence, reports, and hooks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from lumon.agents.agent.config import AgentConfig, AgentConfigStore
from lumon.agents.agent.model import AgentResult
from lumon.agents.agent.runner import AgentEventCallback, AgentRunner, ProgressCallback
from lumon.scan.model import ScanFinding, ScanRun, ScanState
from lumon.scan.report import ReportResult, write_report
from lumon.scan.service import ScanService
from lumon.scan.store import ScanRunStore
from lumon.skills.installer import SkillInstaller
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.model import InitRequest
from lumon.workspace.registry import WorkspaceRegistry
from lumon.workspace.settings import AutoScanSettings, WorkspaceSettings, WorkspaceSettingsStore


class _FakeRunner:
    provider = "fake"
    display_name = "Fake Agent"
    executable = "fake-agent"

    def __init__(self) -> None:
        self.prompts: list[str] = []

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
    ) -> AgentResult:
        del agent_session_id, images, on_progress, on_event
        self.prompts.append(prompt)
        if "Configured completion hooks:" in prompt:
            return AgentResult(status="succeeded", final_text="TWG hook completed")

        run_json = next(workspace.rglob("run.json"))
        (run_json.parent / "scan-result.json").write_text(
            json.dumps(
                {
                    "scan_status": "completed_with_findings",
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
                    ],
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


def test_scan_service_keeps_review_provider_neutral_and_runs_completion_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
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
            auto_scan=AutoScanSettings(
                enabled=True,
                trigger_hooks=("twg.create_bug",),
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

    monkeypatch.setattr("lumon.scan.report._convert_via_chrome", fake_pdf)
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
    assert result.hook_results == ("completed: TWG hook completed",)
    assert len(runner.prompts) == 2
    assert "scan-result.json" in runner.prompts[0]
    assert "twg.create_bug" in runner.prompts[1]
