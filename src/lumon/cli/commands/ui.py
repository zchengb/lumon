"""The ``lumon ui`` command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated
from uuid import UUID

import typer

from lumon.dashboard.server import DashboardServer, create_dashboard_app
from lumon.dashboard.service import DashboardService
from lumon.errors import LumonError


def command(
    workspace: Annotated[
        Path | None,
        typer.Option("--workspace", help="Workspace to select when the Dashboard opens."),
    ] = None,
    port: Annotated[
        int, typer.Option("--port", help="Local TCP port; 0 selects an available port.")
    ] = 0,
    no_open: Annotated[
        bool, typer.Option("--no-open", help="Start the Dashboard without opening a browser.")
    ] = False,
) -> None:
    """Start the local Lumon Dashboard."""

    try:
        service = DashboardService()
        initial_workspace_id: UUID | None = None
        if workspace is not None:
            initial_workspace_id = service.register_workspace(workspace).workspace_id
        server = DashboardServer(
            app=create_dashboard_app(service),
            initial_workspace_id=initial_workspace_id,
        )
        server.run(port=port, open_browser=not no_open)
    except LumonError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from exc
