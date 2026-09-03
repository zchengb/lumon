"""The ``lumon doctor`` command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from lumon.cli.output import emit_doctor
from lumon.workspace.doctor import Doctor


def command(
    workspace: Annotated[
        Path | None,
        typer.Option("--workspace", help="Optional Workspace directory to validate."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Render a JSON report.")] = False,
) -> None:
    """Run read-only environment and Workspace checks."""

    report = Doctor().inspect(workspace)
    emit_doctor(report, json_output)
    if not report.ok:
        raise typer.Exit(code=3)
