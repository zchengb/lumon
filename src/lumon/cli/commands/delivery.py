"""Manage Auto Delivery lifecycle receipts and notifications."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

import typer

from lumon.agents.agent.config import AgentConfigStore
from lumon.agents.agent.model import AgentEvent, AgentProgress, AgentResult
from lumon.agents.agent.runner import create_agent_runner
from lumon.agents.agent.workspace_context import WorkspaceContextBuilder
from lumon.delivery.model import (
    DeliveryActivity,
    DeliveryEvent,
    DeliveryPoll,
    DeliveryPollState,
    DeliveryRun,
    DeliveryState,
)
from lumon.delivery.scheduler import delivery_lock
from lumon.delivery.service import DeliveryNotification, DeliveryService
from lumon.errors import AgentRuntimeError, LumonError, PreflightError
from lumon.observability import redact_text
from lumon.tools.safety import sanitize_output
from lumon.workspace.layout import WorkspaceLayout
from lumon.workspace.manifest import load_manifest
from lumon.workspace.registry import UserStateLayout, WorkspaceRegistry
from lumon.workspace.settings import WorkspaceSettingsStore

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
            result = asyncio.run(_run_poll(root, selected_id, settings.auto_delivery.trigger_hooks))
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
    except LumonError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from exc


async def _run_poll(
    workspace: Path,
    workspace_id: UUID,
    trigger_hooks: tuple[str, ...],
) -> AgentResult:
    state_layout = UserStateLayout.from_root()
    service = DeliveryService(settings_store=WorkspaceSettingsStore(state_layout.root))
    service.recover_interrupted_polls(workspace, workspace_id)
    poll = DeliveryPoll(uuid4().hex, workspace_id, DeliveryPollState.RUNNING, datetime.now(UTC))
    service.run_store.save_poll(workspace, poll)
    try:
        result = await _execute_poll(workspace, workspace_id, trigger_hooks, poll, service)
        claimed = tuple(
            run for run in service.run_store.list(workspace) if run.poll_id == poll.run_id
        )
        if any(run.state == DeliveryState.RUNNING for run in claimed):
            raise AgentRuntimeError(
                "Agent finished without recording the Story's terminal outcome."
            )
        unsuccessful = next((run for run in claimed if run.state != DeliveryState.COMPLETED), None)
        if unsuccessful is not None:
            raise AgentRuntimeError(
                f"Story {unsuccessful.story_key} {unsuccessful.state}: "
                f"{unsuccessful.detail or unsuccessful.reason or 'Delivery did not complete.'}"
            )
        idle = (result.final_text or "").strip() == "AUTO_DELIVERY_IDLE" and not claimed
        if not idle and not claimed:
            summary = redact_text(result.final_text or "")[:300]
            raise AgentRuntimeError(
                "Agent finished without an idle result or a claimed Story receipt. " + summary
            )
        service.run_store.save_poll(
            workspace,
            replace(
                service.run_store.load_poll(workspace, poll.run_id),
                state=DeliveryPollState.IDLE if idle else DeliveryPollState.COMPLETED,
                finished_at=datetime.now(UTC),
                detail=redact_text(result.final_text or "")[:500],
            ),
        )
        return result
    except (KeyboardInterrupt, asyncio.CancelledError):
        _fail_poll(workspace, poll, service, "Auto Delivery was interrupted before completion.")
        raise
    except Exception as exc:
        detail = redact_text(str(exc))[:500] or "Unexpected Auto Delivery failure."
        _fail_poll(workspace, poll, service, detail)
        if isinstance(exc, LumonError):
            raise
        raise AgentRuntimeError(detail) from exc


def _fail_poll(workspace: Path, poll: DeliveryPoll, service: DeliveryService, detail: str) -> None:
    service.run_store.save_poll(
        workspace,
        replace(
            service.run_store.load_poll(workspace, poll.run_id),
            state=DeliveryPollState.FAILED,
            finished_at=datetime.now(UTC),
            detail=detail,
        ),
    )
    for run in service.run_store.list(workspace):
        if run.poll_id == poll.run_id and run.state == DeliveryState.RUNNING:
            service.fail(workspace, poll.workspace_id, run, detail, phase=run.phase)


async def _execute_poll(
    workspace: Path,
    workspace_id: UUID,
    trigger_hooks: tuple[str, ...],
    poll: DeliveryPoll,
    service: DeliveryService,
) -> AgentResult:
    state_layout = UserStateLayout.from_root()
    config = AgentConfigStore(state_layout.root).load()
    if not config.enabled:
        raise PreflightError("The Lumon Agent is disabled.")
    registry = WorkspaceRegistry(state_layout.root)
    if registry.find(workspace_id) is None:
        raise PreflightError(f"Workspace is not registered: {workspace_id}")
    context_builder = WorkspaceContextBuilder(
        replace(config, default_workspace_id=workspace_id),
        registry,
    )
    context = context_builder.resolve_workspace()
    prompt = context_builder.build_prompt(
        context,
        (),
        _scheduled_poll_prompt(trigger_hooks, poll.run_id),
    )
    secrets = (
        config.feishu_app_secret,
        config.observability.secret_key,
        config.observability.public_key,
    )

    async def observe_progress(progress: AgentProgress) -> None:
        # Story stages come from explicit receipts, not generic Agent tool execution.
        phase = "discover"
        detail = redact_text(progress.message, secrets)[:500]
        service.run_store.save_poll(workspace, replace(poll, phase=phase, detail=detail))
        service.run_store.record_activity(
            workspace, poll.run_id, DeliveryActivity(datetime.now(UTC), phase, detail)
        )

    async def observe_event(event: AgentEvent) -> None:
        if event.kind == "progress":
            return  # Only the validated, bounded progress callback records Agent text.
        detail = f"{event.kind.replace('_', ' ')}: {event.lifecycle}"
        if event.exit_code is not None:
            detail += f" (exit {event.exit_code})"
        current = service.run_store.load_poll(workspace, poll.run_id)
        service.run_store.record_activity(
            workspace, poll.run_id, DeliveryActivity(datetime.now(UTC), current.phase, detail)
        )

    result = await create_agent_runner(config).run(
        workspace, prompt, on_progress=observe_progress, on_event=observe_event
    )
    if result.status != "succeeded":
        diagnostic = redact_text(
            result.failure_diagnostic or "Agent poll did not complete.", secrets
        )
        raise AgentRuntimeError(diagnostic)
    return replace(result, final_text=redact_text(result.final_text or "", secrets))


def _scheduled_poll_prompt(trigger_hooks: tuple[str, ...], poll_id: str) -> str:
    instructions = "\n\n".join(trigger_hooks)
    return f"""You are running one scheduled Lumon Auto Delivery poll.

Configured Auto Delivery instructions (legacy hook IDs are also supported):
{instructions}

This poll ID is {poll_id}. Pass `--poll-id {poll_id}` to `lumon delivery start`
so that the development receipt is linked to this check in the Dashboard.

Follow these rules:
1. Inspect the available Workspace capabilities and flows, then use the matching
   capabilities to follow the configured instructions and check for eligible events.
   These instructions are an Agent prompt, not method names to invoke directly.
   Legacy hook IDs describe events to check using Workspace capabilities.
2. If there is no eligible event, make no file, Git, Jira, or Delivery changes
   and return exactly AUTO_DELIVERY_IDLE.
3. If there is an eligible approved Story, follow the Workspace Auto Delivery
   flow. If no matching flow is installed, follow the explicit trigger prompt.
   Use `lumon delivery start` before work and exactly one terminal command
   (`complete`, `fail`, or `block`) after the outcome.
4. Record each phase using `lumon delivery progress --run-id <story-run-id>
   --phase implementation|verification|handoff --detail <short safe summary>`.
   Do not put credentials, prompts, or raw command output in progress summaries.
5. Never invent an issue, claim verification, or claim a notification was sent
   without a successful command result.
6. Keep the final response short and do not include credentials or raw command output.
"""


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
