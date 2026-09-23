"""Install the user-level macOS schedule for Auto Scan polls."""

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

from lumon.delivery.scheduler import launchd_timing
from lumon.errors import PreflightError
from lumon.workspace.registry import UserStateLayout
from lumon.workspace.settings import AutoScanSettings, validate_schedule_expression


class ScanScheduler(Protocol):
    """OS scheduling boundary used by Dashboard Auto Scan settings."""

    def apply(self, workspace: Path, workspace_id: UUID, settings: AutoScanSettings) -> None:
        """Install, update, or remove one Workspace schedule."""


class LaunchdScanScheduler:
    """Manage one owner-level macOS LaunchAgent per Workspace."""

    def __init__(self, state_root: Path | None = None) -> None:
        self.state_root = UserStateLayout.from_root(state_root).root

    def apply(self, workspace: Path, workspace_id: UUID, settings: AutoScanSettings) -> None:
        """Write and load the current schedule, or remove it when disabled."""

        if not settings.enabled:
            self.remove(workspace_id)
            return
        if sys.platform != "darwin":
            raise PreflightError("Auto Scan scheduling currently requires macOS.")
        expression = validate_schedule_expression(
            settings.schedule_expression,
            label="Auto Scan",
        )
        timing = launchd_timing(expression)
        path = self.plist_path(workspace_id)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.parent.chmod(0o700)
            _atomic_write(path, _plist_bytes(workspace, workspace_id, timing, self.state_root))
        except OSError as exc:
            raise PreflightError(f"Unable to prepare Auto Scan schedule: {path}") from exc
        domain = f"gui/{os.getuid()}"
        _launchctl("bootout", domain, path, ignore_failure=True)
        _launchctl("bootstrap", domain, path)

    def remove(self, workspace_id: UUID) -> None:
        """Unload and remove one Workspace's LaunchAgent."""

        path = self.plist_path(workspace_id)
        if sys.platform == "darwin" and path.exists():
            _launchctl("bootout", f"gui/{os.getuid()}", path, ignore_failure=True)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise PreflightError(f"Unable to remove Auto Scan schedule: {path}") from exc

    def plist_path(self, workspace_id: UUID) -> Path:
        """Return the stable LaunchAgent path for one Workspace."""

        return Path.home() / "Library" / "LaunchAgents" / f"com.lumon.scan.{workspace_id}.plist"


def _plist_bytes(
    workspace: Path,
    workspace_id: UUID,
    timing: Mapping[str, object],
    state_root: Path,
) -> bytes:
    log_dir = state_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_dir.chmod(0o700)
    payload: dict[str, object] = {
        "Label": f"com.lumon.scan.{workspace_id}",
        "ProgramArguments": [
            sys.executable,
            "-m",
            "lumon",
            "scan",
            "poll",
            "--workspace",
            str(workspace),
            "--workspace-id",
            str(workspace_id),
            "--json",
        ],
        "WorkingDirectory": str(workspace),
        "EnvironmentVariables": {
            "HOME": str(Path.home()),
            "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
            "LUMON_HOME": str(state_root),
        },
        "StandardOutPath": str(log_dir / f"scan-{workspace_id}.log"),
        "StandardErrorPath": str(log_dir / f"scan-{workspace_id}.error.log"),
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
        raise PreflightError("Unable to communicate with the macOS Auto Scan scheduler.") from exc
    if result.returncode and not ignore_failure:
        detail = result.stderr.strip().replace("\n", " ")[:200]
        message = detail or "launchctl failed"
        raise PreflightError(f"Unable to install Auto Scan schedule: {message}")


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
        raise PreflightError(f"Unable to write Auto Scan schedule: {path}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
