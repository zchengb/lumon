"""The ``lumon agent`` lifecycle commands for Mark."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import signal
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated
from uuid import UUID

import typer

from lumon.agents.mark.codex import CodexRunner
from lumon.agents.mark.config import MarkAgentConfig, MarkConfigStore
from lumon.agents.mark.service import MarkAgentService
from lumon.agents.mark.workspace_context import WorkspaceContextBuilder
from lumon.errors import AgentConfigError, AgentRuntimeError, LumonError
from lumon.workspace.registry import UserStateLayout, WorkspaceRegistry

agent_app = typer.Typer(
    name="agent",
    help="Configure and run the local Mark Agent.",
    no_args_is_help=True,
    add_completion=False,
)


@dataclass(frozen=True, slots=True)
class AgentDoctorCheck:
    """One safe Mark diagnostic."""

    name: str
    ok: bool
    detail: str


@dataclass(frozen=True, slots=True)
class AgentDoctorReport:
    """The complete Mark diagnostic report."""

    checks: tuple[AgentDoctorCheck, ...]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    def to_dict(self) -> dict[str, object]:
        return {"ok": self.ok, "checks": [asdict(check) for check in self.checks]}


@agent_app.command("configure")
def configure() -> None:
    """Interactively save Feishu and default Workspace settings for Mark."""

    store = MarkConfigStore()
    existing = _load_existing(store)
    app_id = typer.prompt("Feishu App ID", default=existing.feishu_app_id if existing else "")
    app_secret = typer.prompt("Feishu App Secret", hide_input=True, default="")
    if not app_secret.strip() and existing is not None:
        app_secret = existing.feishu_app_secret

    registry = WorkspaceRegistry()
    default_id = _prompt_workspace_id(registry, existing.default_workspace_id if existing else None)
    config = MarkAgentConfig(
        enabled=True,
        default_workspace_id=default_id,
        codex_model=existing.codex_model if existing else None,
        feishu_app_id=app_id.strip(),
        feishu_app_secret=app_secret,
    )
    try:
        store.save(config)
    except LumonError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from exc
    typer.echo(f"Mark configuration saved: {store.path}")
    typer.echo("App Secret stored with owner-only file permissions.")


@agent_app.command("doctor")
def doctor(
    json_output: Annotated[bool, typer.Option("--json", help="Render a JSON report.")] = False,
) -> None:
    """Check Mark configuration, dependencies, Codex login, and Workspace."""

    report = _inspect_agent()
    if json_output:
        typer.echo(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for check in report.checks:
            marker = "ok" if check.ok else "fail"
            typer.echo(f"[{marker}] {check.name}: {check.detail}")
    if not report.ok:
        raise typer.Exit(code=3)


@agent_app.command("start")
def start(
    background: Annotated[
        bool, typer.Option("--background", help="Run Mark as a detached local process.")
    ] = False,
    child: Annotated[
        bool, typer.Option("--child", hidden=True, help="Internal detached-process marker.")
    ] = False,
) -> None:
    """Start Mark's Feishu WebSocket listener."""

    try:
        if background and not child:
            _start_background()
            return
        typer.echo(
            "Warning: Mark runs requested Workspace actions in full-access mode.",
            err=True,
        )
        asyncio.run(_run_foreground())
    except KeyboardInterrupt:
        return
    except LumonError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from exc


@agent_app.command("status")
def status(
    json_output: Annotated[bool, typer.Option("--json", help="Render JSON status.")] = False,
) -> None:
    """Show whether the local Mark process is running."""

    payload = _runtime_status()
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        typer.echo(f"Status: {payload['status']}")
        if payload.get("pid") is not None:
            typer.echo(f"PID: {payload['pid']}")
        typer.echo(f"State: {payload['state_file']}")


