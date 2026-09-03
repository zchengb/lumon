"""The ``lumon init`` command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from lumon.cli.output import emit_error, emit_init
from lumon.errors import LumonError
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.model import InitRequest


def command(
    path: Annotated[Path, typer.Argument(help="Workspace directory to initialize.")],
    name: Annotated[
        str | None, typer.Option("--name", help="Human-readable Workspace name.")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show changes without writing.")
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Render a JSON result.")] = False,
) -> None:
    """Initialize one Workspace and install missing global Skills."""

    try:
        result = WorkspaceInitializer().initialize(InitRequest(path, name=name, dry_run=dry_run))
    except LumonError as exc:
        emit_error(exc, json_output)
        raise typer.Exit(code=exc.exit_code) from exc
    emit_init(result, json_output)
