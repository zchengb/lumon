"""Run the review-only Auto Scan flow and its configured completion hooks."""

from __future__ import annotations

import asyncio
import fcntl
import json
import os
import re
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

from lumon.agents.agent.config import AgentConfigStore
from lumon.agents.agent.model import WorkspaceContext
from lumon.agents.agent.runner import AgentRunner, create_agent_runner
from lumon.agents.agent.workspace_context import WorkspaceContextBuilder
from lumon.errors import AgentRuntimeError, LumonError, PreflightError
from lumon.scan.model import ScanFinding, ScanRun, ScanState
from lumon.scan.report import write_report
from lumon.scan.store import ScanRunStore
from lumon.tools.safety import sanitize_output
from lumon.workspace.registry import UserStateLayout, WorkspaceRegistry
from lumon.workspace.settings import WorkspaceSettings, WorkspaceSettingsStore


class ScanService:
    """Coordinate one scan without coupling review logic to Jira or PDF code."""

    def __init__(
        self,
        state_root: Path | None = None,
        registry: WorkspaceRegistry | None = None,
        settings_store: WorkspaceSettingsStore | None = None,
        agent_config_store: AgentConfigStore | None = None,
        runner: AgentRunner | None = None,
        run_store: ScanRunStore | None = None,
    ) -> None:
        self.registry = registry or WorkspaceRegistry(state_root)
        self.settings_store = settings_store or WorkspaceSettingsStore(state_root)
        state_layout = UserStateLayout.from_root(state_root or self.registry.layout.root)
        self.agent_config_store = agent_config_store or AgentConfigStore(state_layout.root)
        self.runner = runner
        self.run_store = run_store or ScanRunStore()
        self.state_root = state_layout.root

    def list_runs(self, workspace: Path) -> tuple[ScanRun, ...]:
        """Return history for a registered Workspace."""

        return self.run_store.list(workspace)

    def artifact_path(self, workspace: Path, run_id: str, kind: str) -> Path:
        """Resolve one report artifact for Dashboard download."""

        return self.run_store.artifact_path(workspace, run_id, kind)

    def run(
        self,
        workspace_id: UUID,
        *,
        force: bool = False,
        run_id: str | None = None,
    ) -> ScanRun:
        """Run one scan, optionally bypassing the scheduled-enabled gate."""

        registration = self.registry.find(workspace_id)
        if registration is None:
            raise PreflightError(f"Workspace is not registered: {workspace_id}")
        settings = self.settings_store.load(workspace_id)
        if not force and not settings.auto_scan.enabled:
            raise PreflightError("Auto Scan is disabled for this Workspace.")

        workspace = registration.path
        run = ScanRun.start(run_id or uuid4().hex, settings.auto_scan.lookback_days)
        self.run_store.save(workspace, run)
        with _scan_lock(self.state_root, workspace_id):
            try:
                return self._run_locked(workspace, workspace_id, settings, run)
            except LumonError:
                self._save_failed(workspace, run, "Lumon could not complete the scan.")
                raise
            except Exception as exc:
                detail = sanitize_output(str(exc))[:500] or "Unexpected Auto Scan failure."
                self._save_failed(workspace, run, detail)
                raise AgentRuntimeError(detail) from exc

    def _run_locked(
        self,
        workspace: Path,
        workspace_id: UUID,
        settings: WorkspaceSettings,
        run: ScanRun,
    ) -> ScanRun:
        """Execute the Agent review, report, and optional post-scan hooks."""

        config = self.agent_config_store.load()
        if not config.enabled:
            raise PreflightError("The Lumon Agent is disabled.")
        context_builder = WorkspaceContextBuilder(
            replace(config, default_workspace_id=workspace_id),
            self.registry,
        )
        context = context_builder.resolve_workspace()
        prompt = context_builder.build_prompt(
            context,
            (),
            _scan_prompt(
                run=run,
                workflow_description=settings.auto_scan.workflow_description,
                result_path=self.run_store.path_for(workspace, run.run_id) / "scan-result.json",
            ),
        )
        runner = self.runner or create_agent_runner(config)
        result = asyncio.run(runner.run(workspace, prompt))
        if result.status != "succeeded":
            detail = sanitize_output(
                result.failure_diagnostic or "The Auto Scan Agent did not complete."
            )[:500]
            failed = replace(
                run,
                state=ScanState.FAILED,
                phase="review",
                finished_at=_now(),
                failures=(detail,),
            )
            self.run_store.save(workspace, failed)
            return failed

        payload = _load_agent_result(
            self.run_store.path_for(workspace, run.run_id) / "scan-result.json",
            result.final_text,
        )
        reviewed = _reviewed_run(run, payload, len(context.repositories))
        report = write_report(reviewed, self.run_store.path_for(workspace, run.run_id))
        failures = list(reviewed.failures)
        if report.error:
            failures.append(f"PDF report: {report.error}")
        completed = replace(
            reviewed,
            html_path=report.html_path,
            pdf_path=report.pdf_path,
            failures=tuple(failures),
            state=(ScanState.COMPLETED_WITH_FAILURES if failures else reviewed.state),
            finished_at=_now(),
        )
        hook_results: list[str] = []
        if (
            completed.findings
            and completed.state != ScanState.FAILED
            and settings.auto_scan.trigger_hooks
        ):
            hook_result = self._run_completion_hooks(
                runner,
                workspace,
                context_builder,
                context,
                completed,
                settings.auto_scan.trigger_hooks,
            )
            hook_results.append(hook_result)
            if hook_result.startswith("failed:"):
                failures.append(hook_result)
        final_state = ScanState.COMPLETED_WITH_FAILURES if failures else completed.state
        final = replace(
            completed,
            state=final_state,
            failures=tuple(failures),
            hook_results=tuple(hook_results),
            finished_at=_now(),
        )
        self.run_store.save(workspace, final)
        return final

    def _run_completion_hooks(
        self,
        runner: AgentRunner,
        workspace: Path,
        context_builder: WorkspaceContextBuilder,
        context: WorkspaceContext,
        run: ScanRun,
        hooks: tuple[str, ...],
    ) -> str:
        """Ask the Agent to execute configured, capability-backed hooks."""

        prompt = context_builder.build_prompt(
            context,
            (),
            _hook_prompt(run, hooks),
        )
        result = asyncio.run(runner.run(workspace, prompt))
        if result.status != "succeeded":
            detail = sanitize_output(
                result.failure_diagnostic or "completion hook Agent turn failed"
            )[:400]
            return f"failed: {detail}"
        summary = sanitize_output((result.final_text or "hooks completed").strip())[:500]
        return f"completed: {summary}"

    def _save_failed(self, workspace: Path, run: ScanRun, detail: str) -> None:
        failed = replace(
            run,
            state=ScanState.FAILED,
            phase="preflight",
            finished_at=_now(),
            failures=(sanitize_output(detail)[:500],),
        )
        self.run_store.save(workspace, failed)


