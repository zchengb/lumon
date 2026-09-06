"""Human and JSON output at the CLI interface."""

from __future__ import annotations

import json
from typing import Any

import typer

from lumon.errors import LumonError
from lumon.update import UpdateResult, UpdateStatus
from lumon.workspace.doctor import DoctorReport
from lumon.workspace.model import InitResult


def emit_init(result: InitResult, json_output: bool) -> None:
    """Render an initialization result without leaking internal objects."""

    if json_output:
        typer.echo(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return

    typer.echo(f"Workspace: {result.workspace}")
    typer.echo(f"Status: {result.status}")
    if result.installed_skills:
        typer.echo(f"Skills installed: {', '.join(result.installed_skills)}")
    if result.skipped_skills:
        typer.echo(f"Skills skipped: {', '.join(result.skipped_skills)}")
    if result.planned_skills:
        typer.echo(f"Skills to install: {', '.join(result.planned_skills)}")
    if result.created_paths:
        typer.echo(f"Created paths: {len(result.created_paths)}")


def emit_doctor(report: DoctorReport, json_output: bool) -> None:
    """Render a diagnostic report."""

    if json_output:
        typer.echo(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return

    for check in report.checks:
        marker = "ok" if check.ok else "fail"
        typer.echo(f"[{marker}] {check.name}: {check.detail}")


def emit_update(result: UpdateResult, json_output: bool) -> None:
    """Render an update result without exposing implementation details."""

    if json_output:
        typer.echo(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return

    if result.status is UpdateStatus.UP_TO_DATE:
        typer.echo(f"Lumon {result.current_version} is up to date.")
    elif result.status is UpdateStatus.UPDATE_AVAILABLE:
        typer.echo(f"Update available: Lumon {result.current_version} -> {result.latest_version}.")
    else:
        typer.echo(f"Lumon updated: {result.current_version} -> {result.latest_version}.")


def emit_error(error: LumonError, json_output: bool) -> None:
    """Render a stable error and let the command choose the exit code."""

    if json_output:
        payload: dict[str, Any] = {
            "ok": False,
            "error": {"type": type(error).__name__, "message": str(error)},
        }
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), err=True)
    else:
        typer.echo(f"Error: {error}", err=True)
