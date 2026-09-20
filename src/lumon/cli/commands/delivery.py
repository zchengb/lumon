"""Manage Auto Delivery lifecycle receipts and notifications."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

import typer

from lumon.delivery.model import DeliveryEvent, DeliveryRun
from lumon.delivery.service import DeliveryNotification, DeliveryService
from lumon.errors import LumonError, PreflightError
from lumon.workspace.layout import WorkspaceLayout
from lumon.workspace.manifest import load_manifest

delivery_app = typer.Typer(
    name="delivery",
    help="Run and inspect Auto Delivery lifecycle notifications.",
    no_args_is_help=True,
    add_completion=False,
)
FinishOperation = Callable[
    [DeliveryService, Path, UUID, DeliveryRun], tuple[DeliveryRun, DeliveryNotification]
]


@delivery_app.command("start")
def start(
    story_key: Annotated[str, typer.Option("--story-key", help="Jira Story key.")],
    story_title: Annotated[str, typer.Option("--story-title", help="Story title.")],
    workspace: Annotated[Path, typer.Option("--workspace", dir_okay=True)] = Path("."),
    run_id: Annotated[
        str | None, typer.Option("--run-id", help="Stable run ID; generated when omitted.")
    ] = None,
    jira_url: Annotated[str | None, typer.Option("--jira-url")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Create a Delivery run and send its started notification."""

    try:
        root, workspace_id = _workspace_identity(workspace)
        run = DeliveryRun.claim(
            run_id or str(uuid4()),
            story_key.strip(),
            story_title.strip(),
            workspace_id=workspace_id,
            jira_url=jira_url.strip() if jira_url else None,
        )
        notification = DeliveryService().start(root, workspace_id, run)
        _emit(run, notification, json_output)
    except LumonError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from exc


@delivery_app.command("notify")
def notify(
    event: Annotated[str, typer.Argument(help="One of the four delivery event names.")],
    run_id: Annotated[str, typer.Option("--run-id")],
    workspace: Annotated[Path, typer.Option("--workspace", dir_okay=True)] = Path("."),
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Retry one lifecycle notification for a persisted run."""

    try:
        root, workspace_id = _workspace_identity(workspace)
        selected = _event(event)
        service = DeliveryService()
        run = service.run_store.load(root, run_id)
        result = service.notify(root, workspace_id, run, selected)
        _emit(run, result, json_output)
    except (LumonError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code if isinstance(exc, LumonError) else 2) from exc


@delivery_app.command("complete")
def complete(
    run_id: Annotated[str, typer.Option("--run-id")],
    detail: Annotated[str, typer.Option("--detail")],
    workspace: Annotated[Path, typer.Option("--workspace", dir_okay=True)] = Path("."),
    phase: Annotated[str, typer.Option("--phase")] = "publish",
    repository: Annotated[str | None, typer.Option("--repository")] = None,
    branch: Annotated[str | None, typer.Option("--branch")] = None,
    pull_request_url: Annotated[str | None, typer.Option("--pull-request-url")] = None,
    verification_summary: Annotated[str | None, typer.Option("--verification")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Record successful verification and publishing, then notify the user."""

    try:
        root, workspace_id = _workspace_identity(workspace)
        service = DeliveryService()
        run = service.run_store.load(root, run_id)
        updated, notification = service.complete(
            root,
            workspace_id,
            run,
            detail,
            phase=phase,
            repository=repository,
            branch=branch,
            pull_request_url=pull_request_url,
            verification_summary=verification_summary,
        )
        _emit(updated, notification, json_output)
    except LumonError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from exc


@delivery_app.command("fail")
def fail(
    run_id: Annotated[str, typer.Option("--run-id")],
    reason: Annotated[str, typer.Option("--reason")],
    phase: Annotated[str, typer.Option("--phase")],
    workspace: Annotated[Path, typer.Option("--workspace", dir_okay=True)] = Path("."),
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Record an unexpected Delivery failure and notify the user."""

    _finish(
        workspace,
        run_id,
        json_output,
        lambda service, root, workspace_id, run: service.fail(
            root, workspace_id, run, reason, phase=phase
        ),
    )


@delivery_app.command("block")
def block(
    run_id: Annotated[str, typer.Option("--run-id")],
    reason: Annotated[str, typer.Option("--reason")],
    phase: Annotated[str, typer.Option("--phase")],
    workspace: Annotated[Path, typer.Option("--workspace", dir_okay=True)] = Path("."),
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Record a known prerequisite or verification block and notify the user."""

    _finish(
        workspace,
        run_id,
        json_output,
        lambda service, root, workspace_id, run: service.block(
            root, workspace_id, run, reason, phase=phase
        ),
    )


def _workspace_identity(workspace: Path) -> tuple[Path, UUID]:
    root = workspace.expanduser().resolve()
    manifest = load_manifest(WorkspaceLayout.from_root(root).manifest)
    return root, manifest.workspace_id


def _finish(
    workspace: Path,
    run_id: str,
    json_output: bool,
    operation: FinishOperation,
) -> None:
    try:
        root, workspace_id = _workspace_identity(workspace)
        service = DeliveryService()
        run = service.run_store.load(root, run_id)
        updated, notification = operation(service, root, workspace_id, run)
        _emit(updated, notification, json_output)
    except LumonError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from exc


def _event(value: str) -> DeliveryEvent:
    try:
        return DeliveryEvent(value)
    except ValueError as exc:
        raise PreflightError(
            "Unknown Delivery event. Use delivery.started, delivery.dev_done, "
            "delivery.failed, or delivery.blocked."
        ) from exc


def _emit(run: DeliveryRun, notification: DeliveryNotification, json_output: bool) -> None:
    payload = {
        "run_id": run.run_id,
        "state": run.state.value,
        "event": notification.event.value,
        "sent": notification.sent,
        "skipped": notification.skipped,
        "detail": notification.detail,
    }
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    typer.echo(f"Run: {run.run_id}")
    typer.echo(f"Event: {notification.event.value}")
    typer.echo(f"Notification: {'sent' if notification.sent else notification.detail}")
