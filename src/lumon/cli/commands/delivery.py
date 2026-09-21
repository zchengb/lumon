"""Manage Auto Delivery lifecycle receipts and notifications."""

from __future__ import annotations

import asyncio
import fcntl
import json
import os
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

import typer

from lumon.agents.agent.config import AgentConfigStore
from lumon.agents.agent.model import AgentResult
from lumon.agents.agent.runner import create_agent_runner
from lumon.agents.agent.workspace_context import WorkspaceContextBuilder
from lumon.delivery.model import DeliveryEvent, DeliveryRun
from lumon.delivery.service import DeliveryNotification, DeliveryService
from lumon.errors import AgentRuntimeError, LumonError, PreflightError
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

        with _poll_lock(state_layout.root, selected_id):
            result = asyncio.run(_run_poll(root, selected_id, settings.auto_delivery.trigger_hooks))
        safe_text = sanitize_output((result.final_text or "").strip())[:500]
        status = "idle" if "AUTO_DELIVERY_IDLE" in safe_text else "completed"
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
        _scheduled_poll_prompt(trigger_hooks),
    )
    result = await create_agent_runner(config).run(workspace, prompt)
    if result.status != "succeeded":
        diagnostic = sanitize_output(result.failure_diagnostic or "Agent poll did not complete.")
        raise AgentRuntimeError(diagnostic)
    return result


def _scheduled_poll_prompt(trigger_hooks: tuple[str, ...]) -> str:
    hooks = "\n".join(f"- {hook}" for hook in trigger_hooks)
    return f"""You are running one scheduled Lumon Auto Delivery poll.

Configured trigger hooks:
{hooks}

Follow these rules:
1. Inspect the available Workspace capabilities and flows, then use the matching
   capability to check whether any configured hook has an eligible event.
2. If there is no eligible event, make no file, Git, Jira, or Delivery changes
   and return exactly AUTO_DELIVERY_IDLE.
3. If there is an eligible approved Story, follow the Workspace Auto Delivery
   flow. Use `lumon delivery start` before work and exactly one terminal command
   (`complete`, `fail`, or `block`) after the outcome.
4. Never invent an issue, claim verification, or claim a notification was sent
   without a successful command result.
5. Keep the final response short and do not include credentials or raw command output.
"""


@contextmanager
def _poll_lock(state_root: Path, workspace_id: UUID) -> Generator[None, None, None]:
    lock_directory = state_root / "locks"
    lock_directory.mkdir(parents=True, exist_ok=True)
    lock_directory.chmod(0o700)
    lock_path = lock_directory / f"delivery-{workspace_id}.lock"
    stream = lock_path.open("a+")
    try:
        os.fchmod(stream.fileno(), 0o600)
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise PreflightError("Another Auto Delivery poll is already running.") from exc
        yield
    finally:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        finally:
            stream.close()


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