@agent_app.command("stop")
def stop() -> None:
    """Stop the locally managed Mark process."""

    layout = UserStateLayout.from_root()
    pid_path = layout.root / "mark-agent.pid"
    pid = _read_pid(pid_path)
    if pid is None:
        typer.echo("Mark is not running.")
        return
    if not _pid_is_running(pid):
        pid_path.unlink(missing_ok=True)
        (layout.root / "mark-agent.status.json").unlink(missing_ok=True)
        typer.echo("Removed stale Mark runtime state.")
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as exc:
        raise typer.BadParameter(f"Unable to stop Mark process {pid}: {exc}") from exc
    typer.echo(f"Stop requested for Mark (PID {pid}).")


def _inspect_agent() -> AgentDoctorReport:
    store = MarkConfigStore()
    checks: list[AgentDoctorCheck] = []
    config: MarkAgentConfig | None = None
    try:
        config = store.load()
    except AgentConfigError as exc:
        checks.append(AgentDoctorCheck("configuration", False, str(exc)))
    else:
        permission_ok = store.is_owner_only()
        checks.append(
            AgentDoctorCheck(
                "configuration",
                permission_ok,
                "configured with owner-only permissions"
                if permission_ok
                else "file mode must be 600",
            )
        )
        checks.append(
            AgentDoctorCheck(
                "agent_enabled",
                config.enabled,
                "enabled" if config.enabled else "disabled; run lumon agent configure",
            )
        )

    sdk_available = importlib.util.find_spec("lark_channel") is not None
    checks.append(
        AgentDoctorCheck(
            "feishu_sdk",
            sdk_available,
            "lark-channel-sdk available" if sdk_available else "lark-channel-sdk is unavailable",
        )
    )

    runner = CodexRunner()
    binary = Path(runner.binary)
    binary_ok = binary.is_file() and os.access(binary, os.X_OK)
    checks.append(
        AgentDoctorCheck(
            "codex_cli",
            binary_ok,
            str(binary) if binary_ok else "Codex CLI not found",
        )
    )
    if binary_ok:
        login_ok = _codex_login_ok(runner.binary)
        checks.append(
            AgentDoctorCheck(
                "codex_login",
                login_ok,
                "logged in" if login_ok else "Codex login is unavailable",
            )
        )
    else:
        checks.append(
            AgentDoctorCheck("codex_login", False, "skipped because Codex CLI is missing")
        )

    if config is not None:
        try:
            context = WorkspaceContextBuilder(config, WorkspaceRegistry())
            resolved = context.resolve_workspace()
        except LumonError as exc:
            checks.append(AgentDoctorCheck("default_workspace", False, str(exc)))
        else:
            checks.append(AgentDoctorCheck("default_workspace", True, str(resolved.path)))
    else:
        checks.append(
            AgentDoctorCheck("default_workspace", False, "skipped until Mark is configured")
        )

    state_layout = UserStateLayout.from_root()
    state_parent_ok = _parent_is_writable(state_layout.root)
    checks.append(
        AgentDoctorCheck(
            "runtime_state",
            state_parent_ok,
            str(state_layout.root / "mark.sqlite3")
            if state_parent_ok
            else f"not writable: {state_layout.root}",
        )
    )
    database_path = state_layout.root / "mark.sqlite3"
    database_mode_ok = not database_path.exists() or _owner_only(database_path)
    checks.append(
        AgentDoctorCheck(
            "database_permissions",
            database_mode_ok,
            "owner-only permissions" if database_mode_ok else "mark.sqlite3 file mode must be 600",
        )
    )
    return AgentDoctorReport(tuple(checks))


def _load_existing(store: MarkConfigStore) -> MarkAgentConfig | None:
    try:
        return store.load()
    except AgentConfigError:
        return None


def _prompt_workspace_id(registry: WorkspaceRegistry, existing: UUID | None) -> UUID | None:
    try:
        workspaces = registry.list()
    except LumonError as exc:
        typer.echo(f"Warning: unable to list Workspaces: {exc}", err=True)
        workspaces = ()
    if len(workspaces) == 1 and existing is None:
        return workspaces[0].workspace_id
    if len(workspaces) > 1:
        typer.echo("Known Workspaces:")
        for workspace in workspaces:
            typer.echo(f"  {workspace.workspace_id}  {workspace.name}  {workspace.path}")
    default = str(existing) if existing else ""
    raw = typer.prompt("Default Workspace ID (optional)", default=default, show_default=False)
    if not raw.strip():
        return None
    try:
        return UUID(raw.strip())
    except ValueError as exc:
        raise typer.BadParameter("Default Workspace ID must be a UUID.") from exc


