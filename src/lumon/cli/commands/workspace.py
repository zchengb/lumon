"""Workspace registry and Agent default Workspace commands."""

from __future__ import annotations

import json
import shutil
from dataclasses import replace
from pathlib import Path
from typing import Annotated, NoReturn
from uuid import UUID

import typer

from lumon.agents.agent.config import AgentConfig, AgentConfigStore
from lumon.cli.output import emit_error
from lumon.errors import (
    AgentConfigError,
    InvalidInputError,
    LumonError,
    PreflightError,
    WorkspaceNotFoundError,
)
from lumon.workspace.config import load_workspace_config
from lumon.workspace.layout import WorkspaceLayout
from lumon.workspace.manifest import load_manifest
from lumon.workspace.registry import WorkspaceRegistration, WorkspaceRegistry
from lumon.workspace.settings import WorkspaceSettingsStore

workspace_app = typer.Typer(
    name="workspace",
    help="List and manage registered Workspaces.",
    no_args_is_help=True,
    add_completion=False,
)


@workspace_app.command("list")
def list_workspaces(
    json_output: Annotated[
        bool, typer.Option("--json", help="Render the Workspace list as JSON.")
    ] = False,
) -> None:
    """List registered Workspaces and identify Agent's default."""

    registry = WorkspaceRegistry()
    try:
        registrations = registry.list()
    except LumonError as exc:
        _fail(exc, json_output)

    default_workspace_id = _load_default_workspace_id()
    summaries = [_summary(registration, default_workspace_id) for registration in registrations]
    if json_output:
        typer.echo(
            json.dumps(
                {
                    "default_workspace_id": (
                        str(default_workspace_id) if default_workspace_id else None
                    ),
                    "workspaces": summaries,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return

    if not summaries:
        typer.echo("No Workspaces are registered.")
        return
    for item in summaries:
        marker = " (default)" if item["default"] else ""
        typer.echo(f"{item['workspace_id']}  {item['name']}  [{item['health']}]{marker}")
        typer.echo(f"  {item['path']}")


@workspace_app.command("set-default")
def set_default(
    target: Annotated[
        str | None,
        typer.Argument(help="Workspace UUID or path to make Agent's default."),
    ] = None,
    clear: Annotated[
        bool, typer.Option("--clear", help="Clear Agent's default Workspace.")
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Render the result as JSON.")] = False,
) -> None:
    """Set or clear Agent's default Workspace."""

    if clear == (target is not None):
        _fail(
            InvalidInputError("Provide one Workspace target or use --clear, but not both."),
            json_output,
        )

    config_store = AgentConfigStore()
    try:
        config = config_store.load()
        selected = None
        registration: WorkspaceRegistration | None = None
        if not clear:
            registry = WorkspaceRegistry()
            registration = _resolve_target(registry.list(), target or "")
            if _workspace_health(registration) != "ready":
                raise PreflightError(
                    f"Workspace is not ready: {registration.path}. "
                    "Run `lumon doctor --workspace <path>` for details."
                )
            selected = registration.workspace_id
        config_store.save(replace(config, default_workspace_id=selected))
    except LumonError as exc:
        _fail(exc, json_output)

    if json_output:
        typer.echo(
            json.dumps(
                {
                    "ok": True,
                    "default_workspace_id": str(selected) if selected else None,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return

    if registration is None:
        typer.echo("Default Workspace cleared.")
        return
    typer.echo(
        f"Default Workspace set to {registration.name} "
        f"({registration.workspace_id}) at {registration.path}."
    )


@workspace_app.command("remove")
def remove(
    target: Annotated[str, typer.Argument(help="Workspace UUID or path to remove from Lumon.")],
    delete: Annotated[
        bool,
        typer.Option(
            "--delete",
            help="Also permanently delete the Workspace directory and its repositories.",
        ),
    ] = False,
    yes: Annotated[
        bool, typer.Option("--yes", help="Skip the removal confirmation prompt.")
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Render the result as JSON.")] = False,
) -> None:
    """Unregister a Workspace and optionally delete its directory."""

    if json_output and not yes:
        _fail(InvalidInputError("`workspace remove --json` requires --yes."), json_output)

    registry = WorkspaceRegistry()
    settings = WorkspaceSettingsStore()
    config_store = AgentConfigStore()
    try:
        registration = _resolve_target(registry.list(), target)
        config = _load_config(config_store)
        default_cleared = bool(
            config is not None and config.default_workspace_id == registration.workspace_id
        )

        if default_cleared and delete:
            action = "clear Agent's default, unregister, and permanently delete"
        elif default_cleared:
            action = "clear Agent's default and unregister"
        elif delete:
            action = "unregister and permanently delete"
        else:
            action = "unregister"
        question = f"Confirm {action} Workspace '{registration.name}' at {registration.path}?"
        if delete:
            question += " This also deletes its cloned repositories."
        if default_cleared:
            question += " This also clears Agent's default Workspace."
        if not yes:
            typer.confirm(question, abort=True)

        if default_cleared:
            if config is None:  # pragma: no cover - guarded by default_cleared
                raise AgentConfigError("Agent configuration is unavailable.")
            config_store.save(replace(config, default_workspace_id=None))
        registry.unregister(registration.workspace_id)
        settings.remove(registration.workspace_id)
        deleted = _delete_directory(registration.path) if delete else False
    except LumonError as exc:
        _fail(exc, json_output)

    if json_output:
        typer.echo(
            json.dumps(
                {
                    "ok": True,
                    "workspace_id": str(registration.workspace_id),
                    "name": registration.name,
                    "path": str(registration.path),
                    "unregistered": True,
                    "default_cleared": default_cleared,
                    "deleted": deleted,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return

    typer.echo(f"Workspace unregistered: {registration.name} ({registration.workspace_id}).")
    if default_cleared:
        typer.echo("Agent's default Workspace cleared.")
    if deleted:
        typer.echo(f"Workspace directory deleted: {registration.path}")
    else:
        typer.echo(f"Workspace directory kept: {registration.path}")


def _resolve_target(
    registrations: tuple[WorkspaceRegistration, ...], target: str
) -> WorkspaceRegistration:
    """Resolve a CLI Workspace target as an ID or canonical filesystem path."""

    normalized = target.strip()
    if not normalized:
        raise InvalidInputError("Workspace target must be a UUID or path.")
    try:
        workspace_id = UUID(normalized)
    except ValueError:
        canonical = Path(normalized).expanduser().resolve()
        registration = next((item for item in registrations if item.path == canonical), None)
    else:
        registration = next(
            (item for item in registrations if item.workspace_id == workspace_id), None
        )
    if registration is None:
        raise WorkspaceNotFoundError(f"Workspace is not registered: {target}")
    return registration


def _load_default_workspace_id() -> UUID | None:
    """Return the configured default without making listing depend on Agent setup."""

    config = _load_config(AgentConfigStore())
    return config.default_workspace_id if config else None


def _load_config(config_store: AgentConfigStore) -> AgentConfig | None:
    """Load Agent configuration when available without blocking registry inspection."""

    try:
        return config_store.load()
    except AgentConfigError:
        return None


def _summary(
    registration: WorkspaceRegistration, default_workspace_id: UUID | None
) -> dict[str, object]:
    """Build the safe JSON and human-output data for one registration."""

    return {
        "workspace_id": str(registration.workspace_id),
        "name": registration.name,
        "path": str(registration.path),
        "registered_at": registration.registered_at,
        "health": _workspace_health(registration),
        "default": registration.workspace_id == default_workspace_id,
    }


def _workspace_health(registration: WorkspaceRegistration) -> str:
    """Return the same ready/missing/invalid health vocabulary as the Dashboard."""

    if not registration.path.is_dir():
        return "missing"
    layout = WorkspaceLayout.from_root(registration.path)
    try:
        manifest = load_manifest(layout.manifest)
        workspace_config = load_workspace_config(layout.workspace_config)
    except PreflightError:
        return "invalid"
    if manifest.workspace_id != registration.workspace_id or workspace_config.name != manifest.name:
        return "invalid"
    return "ready"


def _delete_directory(path: Path) -> bool:
    """Delete a registered Workspace path after explicit user confirmation."""

    if not path.exists() and not path.is_symlink():
        return False
    try:
        if path.is_symlink():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    except OSError as exc:
        raise PreflightError(f"Unable to delete Workspace directory: {path}") from exc
    return True


def _fail(error: LumonError, json_output: bool) -> NoReturn:
    """Render a command error and terminate with its stable Lumon exit code."""

    emit_error(error, json_output)
    raise typer.Exit(code=error.exit_code)
