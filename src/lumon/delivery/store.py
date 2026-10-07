"""Small owner-only JSON receipts for Delivery runs and notifications."""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import cast
from uuid import UUID

from lumon.delivery.model import (
    DeliveryActivity,
    DeliveryEvent,
    DeliveryPoll,
    DeliveryPollState,
    DeliveryRun,
    DeliveryState,
)
from lumon.errors import PreflightError
from lumon.workspace.layout import WorkspaceLayout

_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class DeliveryRunStore:
    """Persist one run and its notification receipts under the Workspace."""

    def path_for(self, workspace: Path, run_id: str) -> Path:
        """Return a safe run directory path."""

        if _RUN_ID.fullmatch(run_id) is None:
            raise PreflightError("Delivery run ID contains unsafe characters.")
        directory = WorkspaceLayout.from_root(workspace).control_dir / "runs" / run_id
        # Receipts must not follow a symlink into another Workspace or user directory.
        if directory.resolve().parent != directory.parent.resolve() or directory.is_symlink():
            raise PreflightError("Delivery run directory is outside this Workspace.")
        if directory.parent.resolve() != workspace.resolve() / "lumon" / "runs":
            raise PreflightError("Delivery run directory is outside this Workspace.")
        return directory

    def save(self, workspace: Path, run: DeliveryRun) -> None:
        """Atomically write the non-sensitive run receipt."""

        directory = self.path_for(workspace, run.run_id)
        directory.mkdir(parents=True, exist_ok=True)
        _secure_directory(directory)
        payload = {
            "run_id": run.run_id,
            "story_key": run.story_key,
            "story_title": run.story_title,
            "state": run.state.value,
            "phase": run.phase,
            "started_at": run.started_at.isoformat(),
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "workspace_id": str(run.workspace_id) if run.workspace_id else None,
            "jira_url": run.jira_url,
            "repository": run.repository,
            "branch": run.branch,
            "pull_request_url": run.pull_request_url,
            "reason": run.reason,
            "verification_summary": run.verification_summary,
            "detail": run.detail,
            "poll_id": run.poll_id,
        }
        _atomic_write(directory / "run.json", payload)

    def load(self, workspace: Path, run_id: str) -> DeliveryRun:
        """Read one persisted run."""

        path = self.path_for(workspace, run_id) / "run.json"
        _reject_symlink(path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PreflightError(f"Unable to read Delivery run: {path}") from exc
        run = _run_from_payload(payload, path)
        if run.run_id != run_id:
            raise PreflightError("Delivery receipt ID does not match its directory.")
        return run

    def list(self, workspace: Path) -> tuple[DeliveryRun, ...]:
        """List valid Story receipts, ignoring other workflow folders."""

        runs: list[DeliveryRun] = []
        for run_id in self._run_ids(workspace):
            try:
                runs.append(self.load(workspace, run_id))
            except PreflightError:
                continue
        return tuple(sorted(runs, key=lambda run: run.started_at, reverse=True))

    def save_poll(self, workspace: Path, poll: DeliveryPoll) -> None:
        directory = self.path_for(workspace, poll.run_id)
        directory.mkdir(parents=True, exist_ok=True)
        _secure_directory(directory)
        payload = {
            "run_id": poll.run_id,
            "workspace_id": str(poll.workspace_id),
            "state": poll.state.value,
            "started_at": poll.started_at.isoformat(),
            "finished_at": poll.finished_at.isoformat() if poll.finished_at else None,
            "phase": poll.phase,
            "detail": poll.detail,
        }
        _atomic_write(directory / "poll.json", payload)

    def load_poll(self, workspace: Path, run_id: str) -> DeliveryPoll:
        path = self.path_for(workspace, run_id) / "poll.json"
        _reject_symlink(path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Expected a poll receipt.")
            values = cast(dict[str, object], payload)
            poll = DeliveryPoll(
                run_id=_required_string(values, "run_id", path),
                workspace_id=UUID(_required_string(values, "workspace_id", path)),
                state=DeliveryPollState(_required_string(values, "state", path)),
                started_at=_timestamp(_required_string(values, "started_at", path)),
                finished_at=_optional_datetime(values.get("finished_at"), path),
                phase=_required_string(values, "phase", path),
                detail=_optional_string(values.get("detail"), path) or "",
            )
            if poll.run_id != run_id:
                raise ValueError("Poll ID does not match its directory.")
            return poll
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise PreflightError(f"Unable to read Delivery poll: {path}") from exc

    def list_polls(self, workspace: Path) -> tuple[DeliveryPoll, ...]:
        polls: list[DeliveryPoll] = []
        for run_id in self._run_ids(workspace):
            try:
                polls.append(self.load_poll(workspace, run_id))
            except PreflightError:
                continue
        return tuple(sorted(polls, key=lambda poll: poll.started_at, reverse=True))

    def activity(self, workspace: Path, run_id: str) -> tuple[DeliveryActivity, ...]:
        path = self.path_for(workspace, run_id) / "activity.json"
        _reject_symlink(path)
        if not path.exists():
            return ()
        try:
            if path.stat().st_size > 1024 * 1024:
                raise ValueError("Activity receipt exceeds the size limit.")
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, list):
                raise ValueError("Invalid activity receipt.")
            entries = cast(list[object], payload)
            if len(entries) > 200:
                raise ValueError("Invalid activity receipt.")
            return tuple(_activity_from_payload(item, path) for item in entries)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise PreflightError(f"Unable to read Delivery activity: {path}") from exc

    def record_activity(self, workspace: Path, run_id: str, activity: DeliveryActivity) -> None:
        directory = self.path_for(workspace, run_id)
        directory.mkdir(parents=True, exist_ok=True)
        _secure_directory(directory)
        # ponytail: one writer per run, bounded to 200 summaries; stream only if traces grow.
        recent = (*self.activity(workspace, run_id), activity)[-200:]
        _atomic_write(
            directory / "activity.json",
            [
                {"at": item.at.isoformat(), "phase": item.phase, "detail": item.detail}
                for item in recent
            ],
        )

    def _run_ids(self, workspace: Path) -> tuple[str, ...]:
        directory = WorkspaceLayout.from_root(workspace).control_dir / "runs"
        if not directory.is_dir() or directory.is_symlink():
            return ()
        return tuple(
            path.name
            for path in directory.iterdir()
            if path.is_dir() and not path.is_symlink() and _RUN_ID.fullmatch(path.name)
        )

    def notification_sent(self, workspace: Path, run_id: str, event: DeliveryEvent) -> bool:
        """Return whether one lifecycle event was already sent."""

        payload = self._load_notifications(workspace, run_id)
        return event.value in payload

    def record_notification(
        self,
        workspace: Path,
        run_id: str,
        event: DeliveryEvent,
        detail: str,
        sent_at: datetime,
    ) -> None:
        """Record a safe successful notification receipt."""

        directory = self.path_for(workspace, run_id)
        directory.mkdir(parents=True, exist_ok=True)
        _secure_directory(directory)
        payload = self._load_notifications(workspace, run_id)
        payload[event.value] = {"sent_at": sent_at.isoformat(), "detail": detail}
        _atomic_write(directory / "notifications.json", payload)

    def _load_notifications(self, workspace: Path, run_id: str) -> dict[str, object]:
        path = self.path_for(workspace, run_id) / "notifications.json"
        _reject_symlink(path)
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PreflightError(f"Unable to read Delivery notifications: {path}") from exc
        if not isinstance(payload, dict):
            raise PreflightError(f"Invalid Delivery notifications receipt: {path}")
        return cast(dict[str, object], payload)


def _run_from_payload(payload: object, source: Path) -> DeliveryRun:
    if not isinstance(payload, dict):
        raise PreflightError(f"Invalid Delivery run receipt: {source}")
    values = cast(dict[str, object], payload)
    try:
        workspace_id = values.get("workspace_id")
        return DeliveryRun(
            run_id=_required_string(values, "run_id", source),
            story_key=_required_string(values, "story_key", source),
            story_title=_required_string(values, "story_title", source),
            state=DeliveryState(_required_string(values, "state", source)),
            phase=_required_string(values, "phase", source),
            started_at=_timestamp(_required_string(values, "started_at", source)),
            finished_at=_optional_datetime(values.get("finished_at"), source),
            workspace_id=(None if workspace_id is None else UUID(str(workspace_id))),
            jira_url=_optional_string(values.get("jira_url"), source),
            repository=_optional_string(values.get("repository"), source),
            branch=_optional_string(values.get("branch"), source),
            pull_request_url=_optional_string(values.get("pull_request_url"), source),
            reason=_optional_string(values.get("reason"), source),
            verification_summary=_optional_string(values.get("verification_summary"), source),
            detail=_optional_string(values.get("detail"), source),
            poll_id=_optional_string(values.get("poll_id"), source),
        )
    except (TypeError, ValueError) as exc:
        raise PreflightError(f"Invalid Delivery run receipt: {source}") from exc


def _required_string(payload: dict[str, object], key: str, source: Path) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PreflightError(f"Invalid Delivery run field '{key}': {source}")
    return value


def _optional_string(value: object, source: Path) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise PreflightError(f"Invalid Delivery run text field: {source}")
    return value


def _optional_datetime(value: object, source: Path) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise PreflightError(f"Invalid Delivery run timestamp: {source}")
    try:
        return _timestamp(value)
    except ValueError as exc:
        raise PreflightError(f"Invalid Delivery run timestamp: {source}") from exc


def _activity_from_payload(payload: object, source: Path) -> DeliveryActivity:
    if not isinstance(payload, dict):
        raise PreflightError(f"Invalid Delivery activity: {source}")
    values = cast(dict[str, object], payload)
    return DeliveryActivity(
        at=_timestamp(_required_string(values, "at", source)),
        phase=_required_string(values, "phase", source),
        detail=_required_string(values, "detail", source),
    )


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Delivery timestamps must include a timezone.")
    return parsed


def _reject_symlink(path: Path) -> None:
    if path.is_symlink():
        raise PreflightError("Delivery receipt must not be a symbolic link.")


def _atomic_write(path: Path, payload: Mapping[str, object] | list[dict[str, str]]) -> None:
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary = Path(temporary_name)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
        path.chmod(0o600)
    except OSError as exc:
        raise PreflightError(f"Unable to write Delivery receipt: {path}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _secure_directory(path: Path) -> None:
    try:
        path.chmod(0o700)
    except OSError as exc:
        raise PreflightError(f"Unable to secure Delivery receipt directory: {path}") from exc