async def _run_foreground() -> None:
    service = MarkAgentService()
    pid = os.getpid()
    layout = UserStateLayout.from_root()
    pid_path = layout.root / "mark-agent.pid"
    existing_pid = _read_pid(pid_path)
    if existing_pid is not None and existing_pid != pid and _pid_is_running(existing_pid):
        raise AgentRuntimeError(f"Mark is already running (PID {existing_pid}).")
    _write_runtime_state("running", pid)
    pid_path.write_text(str(pid) + "\n", encoding="utf-8")
    pid_path.chmod(0o600)
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for value in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(value, stop_event.set)
        except (NotImplementedError, RuntimeError):
            pass
    try:
        service_task = asyncio.create_task(service.run_forever())
        stop_task = asyncio.create_task(stop_event.wait())
        try:
            done, _ = await asyncio.wait(
                (service_task, stop_task), return_when=asyncio.FIRST_COMPLETED
            )
            if service_task in done:
                await service_task
            else:
                await service.stop()
                await service_task
        finally:
            stop_task.cancel()
            await asyncio.gather(stop_task, return_exceptions=True)
    finally:
        if _read_pid(pid_path) == pid:
            pid_path.unlink(missing_ok=True)
            _write_runtime_state("stopped", None)


def _start_background() -> None:
    layout = UserStateLayout.from_root()
    pid_path = layout.root / "mark-agent.pid"
    current = _read_pid(pid_path)
    if current is not None and _pid_is_running(current):
        raise typer.BadParameter(f"Mark is already running (PID {current}).")
    try:
        layout.root.mkdir(parents=True, exist_ok=True)
        layout.root.chmod(0o700)
        process = subprocess.Popen(
            [sys.executable, "-m", "lumon", "agent", "start", "--child"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        pid_path.write_text(str(process.pid) + "\n", encoding="utf-8")
        pid_path.chmod(0o600)
        _write_runtime_state("running", process.pid)
    except OSError as exc:
        raise AgentRuntimeError("Unable to start Mark in the background.") from exc
    typer.echo(f"Mark started in background (PID {process.pid}).")


def _write_runtime_state(status: str, pid: int | None) -> None:
    layout = UserStateLayout.from_root()
    layout.root.mkdir(parents=True, exist_ok=True)
    layout.root.chmod(0o700)
    path = layout.root / "mark-agent.status.json"
    path.write_text(
        json.dumps({"status": status, "pid": pid}, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def _runtime_status() -> dict[str, object]:
    layout = UserStateLayout.from_root()
    pid_path = layout.root / "mark-agent.pid"
    pid = _read_pid(pid_path)
    running = pid is not None and _pid_is_running(pid)
    if not running and pid is not None:
        pid_path.unlink(missing_ok=True)
        (layout.root / "mark-agent.status.json").unlink(missing_ok=True)
    return {
        "status": "running" if running else "stopped",
        "pid": pid if running else None,
        "state_file": str(layout.root / "mark-agent.status.json"),
    }


def _read_pid(path: Path) -> int | None:
    try:
        value = path.read_text(encoding="utf-8").strip()
        pid = int(value)
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    return pid if pid > 0 else None


def _pid_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _parent_is_writable(path: Path) -> bool:
    current = path
    while not current.exists() and current != current.parent:
        current = current.parent
    return current.is_dir() and os.access(current, os.W_OK)


def _owner_only(path: Path) -> bool:
    try:
        return path.stat().st_mode & 0o777 == 0o600
    except OSError:
        return False


def _codex_login_ok(binary: str) -> bool:
    try:
        result = subprocess.run(
            [binary, "login", "status"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0
