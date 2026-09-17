"""The ``lumon init`` command."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path
from typing import Annotated

import typer

from lumon.agents.agent.config import AgentConfigStore
from lumon.cli.output import emit_error, emit_init
from lumon.errors import AgentConfigError, LumonError
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.model import InitRequest, RepositorySpec
from lumon.workspace.registry import WorkspaceRegistry
from lumon.workspace.repositories import spec_from_url


def command(
    path: Annotated[Path, typer.Argument(help="Workspace directory to initialize.")],
    name: Annotated[
        str | None, typer.Option("--name", help="Human-readable Workspace name.")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show changes without writing.")
    ] = False,
    repository: Annotated[
        list[str] | None,
        typer.Option(
            "--repository",
            help="Git clone URL; repeat this option to add multiple Repositories.",
        ),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Render a JSON result.")] = False,
) -> None:
    """Initialize one Workspace, optionally cloning code Repositories."""

    try:
        specifications = collect_repository_specifications(repository, json_output)
        result = WorkspaceInitializer().initialize(
            InitRequest(path, name=name, repositories=specifications, dry_run=dry_run)
        )
        if result.status != "dry_run":
            _set_default_for_sole_workspace()
    except LumonError as exc:
        emit_error(exc, json_output)
        raise typer.Exit(code=exc.exit_code) from exc
    emit_init(result, json_output)


def collect_repository_specifications(
    urls: list[str] | None, json_output: bool
) -> tuple[RepositorySpec, ...]:
    """Resolve command-line URLs or collect them from an interactive terminal."""

    if urls:
        return tuple(spec_from_url(url) for url in urls)
    if json_output or not _interactive_terminal():
        return ()

    typer.echo("Repository setup (press Enter with an empty URL to finish):")
    if not typer.confirm("Add a Repository?", default=True):
        return ()
    specifications: list[RepositorySpec] = []
    while True:
        clone_url = typer.prompt("Git clone URL", default="", show_default=False).strip()
        if not clone_url:
            break
        try:
            specification = spec_from_url(clone_url)
        except LumonError as exc:
            typer.echo(f"Error: {exc}", err=True)
            continue
        if any(item.name == specification.name for item in specifications):
            typer.echo(f"Error: Duplicate Repository name: {specification.name}", err=True)
            continue
        specifications.append(specification)
        typer.echo(f"Identified Repository: {specification.name}")
        if not typer.confirm("Continue adding a Repository?", default=True):
            break
    return tuple(specifications)


def _interactive_terminal() -> bool:
    """Return whether both standard streams can safely support prompts."""

    return sys.stdin.isatty() and sys.stdout.isatty()


def _set_default_for_sole_workspace() -> None:
    """Select the only registered Workspace when Agent has a saved config."""

    registrations = WorkspaceRegistry().list()
    if len(registrations) != 1:
        return

    config_store = AgentConfigStore()
    try:
        config = config_store.load()
    except AgentConfigError:
        return

    workspace_id = registrations[0].workspace_id
    if config.default_workspace_id == workspace_id:
        return
    config_store.save(replace(config, default_workspace_id=workspace_id))
