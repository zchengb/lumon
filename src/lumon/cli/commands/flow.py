"""Run scheduled Workspace Flows by their explicit Flow ID."""

from __future__ import annotations

import asyncio
import fcntl
import json
import os
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Annotated
from uuid import UUID

import typer

from lumon.agents.agent.config import AgentConfigStore
from lumon.agents.agent.model import AgentResult
from lumon.agents.agent.runner import create_agent_runner
from lumon.agents.agent.workspace_context import WorkspaceContextBuilder
from lumon.errors import AgentRuntimeError, LumonError, PreflightError
from lumon.flows.catalog import FlowCatalog, FlowValidationError
from lumon.flows.model import FlowDefinition
from lumon.flows.scheduler import LaunchdFlowScheduler
from lumon.tools.safety import sanitize_output
from lumon.workspace.layout import WorkspaceLayout
from lumon.workspace.manifest import load_manifest
from lumon.workspace.registry import UserStateLayout, WorkspaceRegistry
from lumon.workspace.settings import FlowScheduleSettings, WorkspaceSettings, WorkspaceSettingsStore

flow_app = typer.Typer(
    name="flow",
    help="Run a specific scheduled Workspace Flow.",
    no_args_is_help=True,
    add_completion=False,
)


@flow_app.command("poll")
def poll(
    flow_id: Annotated[str, typer.Option("--flow-id", help="Exact Workspace Flow ID.")],
    workspace: Annotated[Path, typer.Option("--workspace", dir_okay=True)] = Path("."),
    workspace_id: Annotated[str | None, typer.Option("--workspace-id")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Run one scheduled Flow only when its Workspace schedule is enabled."""

    try:
        root, manifest_id = _workspace_identity(workspace)
        selected_id = _parse_workspace_id(workspace_id) if workspace_id else manifest_id
        if selected_id != manifest_id:
            raise PreflightError("The requested Workspace ID does not match its manifest.")

        settings = WorkspaceSettingsStore().load(selected_id)
        schedule = next(
            (item for item in settings.flow_schedules if item.flow_id == flow_id),
            None,
        )
        if schedule is None or not schedule.enabled:
            _emit({"status": "disabled", "flow_id": flow_id}, json_output)
            return

        try:
            definition = FlowCatalog(root).read(flow_id)
        except FlowValidationError:
            _remove_stale_schedule(root, selected_id, flow_id, settings)
            _emit({"status": "flow_unavailable", "flow_id": flow_id}, json_output)
            return
        if not definition.enabled:
            _disable_schedule(root, selected_id, schedule)
            _emit({"status": "flow_disabled", "flow_id": flow_id}, json_output)
            return

        state_layout = UserStateLayout.from_root()
        with _poll_lock(state_layout.root, selected_id, flow_id):
            result = asyncio.run(_run_flow(root, selected_id, definition))
        detail = sanitize_output((result.final_text or "").strip())[:4_000]
        _emit(
            {
                "status": "completed",
                "flow_id": flow_id,
                "workspace_id": str(selected_id),
                "detail": detail,
            },
            json_output,
        )
    except LumonError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from exc


async def _run_flow(workspace: Path, workspace_id: UUID, flow: FlowDefinition) -> AgentResult:
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
        f"Run the scheduled Workspace Flow '{flow.flow_id}' now.",
        scheduled_flow=flow,
    )
    result = await create_agent_runner(config).run(workspace, prompt)
    if result.status != "succeeded":
        diagnostic = sanitize_output(
            result.failure_diagnostic or "Scheduled Flow did not complete."
        )
        raise AgentRuntimeError(diagnostic)
    return result


def _workspace_identity(workspace: Path) -> tuple[Path, UUID]:
    root = workspace.expanduser().resolve()
    manifest = load_manifest(WorkspaceLayout.from_root(root).manifest)
    return root, manifest.workspace_id


def _parse_workspace_id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise PreflightError("Workspace ID must be a valid UUID.") from exc


def _emit(payload: dict[str, object], json_output: bool) -> None:
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    typer.echo(f"Flow poll: {payload['status']}")


def _disable_schedule(
    workspace: Path,
    workspace_id: UUID,
    schedule: FlowScheduleSettings,
) -> None:
    disabled = FlowScheduleSettings(
        schedule.flow_id,
        enabled=False,
        schedule_expression=schedule.schedule_expression,
    )
    LaunchdFlowScheduler().apply(workspace, workspace_id, disabled)
    settings_store = WorkspaceSettingsStore()
    settings = settings_store.load(workspace_id)
    settings_store.save(
        replace(
            settings,
            flow_schedules=tuple(
                disabled if item.flow_id == schedule.flow_id else item
                for item in settings.flow_schedules
            ),
        )
    )


def _remove_stale_schedule(
    workspace: Path,
    workspace_id: UUID,
    flow_id: str,
    settings: WorkspaceSettings,
) -> None:
    schedule = next((item for item in settings.flow_schedules if item.flow_id == flow_id), None)
    LaunchdFlowScheduler().apply(
        workspace,
        workspace_id,
        FlowScheduleSettings(flow_id, enabled=False),
    )
    if schedule is None:
        return
    settings_store = WorkspaceSettingsStore()
    current = settings_store.load(workspace_id)
    settings_store.save(
        replace(
            current,
            flow_schedules=tuple(
                item for item in current.flow_schedules if item.flow_id != flow_id
            ),
        )
    )


@contextmanager
def _poll_lock(state_root: Path, workspace_id: UUID, flow_id: str) -> Generator[None, None, None]:
    lock_directory = state_root / "locks"
    lock_path = lock_directory / f"flow-{workspace_id}-{flow_id}.lock"
    try:
        lock_directory.mkdir(parents=True, exist_ok=True)
        lock_directory.chmod(0o700)
        stream = lock_path.open("a+")
        os.fchmod(stream.fileno(), 0o600)
    except OSError as exc:
        raise PreflightError("Unable to prepare the scheduled Flow lock.") from exc
    try:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        stream.close()
        raise PreflightError("This Flow already has a scheduled run in progress.") from exc
    except OSError as exc:
        stream.close()
        raise PreflightError("Unable to acquire the scheduled Flow lock.") from exc
    try:
        yield
    finally:
        stream.close()
