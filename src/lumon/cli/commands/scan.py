"""Run and inspect Lumon Auto Scan reviews."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated
from uuid import UUID

import typer

from lumon.errors import LumonError, PreflightError
from lumon.scan.model import ScanRun
from lumon.scan.service import ScanService
from lumon.workspace.layout import WorkspaceLayout
from lumon.workspace.manifest import load_manifest
from lumon.workspace.settings import WorkspaceSettingsStore

scan_app = typer.Typer(
    name="scan",
    help="Run and inspect Auto Scan code reviews.",
    no_args_is_help=True,
    add_completion=False,
)


@scan_app.command("run")
def run(
    workspace: Annotated[Path, typer.Option("--workspace", dir_okay=True)] = Path("."),
    workspace_id: Annotated[str | None, typer.Option("--workspace-id")] = None,
    run_id: Annotated[str | None, typer.Option("--run-id")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Run one manual Auto Scan, regardless of its schedule toggle."""

    try:
        _root, manifest_id = _workspace_identity(workspace)
        selected_id = _parse_workspace_id(workspace_id) if workspace_id else manifest_id
        if selected_id != manifest_id:
            raise PreflightError("The requested Workspace ID does not match its manifest.")
        result = ScanService().run(selected_id, force=True, run_id=run_id)
        _emit(result, json_output)
    except LumonError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from exc


@scan_app.command("poll")
def poll(
    workspace: Annotated[Path, typer.Option("--workspace", dir_okay=True)] = Path("."),
    workspace_id: Annotated[str | None, typer.Option("--workspace-id")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Run one scheduled Auto Scan when the Workspace setting is enabled."""

    try:
        _root, manifest_id = _workspace_identity(workspace)
        selected_id = _parse_workspace_id(workspace_id) if workspace_id else manifest_id
        if selected_id != manifest_id:
            raise PreflightError("The requested Workspace ID does not match its manifest.")
        settings = WorkspaceSettingsStore().load(selected_id)
        if not settings.auto_scan.enabled:
            _emit_poll({"status": "disabled", "workspace_id": str(selected_id)}, json_output)
            return
        result = ScanService().run(selected_id)
        _emit(result, json_output)
    except LumonError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from exc


@scan_app.command("history")
def history(
    workspace: Annotated[Path, typer.Option("--workspace", dir_okay=True)] = Path("."),
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """List persisted Auto Scan history."""

    try:
        root, _workspace_id = _workspace_identity(workspace)
        runs = ScanService().list_runs(root)
        payload = [run.as_payload() for run in runs]
        if json_output:
            typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            for run in runs:
                typer.echo(f"{run.run_id}  {run.state.value}  {run.started_at.isoformat()}")
    except LumonError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from exc


def _workspace_identity(workspace: Path) -> tuple[Path, UUID]:
    root = workspace.expanduser().resolve()
    manifest = load_manifest(WorkspaceLayout.from_root(root).manifest)
    return root, manifest.workspace_id


def _parse_workspace_id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise PreflightError("Workspace ID must be a valid UUID.") from exc


def _emit(result: ScanRun, json_output: bool) -> None:
    payload = result.as_payload()
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    typer.echo(f"Auto Scan: {result.state.value}")
    if result.findings:
        typer.echo(f"Findings: {len(result.findings)}")


def _emit_poll(payload: dict[str, object], json_output: bool) -> None:
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    typer.echo(f"Auto Scan poll: {payload['status']}")
