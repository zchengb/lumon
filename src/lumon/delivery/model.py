"""Small, provider-neutral Auto Delivery value objects."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from urllib.parse import urlsplit
from uuid import UUID

from lumon.tools.safety import sanitize_output


class DeliveryEvent(StrEnum):
    """Lifecycle events that can be sent to the configured Webhook."""

    STARTED = "delivery.started"
    DEV_DONE = "delivery.dev_done"
    FAILED = "delivery.failed"
    BLOCKED = "delivery.blocked"


class DeliveryState(StrEnum):
    """Persisted outcome of one Delivery run."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class DeliveryPollState(StrEnum):
    """A scheduled check can finish without claiming a Story."""

    RUNNING = "running"
    IDLE = "idle"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class DeliveryActivity:
    """One safe progress summary, never a command or its raw output."""

    at: datetime
    phase: str
    detail: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "phase", sanitize_output(self.phase.strip())[:80])
        object.__setattr__(self, "detail", sanitize_output(self.detail.strip())[:500])


@dataclass(frozen=True, slots=True)
class DeliveryPoll:
    """The durable outcome of one scheduled Agent check."""

    run_id: str
    workspace_id: UUID
    state: DeliveryPollState
    started_at: datetime
    phase: str = "discover"
    finished_at: datetime | None = None
    detail: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "detail", sanitize_output(self.detail.strip())[:500])

    @property
    def duration_seconds(self) -> int | None:
        if self.finished_at is None:
            return None
        return max(0, int((self.finished_at - self.started_at).total_seconds()))


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    """Result details produced by one Delivery phase."""

    state: DeliveryState
    phase: str
    detail: str
    published_url: str | None = None
    verification_summary: str | None = None


@dataclass(frozen=True, slots=True)
class DeliveryRun:
    """The state needed to render and persist a Delivery lifecycle."""

    run_id: str
    story_key: str
    story_title: str
    state: DeliveryState
    phase: str
    started_at: datetime
    finished_at: datetime | None = None
    workspace_id: UUID | None = None
    jira_url: str | None = None
    repository: str | None = None
    branch: str | None = None
    pull_request_url: str | None = None
    reason: str | None = None
    verification_summary: str | None = None
    detail: str | None = None
    poll_id: str | None = None

    def __post_init__(self) -> None:
        """Keep external text safe before it reaches Cards or receipts."""

        for field_name in (
            "story_key",
            "story_title",
            "phase",
            "jira_url",
            "repository",
            "branch",
            "pull_request_url",
            "reason",
            "verification_summary",
            "detail",
        ):
            value = getattr(self, field_name)
            if isinstance(value, str):
                object.__setattr__(self, field_name, sanitize_output(value.strip()))
        for field_name in ("jira_url", "pull_request_url"):
            value = getattr(self, field_name)
            if isinstance(value, str):
                try:
                    parsed = urlsplit(value)
                except ValueError:
                    object.__setattr__(self, field_name, None)
                    continue
                if (
                    parsed.scheme not in {"http", "https"}
                    or not parsed.hostname
                    or parsed.username
                    or parsed.password
                ):
                    object.__setattr__(self, field_name, None)

    @classmethod
    def claim(
        cls,
        run_id: str,
        story_key: str,
        story_title: str,
        *,
        now: datetime | None = None,
        workspace_id: UUID | None = None,
        jira_url: str | None = None,
        poll_id: str | None = None,
    ) -> DeliveryRun:
        """Create a claimed run before any Agent work begins."""

        timestamp = now or datetime.now(UTC)
        return cls(
            run_id=run_id,
            story_key=story_key,
            story_title=story_title,
            state=DeliveryState.RUNNING,
            phase="claim",
            started_at=timestamp,
            workspace_id=workspace_id,
            jira_url=jira_url,
            poll_id=poll_id,
        )

    def with_result(
        self,
        result: DeliveryResult,
        *,
        now: datetime | None = None,
        repository: str | None = None,
        branch: str | None = None,
        pull_request_url: str | None = None,
    ) -> DeliveryRun:
        """Return the next immutable run state after one lifecycle phase."""

        finished_at = now or datetime.now(UTC)
        terminal = result.state in {
            DeliveryState.COMPLETED,
            DeliveryState.FAILED,
            DeliveryState.BLOCKED,
        }
        return replace(
            self,
            state=result.state,
            phase=result.phase,
            finished_at=finished_at if terminal else None,
            repository=repository if repository is not None else self.repository,
            branch=branch if branch is not None else self.branch,
            pull_request_url=(
                pull_request_url if pull_request_url is not None else self.pull_request_url
            ),
            reason=(
                result.detail
                if result.state in {DeliveryState.FAILED, DeliveryState.BLOCKED}
                else None
            ),
            verification_summary=result.verification_summary,
            detail=result.detail,
        )

    @property
    def duration_seconds(self) -> int | None:
        """Return whole elapsed seconds when the run has finished."""

        if self.finished_at is None:
            return None
        return max(0, int((self.finished_at - self.started_at).total_seconds()))
