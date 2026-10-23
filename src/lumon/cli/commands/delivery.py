"""Manage Auto Delivery lifecycle receipts and notifications."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

import typer

from lumon.agents.agent.model import AgentResult
from lumon.agents.agent.runner import create_agent_runner
from lumon.delivery.control import request_stop, save_checkpoint
from lumon.delivery.execution import resume_delivery, run_poll
from lumon.delivery.model import (
    DeliveryEvent,
    DeliveryRun,
)
from lumon.delivery.scheduler import delivery_lock
from lumon.delivery.service import DeliveryNotification, DeliveryService
from lumon.errors import LumonError, PreflightError
from lumon.observability import redact_text
from lumon.tools.safety import sanitize_output
from lumon.workspace.layout import WorkspaceLayout
from lumon.workspace.manifest import load_manifest
from lumon.workspace.registry import UserStateLayout
from lumon.workspace.settings import AutoDeliverySettings, WorkspaceSettingsStore

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
    poll_id: Annotated[
        str | None, typer.Option("--poll-id", help="Parent scheduled poll ID.")
    ] = None,
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
            poll_id=poll_id,
        )
        notification = DeliveryService().start(root, workspace_id, run)
        _emit(run, notification, json_output)
    except LumonError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from exc


@delivery_app.command("progress")
def progress(
    run_id: Annotated[str, typer.Option("--run-id")],
    phase: Annotated[str, typer.Option("--phase")],
    detail: Annotated[str, typer.Option("--detail")],
    workspace: Annotated[Path, typer.Option("--workspace", dir_okay=True)] = Path("."),
) -> None:
    """Publish a safe phase summary for the Dashboard's live progress view."""

    try:
        root, _workspace_id = _workspace_identity(workspace)
        service = DeliveryService()
        run = service.run_store.load(root, run_id)
        updated = service.progress(root, run, phase=phase, detail=redact_text(detail)[:500])
        typer.echo(f"Delivery {updated.run_id}: {updated.phase}")
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
    branch: Annotated[
        str | None,
        typer.Option("--branch", help="Published branch; direct mode uses the target branch."),
    ] = None,
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


@delivery_app.command("poll")
def poll(
    workspace: Annotated[Path, typer.Option("--workspace", dir_okay=True)] = Path("."),
    workspace_id: Annotated[str | None, typer.Option("--workspace-id")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Run one scheduled Auto Delivery detection turn for a Workspace."""

    try:
        root, manifest_id = _workspace_identity(workspace)
        selected_id = _parse_workspace_id(workspace_id) if workspace_id else manifest_id
        if selected_id != manifest_id:
            raise PreflightError("The requested Workspace ID does not match its manifest.")

        state_layout = UserStateLayout.from_root()
        settings = WorkspaceSettingsStore(state_layout.root).load(selected_id)
        if not settings.auto_delivery.enabled:
            _emit_poll(
                {"status": "disabled", "workspace_id": str(selected_id)},
                json_output,
            )
            return

        with delivery_lock(state_layout.root, selected_id):
            result = asyncio.run(_run_poll(root, selected_id, settings.auto_delivery))
        safe_text = sanitize_output((result.final_text or "").strip())[:500]
        status = "idle" if safe_text == "AUTO_DELIVERY_IDLE" else "completed"
        _emit_poll(
            {
                "status": status,
                "workspace_id": str(selected_id),
                "detail": safe_text,
            },
            json_output,
        )
    except asyncio.CancelledError:
        _emit_poll({"status": "stopped", "detail": "Agent stopped; work preserved."}, json_output)
    except LumonError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from exc


@delivery_app.command("resume")
def resume(
    run_id: Annotated[str, typer.Option("--run-id")],
    attempt: Annotated[int, typer.Option("--attempt", min=1)],
    workspace: Annotated[Path, typer.Option("--workspace")] = Path("."),
) -> None:
    """Continue one failed/blocked/stopped receipt without discarding its work."""
    try:
        root, workspace_id = _workspace_identity(workspace)
        asyncio.run(resume_delivery(root, workspace_id, run_id, attempt=attempt))
    except asyncio.CancelledError:
        typer.echo("Delivery stopped; work and checkpoint preserved.")
    except LumonError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from exc


@delivery_app.command("stop")
def stop(
    run_id: Annotated[str, typer.Option("--run-id")],
    attempt: Annotated[int, typer.Option("--attempt", min=1)],
    workspace: Annotated[Path, typer.Option("--workspace")] = Path("."),
) -> None:
    """Request interruption; Stopped is acknowledged only after the Agent exits."""
    try:
        root, workspace_id = _workspace_identity(workspace)
        request_stop(DeliveryService().run_store, root, workspace_id, run_id, attempt=attempt)
        typer.echo("Stop requested; waiting for the owning worker to stop.")
    except LumonError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from exc


@delivery_app.command("checkpoint")
def checkpoint(
    run_id: Annotated[str, typer.Option("--run-id")],
    detail: Annotated[str, typer.Option("--detail")],
    result_comment_id: Annotated[str | None, typer.Option("--result-comment-id")] = None,
    workspace: Annotated[Path, typer.Option("--workspace")] = Path("."),
) -> None:
    """Save a safe handoff and source fingerprint, optionally the one Jira result comment ID."""
    try:
        root, _ = _workspace_identity(workspace)
        save_checkpoint(
            DeliveryService().run_store, root, run_id, detail=detail, comment_id=result_comment_id
        )
        typer.echo("Delivery checkpoint saved.")
    except (LumonError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code if isinstance(exc, LumonError) else 2) from exc


async def _run_poll(
    workspace: Path, workspace_id: UUID, settings: AutoDeliverySettings
) -> AgentResult:
    return await run_poll(workspace, workspace_id, settings, runner_factory=create_agent_runner)


def _parse_workspace_id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise PreflightError("Workspace ID must be a valid UUID.") from exc


def _emit_poll(payload: dict[str, object], json_output: bool) -> None:
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    typer.echo(f"Auto Delivery poll: {payload['status']}")
    if payload.get("detail"):
        typer.echo(str(payload["detail"]))


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
