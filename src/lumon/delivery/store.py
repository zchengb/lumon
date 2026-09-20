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

from lumon.delivery.model import DeliveryEvent, DeliveryRun, DeliveryState
from lumon.errors import PreflightError
from lumon.workspace.layout import WorkspaceLayout

_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class DeliveryRunStore:
    """Persist one run and its notification receipts under the Workspace."""

    def path_for(self, workspace: Path, run_id: str) -> Path:
        """Return a safe run directory path."""

        if _RUN_ID.fullmatch(run_id) is None:
            raise PreflightError("Delivery run ID contains unsafe characters.")
        return WorkspaceLayout.from_root(workspace).control_dir / "runs" / run_id

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
        }
        _atomic_write(directory / "run.json", payload)

    def load(self, workspace: Path, run_id: str) -> DeliveryRun:
        """Read one persisted run."""

        path = self.path_for(workspace, run_id) / "run.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PreflightError(f"Unable to read Delivery run: {path}") from exc
        return _run_from_payload(payload, path)

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
            started_at=datetime.fromisoformat(_required_string(values, "started_at", source)),
            finished_at=_optional_datetime(values.get("finished_at"), source),
            workspace_id=(None if workspace_id is None else UUID(str(workspace_id))),
            jira_url=_optional_string(values.get("jira_url"), source),
            repository=_optional_string(values.get("repository"), source),
            branch=_optional_string(values.get("branch"), source),
            pull_request_url=_optional_string(values.get("pull_request_url"), source),
            reason=_optional_string(values.get("reason"), source),
            verification_summary=_optional_string(values.get("verification_summary"), source),
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
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise PreflightError(f"Invalid Delivery run timestamp: {source}") from exc


def _atomic_write(path: Path, payload: Mapping[str, object]) -> None:
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