def _scan_prompt(run: ScanRun, workflow_description: str, result_path: Path) -> str:
    return f"""You are running one Lumon Auto Scan review.

Workflow description:
{workflow_description}

Review the configured repositories for changes in the last {run.lookback_days} days.
The core flow is review-only: inspect git history, diffs, and related code, then
report only confirmed bugs with concrete evidence. Do not require Jira, do not
create issues, do not modify repositories, do not run builds or tests, and do not
generate a PDF. Completion hooks run separately after this review.

Write the only source of truth to:
{result_path}

Use this JSON contract:
{{
  "scan_status": "completed | completed_with_findings | completed_with_failures | failed",
  "repositories_scanned": 0,
  "repositories_failed": 0,
  "findings": [
    {{
      "title": "short confirmed issue",
      "severity": "High | Medium | Low",
      "repository": "repository name",
      "impact": "production impact",
      "trigger": "realistic trigger",
      "file": "path/to/file",
      "line_range": "10-15",
      "code_snippet": "redacted evidence",
      "suggestion": "specific remediation",
      "root_cause": "why it happens",
      "validation": "Skipped: lightweight review-only mode",
      "pr_url": null
    }}
  ],
  "failures": []
}}

Only include findings with evidence, impact, and a realistic trigger. Never put
credentials, tokens, webhook URLs, or raw private data in the JSON. Finish with
a short summary after the file has been written.
"""


