"""Install the user-level scheduler for Workspace Auto Delivery polls."""

from __future__ import annotations

import os
import plistlib
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol
from uuid import UUID

from lumon.errors import PreflightError
from lumon.workspace.registry import UserStateLayout
from lumon.workspace.settings import AutoDeliverySettings, validate_schedule_expression


class DeliveryScheduler(Protocol):
    """OS scheduling boundary used by Dashboard settings."""

    def apply(
        self,
        workspace: Path,
        workspace_id: UUID,
        settings: AutoDeliverySettings,
    ) -> None:
        """Install, update, or remove one Workspace schedule."""


class LaunchdDeliveryScheduler:
    """Manage one owner-level macOS LaunchAgent per Workspace."""

    def __init__(self, state_root: Path | None = None) -> None:
        self.state_root = UserStateLayout.from_root(state_root).root

    def apply(
        self,
        workspace: Path,
        workspace_id: UUID,
        settings: AutoDeliverySettings,
    ) -> None:
        """Write and load the current schedule, or remove it when disabled."""

        if not settings.enabled:
            self.remove(workspace_id)
            return
        if sys.platform != "darwin":
            raise PreflightError("Auto Delivery scheduling currently requires macOS.")

        expression = validate_schedule_expression(settings.schedule_expression)
        timing = launchd_timing(expression)
        plist_path = self.plist_path(workspace_id)
        try:
            plist_path.parent.mkdir(parents=True, exist_ok=True)
            plist_path.parent.chmod(0o700)
            _atomic_write(
                plist_path, _plist_bytes(workspace, workspace_id, timing, self.state_root)
            )
        except OSError as exc:
            raise PreflightError(f"Unable to prepare Auto Delivery schedule: {plist_path}") from exc

        domain = f"gui/{os.getuid()}"
        _launchctl("bootout", domain, plist_path, ignore_failure=True)
        _launchctl("bootstrap", domain, plist_path)

    def remove(self, workspace_id: UUID) -> None:
        """Unload and remove one Workspace's LaunchAgent."""

        plist_path = self.plist_path(workspace_id)
        if sys.platform == "darwin" and plist_path.exists():
            _launchctl("bootout", f"gui/{os.getuid()}", plist_path, ignore_failure=True)
        try:
            plist_path.unlink(missing_ok=True)
        except OSError as exc:
            raise PreflightError(f"Unable to remove Auto Delivery schedule: {plist_path}") from exc

    def plist_path(self, workspace_id: UUID) -> Path:
        """Return the stable LaunchAgent path for one Workspace."""

        return Path.home() / "Library" / "LaunchAgents" / f"com.lumon.delivery.{workspace_id}.plist"


def launchd_timing(
    expression: str,
    *,
    label: str = "Auto Delivery",
) -> dict[str, object]:
    """Translate the supported cron subset into Launchd calendar settings."""

    fields = validate_schedule_expression(expression, label=label).split()
    minute, hour, day_of_week = fields[0], fields[1], fields[4]
    if fields[2:4] != ["*", "*"]:
        raise PreflightError(
            f"{label} schedule supports minute/hour schedules only; use * for day and month."
        )
    if minute.startswith("*/") and hour == "*" and day_of_week == "*":
        return {"StartInterval": int(minute[2:]) * 60}
    if not minute.isdigit() or not hour.isdigit():
        raise PreflightError(
            f"{label} schedule must use a numeric minute and hour or */N intervals."
        )
    minute_value = int(minute)
    hour_value = int(hour)
    if not 0 <= minute_value <= 59 or not 0 <= hour_value <= 23:
        raise PreflightError(f"{label} schedule contains an invalid minute or hour.")
    weekdays = _weekday_values(day_of_week, label)
    entries = [
        {
            "Minute": minute_value,
            "Hour": hour_value,
            **({"Weekday": day} if day is not None else {}),
        }
        for day in weekdays
    ]
    return {"StartCalendarInterval": entries[0] if len(entries) == 1 else entries}


def _weekday_values(value: str, label: str) -> list[int | None]:
    if value == "*":
        return [None]
    values: list[int | None] = []
    try:
        for item in value.split(","):
            if item.startswith("*/"):
                raise ValueError
            if "-" in item:
                start, end = (int(part) for part in item.split("-", 1))
                if start > end:
                    raise ValueError
                values.extend(range(start, end + 1))
            else:
                values.append(int(item))
    except ValueError as exc:
        raise PreflightError(f"{label} schedule contains an invalid weekday.") from exc
    if any(item is None or not 0 <= item <= 7 for item in values):
        raise PreflightError(f"{label} schedule contains an invalid weekday.")
    return values


def _plist_bytes(
    workspace: Path,
    workspace_id: UUID,
    timing: Mapping[str, object],
    state_root: Path,
) -> bytes:
    log_dir = state_root / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_dir.chmod(0o700)
    except OSError as exc:
        raise PreflightError(f"Unable to prepare Auto Delivery logs: {log_dir}") from exc
    environment = {
        "HOME": str(Path.home()),
        "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
        "LUMON_HOME": str(state_root),
    }
    payload: dict[str, object] = {
        "Label": f"com.lumon.delivery.{workspace_id}",
        "ProgramArguments": [
            sys.executable,
            "-m",
            "lumon",
            "delivery",
            "poll",
            "--workspace",
            str(workspace),
            "--workspace-id",
            str(workspace_id),
            "--json",
        ],
        "WorkingDirectory": str(workspace),
        "EnvironmentVariables": environment,
        "StandardOutPath": str(log_dir / f"delivery-{workspace_id}.log"),
        "StandardErrorPath": str(log_dir / f"delivery-{workspace_id}.error.log"),
        "RunAtLoad": False,
        **timing,
    }
    return plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=True)


def _launchctl(*arguments: object, ignore_failure: bool = False) -> None:
    try:
        result = subprocess.run(
            ["launchctl", *(str(argument) for argument in arguments)],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PreflightError(
            "Unable to communicate with the macOS Auto Delivery scheduler."
        ) from exc
    if result.returncode and not ignore_failure:
        detail = result.stderr.strip().replace("\n", " ")[:200]
        raise PreflightError(
            f"Unable to install Auto Delivery schedule: {detail or 'launchctl failed'}"
        )


def _atomic_write(path: Path, content: bytes) -> None:
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary = Path(temporary_name)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
        path.chmod(0o600)
    except OSError as exc:
        raise PreflightError(f"Unable to write Auto Delivery schedule: {path}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
