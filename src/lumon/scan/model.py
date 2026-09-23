"""Provider-neutral values for one Lumon Auto Scan run."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import cast

from lumon.tools.safety import sanitize_output


class ScanState(StrEnum):
    """Persisted outcome of one Auto Scan."""

    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_FINDINGS = "completed_with_findings"
    COMPLETED_WITH_FAILURES = "completed_with_failures"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ScanFinding:
    """One evidence-backed finding from the review-only Agent flow."""

    title: str
    severity: str
    repository: str
    impact: str
    trigger: str
    file: str
    line_range: str
    code_snippet: str
    suggestion: str
    root_cause: str = ""
    validation: str = "Skipped: lightweight review-only mode"
    issue_id: str = "untracked"
    issue_status: str = "open"
    pr_url: str | None = None

    @classmethod
    def from_payload(cls, payload: object, index: int) -> ScanFinding | None:
        """Convert untrusted Agent JSON into a bounded report value."""

        if not isinstance(payload, dict):
            return None
        values = cast(dict[str, object], payload)
        title = _text(values.get("title"), limit=500)
        if not title:
            return None
        severity = _text(values.get("severity"), default="Low", limit=20)
        if severity not in {"High", "Medium", "Low"}:
            severity = "Low"
        return cls(
            title=title,
            severity=severity,
            repository=_text(values.get("repository"), default="unknown", limit=300),
            impact=_text(values.get("impact"), limit=8_000),
            trigger=_text(values.get("trigger"), limit=8_000),
            file=_text(values.get("file"), limit=1_000),
            line_range=_text(values.get("line_range"), limit=200),
            code_snippet=_text(values.get("code_snippet"), limit=12_000),
            suggestion=_text(values.get("suggestion"), limit=8_000),
            root_cause=_text(values.get("root_cause"), limit=8_000),
            validation=_text(
                values.get("validation"),
                default="Skipped: lightweight review-only mode",
                limit=2_000,
            ),
            issue_id=_issue_id(values, index),
            issue_status=_text(values.get("issue_status"), default="open", limit=40),
            pr_url=_optional_url(values.get("pr_url")),
        )

    def as_payload(self) -> dict[str, str | None]:
        """Return the safe JSON shape consumed by the report renderer."""

        return {
            "title": self.title,
            "severity": self.severity,
            "repository": self.repository,
            "impact": self.impact,
            "trigger": self.trigger,
            "file": self.file,
            "line_range": self.line_range,
            "code_snippet": self.code_snippet,
            "suggestion": self.suggestion,
            "root_cause": self.root_cause,
            "validation": self.validation,
            "issue_id": self.issue_id,
            "issue_status": self.issue_status,
            "pr_url": self.pr_url,
        }


@dataclass(frozen=True, slots=True)
class ScanRun:
    """The state needed for history, report artifacts, and Dashboard display."""

    run_id: str
    state: ScanState
    phase: str
    started_at: datetime
    finished_at: datetime | None
    lookback_days: int
    repositories_scanned: int
    repositories_failed: int
    findings: tuple[ScanFinding, ...] = ()
    failures: tuple[str, ...] = ()
    hook_results: tuple[str, ...] = ()
    html_path: str | None = None
    pdf_path: str | None = None

    @classmethod
    def start(cls, run_id: str, lookback_days: int) -> ScanRun:
        """Create a new running receipt before Agent work begins."""

        return cls(
            run_id=run_id,
            state=ScanState.RUNNING,
            phase="review",
            started_at=datetime.now(UTC),
            finished_at=None,
            lookback_days=lookback_days,
            repositories_scanned=0,
            repositories_failed=0,
        )

    @property
    def duration_seconds(self) -> int | None:
        """Return whole elapsed seconds when the run has finished."""

        if self.finished_at is None:
            return None
        return max(0, int((self.finished_at - self.started_at).total_seconds()))

    @property
    def scan_window(self) -> str:
        """Use the legacy report wording for the configured review window."""

        return f"Last {self.lookback_days} Days"

    def as_payload(self) -> dict[str, object]:
        """Return the owner-only JSON receipt persisted under the Workspace."""

        return {
            "run_id": self.run_id,
            "state": self.state.value,
            "phase": self.phase,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "lookback_days": self.lookback_days,
            "repositories_scanned": self.repositories_scanned,
            "repositories_failed": self.repositories_failed,
            "findings": [finding.as_payload() for finding in self.findings],
            "failures": list(self.failures),
            "hook_results": list(self.hook_results),
            "html_path": self.html_path,
            "pdf_path": self.pdf_path,
        }

    @classmethod
    def from_payload(cls, payload: object) -> ScanRun:
        """Load one persisted receipt and reject malformed history entries."""

        if not isinstance(payload, dict):
            raise ValueError("scan receipt must be an object")
        values = cast(dict[str, object], payload)
        state = ScanState(str(values.get("state")))
        raw_findings = values.get("findings", [])
        finding_items = cast(list[object], raw_findings) if isinstance(raw_findings, list) else []
        findings = tuple(
            finding
            for index, item in enumerate(finding_items, start=1)
            if (finding := ScanFinding.from_payload(item, index)) is not None
        )
        raw_failures = values.get("failures", [])
        failure_items = cast(list[object], raw_failures) if isinstance(raw_failures, list) else []
        raw_hooks = values.get("hook_results", [])
        hook_items = cast(list[object], raw_hooks) if isinstance(raw_hooks, list) else []
        failures = tuple(_text(item, limit=2_000) for item in failure_items)
        hooks = tuple(_text(item, limit=2_000) for item in hook_items)
        return cls(
            run_id=_required_text(values.get("run_id")),
            state=state,
            phase=_required_text(values.get("phase")),
            started_at=_datetime(values.get("started_at")),
            finished_at=_optional_datetime(values.get("finished_at")),
            lookback_days=_integer(values.get("lookback_days"), minimum=1, maximum=365),
            repositories_scanned=_integer(values.get("repositories_scanned"), minimum=0),
            repositories_failed=_integer(values.get("repositories_failed"), minimum=0),
            findings=findings,
            failures=failures,
            hook_results=hooks,
            html_path=_optional_text(values.get("html_path")),
            pdf_path=_optional_text(values.get("pdf_path")),
        )


def _text(value: object, default: str = "", limit: int = 4_000) -> str:
    if value is None:
        return default
    return sanitize_output(str(value).strip())[:limit]


def _optional_text(value: object) -> str | None:
    text = _text(value)
    return text or None


def _optional_url(value: object) -> str | None:
    text = _optional_text(value)
    return text if text and text.startswith(("https://", "http://")) else None


def _issue_id(values: dict[str, object], index: int) -> str:
    """Keep legacy deterministic IDs when the Agent does not provide one."""

    supplied = _text(values.get("issue_id") or values.get("id"), limit=100)
    if supplied:
        return supplied
    title = re.sub(
        r"[^a-z0-9]+",
        "-",
        _text(values.get("title"), limit=500).lower(),
    ).strip("-")
    trigger_hash = hashlib.sha256(
        sanitize_output(_text(values.get("trigger"), limit=8_000)).encode("utf-8")
    ).hexdigest()[:12]
    identity = "|".join(
        (
            _text(values.get("repository"), default="unknown", limit=300),
            _text(values.get("file"), limit=1_000),
            title,
            _text(values.get("severity"), default="Low", limit=20),
            trigger_hash,
        )
    )
    if not identity.strip("|"):
        return f"finding-{index}"
    return f"ISSUE-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:10]}"


def _required_text(value: object) -> str:
    text = _text(value, limit=500)
    if not text:
        raise ValueError("scan receipt contains an empty text field")
    return text


def _integer(value: object, *, minimum: int, maximum: int | None = None) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError("scan receipt contains an invalid integer")
    if maximum is not None and value > maximum:
        raise ValueError("scan receipt contains an out-of-range integer")
    return value


def _datetime(value: object) -> datetime:
    parsed = _optional_datetime(value)
    if parsed is None:
        raise ValueError("scan receipt contains an invalid timestamp")
    return parsed


def _optional_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("scan receipt contains an invalid timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("scan receipt contains an invalid timestamp") from exc
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