def _hook_prompt(run: ScanRun, hooks: tuple[str, ...]) -> str:
    hook_list = "\n".join(f"- {hook}" for hook in hooks)
    findings = json.dumps(
        [finding.as_payload() for finding in run.findings],
        ensure_ascii=False,
    )
    return f"""The Lumon Auto Scan review has completed.

Configured completion hooks:
{hook_list}

Findings:
{findings}

Execute only the configured hooks that are supported by the current Workspace
capabilities. For example, a Workspace may configure a TWG CLI hook to create
bug cards; another Workspace may have no Jira connection and should use a
different hook or remain report-only. Do not assume Jira, do not invent a hook,
and do not alter the reviewed code. Do not claim a hook succeeded without a
successful tool result. Return a short, redacted completion summary.
"""


def _reviewed_run(run: ScanRun, payload: dict[str, object], repository_fallback: int) -> ScanRun:
    raw_findings = payload.get("findings", [])
    findings_items = cast(list[object], raw_findings) if isinstance(raw_findings, list) else []
    findings = tuple(
        finding
        for index, item in enumerate(findings_items, start=1)
        if (finding := ScanFinding.from_payload(item, index)) is not None
    )
    raw_failures = payload.get("failures", [])
    failure_items = cast(list[object], raw_failures) if isinstance(raw_failures, list) else []
    failures = tuple(
        sanitize_output(str(item))[:2_000] for item in failure_items if str(item).strip()
    )
    scanned = _non_negative_int(payload.get("repositories_scanned"), repository_fallback)
    failed = _non_negative_int(payload.get("repositories_failed"), len(failures))
    requested_state = str(payload.get("scan_status") or "")
    state = _state_from_payload(requested_state, findings, failures)
    return replace(
        run,
        state=state,
        phase="review",
        finished_at=_now(),
        repositories_scanned=scanned,
        repositories_failed=failed,
        findings=findings,
        failures=failures,
    )


def _state_from_payload(
    value: str,
    findings: tuple[ScanFinding, ...],
    failures: tuple[str, ...],
) -> ScanState:
    try:
        state = ScanState(value)
    except ValueError:
        state = ScanState.COMPLETED_WITH_FINDINGS if findings else ScanState.COMPLETED
    if state == ScanState.COMPLETED and findings:
        return ScanState.COMPLETED_WITH_FINDINGS
    if failures and state in {ScanState.COMPLETED, ScanState.COMPLETED_WITH_FINDINGS}:
        return ScanState.COMPLETED_WITH_FAILURES
    return state


def _load_agent_result(path: Path, final_text: str | None) -> dict[str, object]:
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AgentRuntimeError(f"Auto Scan result JSON is invalid: {path}") from exc
        if isinstance(payload, dict):
            return cast(dict[str, object], payload)
    if final_text:
        candidate = final_text.strip()
        if candidate.startswith("```"):
            candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", candidate, flags=re.S)
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise AgentRuntimeError(f"Auto Scan did not write its result: {path}") from exc
        if isinstance(payload, dict):
            return cast(dict[str, object], payload)
    raise AgentRuntimeError(f"Auto Scan did not write its result: {path}")


def _non_negative_int(value: object, fallback: int) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return fallback


def _now() -> datetime:
    return datetime.now(UTC)


@contextmanager
def _scan_lock(state_root: Path, workspace_id: UUID) -> Generator[None, None, None]:
    lock_directory = state_root / "locks"
    lock_directory.mkdir(parents=True, exist_ok=True)
    lock_directory.chmod(0o700)
    lock_path = lock_directory / f"scan-{workspace_id}.lock"
    stream = lock_path.open("a+")
    try:
        os.fchmod(stream.fileno(), 0o600)
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise PreflightError("Another Auto Scan is already running.") from exc
        yield
    finally:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        finally:
            stream.close()
