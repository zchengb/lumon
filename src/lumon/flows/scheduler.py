"""Install one user-level macOS schedule for a specific Workspace flow."""

from __future__ import annotations

import os
import plistlib
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Protocol
from uuid import UUID

from lumon.delivery.scheduler import launchd_timing
from lumon.errors import PreflightError
from lumon.flows.catalog import FlowCatalog
from lumon.workspace.registry import UserStateLayout
from lumon.workspace.settings import FlowScheduleSettings, validate_schedule_expression


class FlowScheduler(Protocol):
    """Operating-system scheduling boundary for one Flow."""

    def apply(
        self,
        workspace: Path,
        workspace_id: UUID,
        schedule: FlowScheduleSettings,
    ) -> None:
        """Install, update, or remove one Flow schedule."""


class LaunchdFlowScheduler:
    """Manage one owner-level LaunchAgent per scheduled Workspace Flow."""

    def __init__(
        self,
        state_root: Path | None = None,
        launch_agents_dir: Path | None = None,
    ) -> None:
        self.state_root = UserStateLayout.from_root(state_root).root
        self.launch_agents_dir = launch_agents_dir or (Path.home() / "Library" / "LaunchAgents")

    def apply(
        self,
        workspace: Path,
        workspace_id: UUID,
        schedule: FlowScheduleSettings,
    ) -> None:
        """Install the Flow's schedule only when both it and its Flow are enabled."""

        if not schedule.enabled:
            self.remove(workspace_id, schedule.flow_id)
            return

        definition = FlowCatalog(workspace).read(schedule.flow_id)
        if not definition.enabled:
            self.remove(workspace_id, schedule.flow_id)
            return
        if sys.platform != "darwin":
            raise PreflightError("Flow scheduling currently requires macOS.")

        expression = validate_schedule_expression(
            schedule.schedule_expression,
            label="Flow",
        )
        timing = launchd_timing(expression, label="Flow")
        label = self._label(workspace_id, schedule.flow_id)
        plist_path = self.plist_path(workspace_id, schedule.flow_id)
        try:
            plist_path.parent.mkdir(parents=True, exist_ok=True)
            plist_path.parent.chmod(0o700)
            self.state_root.joinpath("logs").mkdir(parents=True, exist_ok=True)
            self.state_root.joinpath("logs").chmod(0o700)
            _atomic_write(
                plist_path,
                self._plist_bytes(
                    workspace,
                    workspace_id,
                    schedule.flow_id,
                    label,
                    timing,
                ),
            )
        except OSError as exc:
            raise PreflightError(f"Unable to prepare Flow schedule: {plist_path}") from exc

        domain = f"gui/{os.getuid()}"
        _launchctl("bootout", domain, plist_path, ignore_failure=True)
        _launchctl("bootstrap", domain, plist_path)

    def remove(self, workspace_id: UUID, flow_id: str) -> None:
        """Unload and remove one Flow's LaunchAgent."""

        plist_path = self.plist_path(workspace_id, flow_id)
        if sys.platform == "darwin" and plist_path.exists():
            _launchctl("bootout", f"gui/{os.getuid()}", plist_path, ignore_failure=True)
        try:
            plist_path.unlink(missing_ok=True)
        except OSError as exc:
            raise PreflightError(f"Unable to remove Flow schedule: {plist_path}") from exc

    def plist_path(self, workspace_id: UUID, flow_id: str) -> Path:
        """Return a stable LaunchAgent path for one Flow schedule."""

        return self.launch_agents_dir / f"{self._label(workspace_id, flow_id)}.plist"

    def _label(self, workspace_id: UUID, flow_id: str) -> str:
        return f"com.lumon.flow.{workspace_id}.{flow_id}"

    def _plist_bytes(
        self,
        workspace: Path,
        workspace_id: UUID,
        flow_id: str,
        label: str,
        timing: dict[str, object],
    ) -> bytes:
        log_dir = self.state_root / "logs"
        return plistlib.dumps(
            {
                "Label": label,
                "ProgramArguments": [
                    sys.executable,
                    "-m",
                    "lumon",
                    "flow",
                    "poll",
                    "--workspace",
                    str(workspace),
                    "--workspace-id",
                    str(workspace_id),
                    "--flow-id",
                    flow_id,
                    "--json",
                ],
                "WorkingDirectory": str(workspace),
                "EnvironmentVariables": {
                    "HOME": str(Path.home()),
                    "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
                    "LUMON_HOME": str(self.state_root),
                },
                "StandardOutPath": str(log_dir / f"flow-{workspace_id}-{flow_id}.log"),
                "StandardErrorPath": str(log_dir / f"flow-{workspace_id}-{flow_id}.error.log"),
                "RunAtLoad": False,
                **timing,
            },
            fmt=plistlib.FMT_XML,
            sort_keys=True,
        )


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
        raise PreflightError("Unable to communicate with the macOS Flow scheduler.") from exc
    if result.returncode and not ignore_failure:
        raise PreflightError("Unable to install Flow schedule: launchctl failed.")


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
        raise PreflightError(f"Unable to write Flow schedule: {path}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
