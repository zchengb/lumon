"""The ``lumon doctor`` command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from lumon.cli.output import emit_doctor
from lumon.visual import environment
from lumon.workspace.doctor import Doctor


def command(
    workspace: Annotated[
        Path | None,
        typer.Option("--workspace", help="Optional Workspace directory to validate."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Render a JSON report.")] = False,
    visual: Annotated[
        bool, typer.Option("--visual", help="Inspect visual tools without starting devices.")
    ] = False,
) -> None:
    """Run read-only environment and Workspace checks."""

    if visual:
        snapshot = environment.get_environment(refresh=True)
        if json_output:
            typer.echo(snapshot.prompt_text())
        else:
            for item in snapshot.environments:
                typer.echo(f"{item.platform}: {item.status}")
                for check in item.checks:
                    typer.echo(f"  {check.name}: {check.status}")
            typer.echo("Application build, login and interactions remain unverified.")
        return

    report = Doctor().inspect(workspace)
    emit_doctor(report, json_output)
    if not report.ok:
        raise typer.Exit(code=3)
