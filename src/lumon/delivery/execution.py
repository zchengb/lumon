"""Shared scheduled and resumed Auto Delivery execution."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from lumon.agents.agent.config import AgentConfig, AgentConfigStore
from lumon.agents.agent.model import AgentErrorCode, AgentEvent, AgentProgress, AgentResult
from lumon.agents.agent.prompt import render_automation_prompt
from lumon.agents.agent.runner import AgentRunner, create_agent_runner
from lumon.agents.agent.workspace_context import WorkspaceContextBuilder
from lumon.delivery.control import acknowledge_stop, prepare_resume, require_owned, save_checkpoint
from lumon.delivery.model import (
    DeliveryActivity,
    DeliveryPoll,
    DeliveryPollState,
    DeliveryRun,
    DeliveryState,
)
from lumon.delivery.scheduler import delivery_lock
from lumon.delivery.service import DeliveryService
from lumon.delivery.store import DeliveryRunStore
from lumon.errors import AgentRuntimeError, LumonError, PreflightError
from lumon.observability import redact_text
from lumon.tools.jira_delivery import JiraDeliveryCandidate, JiraDeliveryTrigger
from lumon.workspace.registry import UserStateLayout, WorkspaceRegistry
from lumon.workspace.settings import AutoDeliverySettings, WorkspaceSettingsStore

logger = logging.getLogger(__name__)
_DETECTION_TIMEOUT_SECONDS = 30


async def run_poll(
    workspace: Path,
    workspace_id: UUID,
    settings: AutoDeliverySettings,
    *,
    state_root: Path | None = None,
    runner_factory: Callable[[AgentConfig], AgentRunner] = create_agent_runner,
    resume_run: DeliveryRun | None = None,
    on_started: Callable[[], None] | None = None,
) -> AgentResult:
    state_layout = UserStateLayout.from_root(state_root)
    service = DeliveryService(settings_store=WorkspaceSettingsStore(state_layout.root))
    service.recover_interrupted_polls(workspace, workspace_id)
    poll = DeliveryPoll(uuid4().hex, workspace_id, DeliveryPollState.RUNNING, datetime.now(UTC))
    service.run_store.save_poll(workspace, poll)
    try:
        if resume_run is not None:
            resume_run = prepare_resume(
                service.run_store,
                workspace,
                workspace_id,
                resume_run.run_id,
                attempt=resume_run.attempt,
                poll=poll,
            )
        service.run_store.set_control(workspace, poll.run_id, stopping=False)
        if on_started is not None:
            on_started()
        result = await _interruptible_poll(
            workspace,
            workspace_id,
            settings,
            poll,
            service,
            state_root=state_layout.root,
            runner_factory=runner_factory,
            resume_run=resume_run,
        )
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
                detail=(
                    "No new eligible Story." if idle else redact_text(result.final_text or "")[:500]
                ),
            ),
        )
        return result
    except (KeyboardInterrupt, asyncio.CancelledError):
        acknowledge_stop(service.run_store, workspace, poll, datetime.now(UTC))
        raise
    except Exception as exc:
        detail = redact_text(str(exc))[:500] or "Unexpected Auto Delivery failure."
        _fail_poll(workspace, poll, service, detail)
        if isinstance(exc, LumonError):
            raise
        raise AgentRuntimeError(detail) from exc
    finally:
        for run in service.run_store.list(workspace):
            if run.poll_id == poll.run_id:
                try:
                    save_checkpoint(service.run_store, workspace, run.run_id)
                except PreflightError:
                    service.run_store.save(
                        workspace, replace(run, worktree_snapshot=None, verification_summary=None)
                    )
                    service.run_store.record_activity(
                        workspace,
                        run.run_id,
                        DeliveryActivity(
                            datetime.now(UTC),
                            run.phase,
                            "Worktree fingerprint unavailable; continuation must revalidate "
                            "source and evidence.",
                        ),
                    )


async def resume_delivery(
    workspace: Path,
    workspace_id: UUID,
    run_id: str,
    *,
    attempt: int,
    state_root: Path | None = None,
    on_started: Callable[[], None] | None = None,
    runner_factory: Callable[[AgentConfig], AgentRunner] = create_agent_runner,
) -> AgentResult:
    root = UserStateLayout.from_root(state_root).root
    with delivery_lock(root, workspace_id):
        settings = WorkspaceSettingsStore(root).load(workspace_id).auto_delivery
        if not settings.enabled:
            raise PreflightError("Enable Auto Delivery before resuming a Delivery.")
        run = DeliveryRunStore().load(workspace, run_id)
        require_owned(run, workspace_id, attempt)
        if run.state not in {DeliveryState.FAILED, DeliveryState.BLOCKED, DeliveryState.STOPPED}:
            raise PreflightError("Only a failed, blocked or stopped Delivery can be resumed.")
        return await run_poll(
            workspace,
            workspace_id,
            settings,
            state_root=root,
            runner_factory=runner_factory,
            resume_run=run,
            on_started=on_started,
        )


async def _interruptible_poll(
    workspace: Path,
    workspace_id: UUID,
    settings: AutoDeliverySettings,
    poll: DeliveryPoll,
    service: DeliveryService,
    *,
    state_root: Path,
    runner_factory: Callable[[AgentConfig], AgentRunner],
    resume_run: DeliveryRun | None,
) -> AgentResult:
    task = asyncio.create_task(
        _execute_poll(
            workspace,
            workspace_id,
            settings,
            poll,
            service,
            state_root=state_root,
            runner_factory=runner_factory,
            resume_run=resume_run,
        )
    )
    interrupted = False
    try:
        while not task.done():
            await asyncio.wait({task}, timeout=0.2)
            if service.run_store.stop_requested(workspace, poll.run_id):
                # A terminal receipt wins a stop/completion race; never overwrite it.
                claimed = [
                    run for run in service.run_store.list(workspace) if run.poll_id == poll.run_id
                ]
                if any(run.state == DeliveryState.COMPLETED for run in claimed):
                    continue
                raise asyncio.CancelledError("Delivery stopped by user.")
        return await task
    except asyncio.CancelledError:
        interrupted = True
        raise
    finally:
        if not task.done():
            task.cancel()
        outcome = (await asyncio.gather(task, return_exceptions=True))[0]
        if interrupted and isinstance(outcome, Exception):
            raise AgentRuntimeError(
                "Agent execution or cleanup failed; inspect the preserved checkpoint."
            ) from outcome


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
    settings: AutoDeliverySettings,
    poll: DeliveryPoll,
    service: DeliveryService,
    *,
    state_root: Path,
    runner_factory: Callable[[AgentConfig], AgentRunner],
    resume_run: DeliveryRun | None = None,
) -> AgentResult:
    try:
        async with asyncio.timeout(_DETECTION_TIMEOUT_SECONDS):
            candidate, resume_run = await _select_delivery(
                workspace, workspace_id, settings, poll, service, resume_run
            )
    except TimeoutError as exc:
        raise PreflightError(
            "Jira detection exceeded its time budget; Codex was not started."
        ) from exc
    detection_detail = (
        f"Jira matched {candidate.key}; starting Agent for this Story only."
        if candidate
        else "No new eligible Story; Codex was not started."
    )
    service.run_store.record_activity(
        workspace, poll.run_id, DeliveryActivity(datetime.now(UTC), "discover", detection_detail)
    )
    if candidate is None:
        return AgentResult(status="succeeded", final_text="AUTO_DELIVERY_IDLE")

    state_layout = UserStateLayout.from_root(state_root)
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
        _scheduled_poll_prompt(settings, poll.run_id, candidate) + _resume_prompt(resume_run),
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
        if event.kind == "session":
            if event.agent_session_id:
                # Persist immediately, including sessions started before the Story is claimed.
                service.run_store.save_session(workspace, poll.run_id, event.agent_session_id)
                for run in service.run_store.list(workspace):
                    if run.poll_id == poll.run_id:
                        service.run_store.save(
                            workspace, replace(run, agent_session_id=event.agent_session_id)
                        )
            return
        if event.kind == "progress":
            return  # Only the validated, bounded progress callback records Agent text.
        detail = f"{event.kind.replace('_', ' ')}: {event.lifecycle}"
        if event.exit_code is not None:
            detail += f" (exit {event.exit_code})"
        current = service.run_store.load_poll(workspace, poll.run_id)
        service.run_store.record_activity(
            workspace,
            poll.run_id,
            DeliveryActivity(
                datetime.now(UTC),
                current.phase,
                detail,
                command=redact_text(event.command, secrets) if event.command else None,
                operation_id=redact_text(event.operation_id, secrets)
                if event.operation_id
                else None,
                exit_code=event.exit_code,
            ),
        )

    runner = runner_factory(config)
    if resume_run is not None and resume_run.agent_session_id:
        result = await runner.run(
            workspace,
            prompt,
            agent_session_id=resume_run.agent_session_id,
            on_progress=observe_progress,
            on_event=observe_event,
        )
        if result.error_code == AgentErrorCode.SESSION_UNAVAILABLE:
            current = service.run_store.load(workspace, resume_run.run_id)
            service.run_store.save(workspace, replace(current, agent_session_id=None))
            service.run_store.record_activity(
                workspace,
                current.run_id,
                DeliveryActivity(
                    datetime.now(UTC),
                    current.phase,
                    "Saved Agent session unavailable; continuing in a new session "
                    "from the checkpoint.",
                ),
            )
            result = await runner.run(
                workspace, prompt, on_progress=observe_progress, on_event=observe_event
            )
    else:
        result = await runner.run(
            workspace, prompt, on_progress=observe_progress, on_event=observe_event
        )
    if result.agent_session_id:
        for run in service.run_store.list(workspace):
            if run.poll_id == poll.run_id:
                service.run_store.save(
                    workspace, replace(run, agent_session_id=result.agent_session_id)
                )
    if result.status != "succeeded":
        diagnostic = redact_text(
            result.failure_diagnostic or "Agent poll did not complete.", secrets
        )
        raise AgentRuntimeError(diagnostic)
    if any(
        run.story_key != candidate.key
        for run in service.run_store.list(workspace)
        if run.poll_id == poll.run_id
    ):
        raise AgentRuntimeError("Agent claimed a Story other than the selected Jira candidate.")
    return replace(result, final_text=redact_text(result.final_text or "", secrets))


async def _select_delivery(
    workspace: Path,
    workspace_id: UUID,
    settings: AutoDeliverySettings,
    poll: DeliveryPoll,
    service: DeliveryService,
    resume_run: DeliveryRun | None,
) -> tuple[JiraDeliveryCandidate | None, DeliveryRun | None]:
    excluded_keys = frozenset(
        run.story_key.upper()
        for run in service.run_store.list(workspace)
        if run.workspace_id in (None, workspace_id)
    )
    candidate = (
        JiraDeliveryCandidate(
            resume_run.story_key, resume_run.story_title, resume_run.jira_url or ""
        )
        if resume_run
        else await JiraDeliveryTrigger().find_candidate(
            settings.jira_site, settings.trigger_jql, excluded_keys=excluded_keys
        )
    )
    if candidate is None:
        for previous in service.run_store.list(workspace):
            if previous.workspace_id not in {None, workspace_id} or previous.finished_at is None:
                continue
            if previous.state not in {
                DeliveryState.FAILED,
                DeliveryState.BLOCKED,
                DeliveryState.STOPPED,
            }:
                continue
            candidate = await JiraDeliveryTrigger().reentered(
                settings.jira_site,
                settings.trigger_jql,
                previous.story_key,
                finished_at=previous.finished_at,
                consumed_event_id=previous.jira_reentry_id,
            )
            if candidate is not None:
                if service.settings_store.load(workspace_id).auto_delivery != settings:
                    raise PreflightError("Auto Delivery settings changed; no resume was started.")
                resume_run = prepare_resume(
                    service.run_store,
                    workspace,
                    workspace_id,
                    previous.run_id,
                    attempt=previous.attempt,
                    poll=poll,
                    reentry_id=candidate.reentry_id,
                )
                break
    if (
        candidate is not None
        and service.settings_store.load(workspace_id).auto_delivery != settings
    ):
        raise PreflightError(
            "Auto Delivery settings changed during detection; Codex was not started."
        )
    return candidate, resume_run


def _resume_prompt(run: DeliveryRun | None) -> str:
    if run is None:
        return ""
    return "\n\n" + render_automation_prompt(
        "auto_delivery_resume.md",
        checkpoint=json.dumps(
            {
                "run_id": run.run_id,
                "attempt": run.attempt,
                "poll_id": run.poll_id,
                "phase": run.phase,
                "checkpoint": run.checkpoint,
                "current_worktrees": run.worktree_snapshot,
                "result_comment_id": run.result_comment_id,
                "previous_attempt_receipt": (
                    f"lumon/runs/{run.run_id}/attempt-{run.attempt - 1}.json"
                ),
            }
        ),
    )


class DeliveryTasks:
    """Keep Dashboard-owned continuations alive and cancel them on server shutdown."""

    def __init__(
        self,
        state_root: Path,
        runner_factory: Callable[[AgentConfig], AgentRunner] = create_agent_runner,
    ) -> None:
        self.state_root = state_root
        self.runner_factory = runner_factory
        self.tasks: set[asyncio.Task[None]] = set()

    async def launch(
        self, workspace: Path, workspace_id: UUID, run_id: str, *, attempt: int
    ) -> None:
        ready = asyncio.get_running_loop().create_future()

        def started() -> None:
            if not ready.done():
                ready.set_result(None)

        async def execute() -> None:
            try:
                await resume_delivery(
                    workspace,
                    workspace_id,
                    run_id,
                    attempt=attempt,
                    state_root=self.state_root,
                    runner_factory=self.runner_factory,
                    on_started=started,
                )
            except asyncio.CancelledError:
                if not ready.done():
                    ready.cancel()
            except Exception as exc:
                # The execution boundary already saved the failure; preflight errors go to HTTP.
                if not ready.done():
                    ready.set_exception(exc)
                else:
                    logger.warning("Delivery continuation failed (%s).", type(exc).__name__)

        task = asyncio.create_task(execute())
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        await asyncio.shield(ready)

    async def close(self) -> None:
        tasks = tuple(self.tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def _scheduled_poll_prompt(
    settings: AutoDeliverySettings, poll_id: str, candidate: JiraDeliveryCandidate
) -> str:
    return render_automation_prompt(
        "auto_delivery.md",
        instructions="\n\n".join(settings.trigger_hooks),
        poll_id=poll_id,
        candidate=json.dumps(
            {"key": candidate.key, "title": candidate.title, "url": candidate.url}
        ),
        jira_site=settings.jira_site,
        trigger_jql=json.dumps(settings.trigger_jql),
        publish_mode=settings.publish_mode,
        target_branch=json.dumps(settings.target_branch)
        if settings.target_branch
        else "each Repository's registered branch",
    )
