"""Orchestrate Feishu messages, Workspace context, Agent execution, and persistence."""

from __future__ import annotations

import asyncio
import logging
import time
import traceback
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from lumon.agents.agent.config import AgentConfig, AgentConfigStore
from lumon.agents.agent.feishu import AgentFeishuChannel
from lumon.agents.agent.model import (
    AgentErrorCode,
    AgentProgress,
    AgentRunResult,
    AgentRunStatus,
    InboundMessage,
    Message,
    ProgressPhase,
    RecalledMessage,
    WorkspaceContext,
)
from lumon.agents.agent.runner import AgentRunner, create_agent_runner
from lumon.agents.agent.session_store import AgentSessionStore
from lumon.agents.agent.soul import SoulLoader
from lumon.agents.agent.workspace_context import WorkspaceContextBuilder
from lumon.errors import AgentConfigError, AgentRuntimeError, LumonError
from lumon.flows.catalog import FlowCatalog
from lumon.flows.protocol import extract_flow_selection
from lumon.observability import (
    AgentTelemetry,
    AgentTrace,
    NoopAgentTelemetry,
    TelemetryStatus,
    create_agent_telemetry,
)
from lumon.tools.safety import sanitize_output
from lumon.workspace.registry import WorkspaceRegistry

logger = logging.getLogger(__name__)


class AgentService:
    """Coordinate the Agent message lifecycle with per-conversation ordering."""

    def __init__(
        self,
        config_store: AgentConfigStore | None = None,
        registry: WorkspaceRegistry | None = None,
        session_store: AgentSessionStore | None = None,
        soul_loader: SoulLoader | None = None,
        agent_runner: AgentRunner | None = None,
        channel: AgentFeishuChannel | None = None,
        now: Callable[[], datetime] | None = None,
        telemetry: AgentTelemetry | None = None,
    ) -> None:
        self.config_store = config_store or AgentConfigStore()
        self.registry = registry or WorkspaceRegistry()
        self.session_store = session_store or AgentSessionStore()
        self.soul_loader = soul_loader or SoulLoader()
        self.agent_runner = agent_runner
        self._channel = channel
        self._now = now or (lambda: datetime.now(UTC))
        self._telemetry = telemetry
        self._telemetry_shutdown = False
        self._config: AgentConfig | None = None
        self._context_builder: WorkspaceContextBuilder | None = None
        self._conversation_locks: dict[str, asyncio.Lock] = {}
        self._tasks: set[asyncio.Task[None]] = set()
        self._tasks_by_event: dict[str, asyncio.Task[None]] = {}
        self._stop_event: asyncio.Event | None = None

    async def run_forever(self) -> None:
        """Start the Feishu WebSocket lifecycle and recover pending messages."""

        try:
            self._ensure_runtime()
            assert self._channel is not None
            if self._context_builder is None:
                raise AgentRuntimeError("Agent Workspace context is not ready.")
            self._context_builder.resolve_workspace()
            self._stop_event = asyncio.Event()
            for message in self.session_store.recover_pending():
                if message.admitted:
                    session = self.session_store.get_or_create_session(message)
                    self._schedule(message, session.session_id)
            await self._channel.connect(self.handle_message, self.handle_recalled)
        except asyncio.CancelledError:
            raise
        finally:
            await self._shutdown_tasks()
            try:
                if self._channel is not None:
                    await self._channel.disconnect()
            finally:
                self._shutdown_telemetry()

    async def stop(self) -> None:
        """Request a graceful stop for the channel and in-flight message tasks."""

        if self._stop_event is not None:
            self._stop_event.set()
        await self._shutdown_tasks()
        try:
            if self._channel is not None:
                await self._channel.disconnect()
        finally:
            self._shutdown_telemetry()

    async def handle_message(self, message: InboundMessage) -> None:
        """Admit one normalized message and enqueue it without duplicate work."""

        if not message.admitted:
            return
        self._ensure_runtime()
        session_id = self.session_store.get_or_create_session(message).session_id
        if not self.session_store.claim_event(message.event_id, message):
            return
        self._schedule(message, session_id)

    async def handle_recalled(self, message: RecalledMessage) -> None:
        """Cancel the active Agent request associated with a recalled message."""

        event_id = self.session_store.request_message_cancellation(message.message_id)
        if event_id is None:
            return
        task = self._tasks_by_event.get(event_id)
        if task is None or task.done():
            self.session_store.mark_event_cancelled(event_id)
            return
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def wait_for_idle(self) -> None:
        """Wait for currently scheduled messages; useful for integration tests."""

        while self._tasks:
            await asyncio.gather(*tuple(self._tasks), return_exceptions=True)

    def _ensure_runtime(self) -> None:
        if self._config is not None:
            return
        config = self.config_store.load()
        if not config.enabled:
            raise AgentConfigError("Agent is disabled. Enable it with `lumon agent configure`.")
        self._config = config
        self._context_builder = WorkspaceContextBuilder(
            config=config,
            registry=self.registry,
            soul_loader=self.soul_loader,
        )
        if self._telemetry is None:
            try:
                self._telemetry = create_agent_telemetry(config)
            except Exception as exc:
                logger.warning("Agent telemetry setup failed (%s).", type(exc).__name__)
                self._telemetry = NoopAgentTelemetry()
        if self.agent_runner is None:
            self.agent_runner = create_agent_runner(config)
        if self._channel is None:
            self._channel = AgentFeishuChannel(config)

    def _schedule(self, message: InboundMessage, session_id: str) -> None:
        task = asyncio.create_task(self._process(message, session_id))
        self._tasks.add(task)
        self._tasks_by_event[message.event_id] = task
        task.add_done_callback(self._task_finished)

    async def _process(self, message: InboundMessage, session_id: str) -> None:
        """Run one task and finalize queued cancellation that races its lock."""

        try:
            await self._process_locked(message, session_id)
        except asyncio.CancelledError:
            if self.session_store.is_cancellation_requested(message.event_id):
                self.session_store.mark_event_cancelled(message.event_id)
            raise

    async def _process_locked(self, message: InboundMessage, session_id: str) -> None:
        lock = self._conversation_locks.setdefault(message.conversation_key, asyncio.Lock())
        async with lock:
            if self.session_store.is_cancellation_requested(message.event_id):
                self.session_store.mark_event_cancelled(message.event_id)
                return
            self.session_store.mark_event_status(message.event_id, "processing")
            self.session_store.bind_event_session(message.event_id, session_id)
            session = self.session_store.get_session(session_id)
            if session is None:
                raise AgentRuntimeError("Agent conversation session is not available.")
            config = self._config
            if config is None:
                raise AgentRuntimeError("Agent configuration is not loaded.")
            started_at = _timestamp(self._now())
            run_id = str(uuid4())
            workspace_id: UUID | None = None
            final_text: str | None = None
            status: AgentRunStatus = "failed"
            error_code: str | None = None
            agent_provider: str | None = None
            prompt: str | None = None
            failure_diagnostic: str | None = None
            run_started = False
            completed = False
            typing_reaction_id: str | None = None
            trace_status: TelemetryStatus = "failed"
            trace_error_code: str | None = None
            reply_failed = False
            flow_id: str | None = None
            stage = "add_typing_reaction"
            trace = self._start_trace(
                run_id=run_id,
                session_id=session_id,
                event_id=message.event_id,
                sender_id=message.sender_id,
                chat_type=message.chat_type,
                workspace_id=workspace_id,
                provider=(
                    self.agent_runner.provider
                    if self.agent_runner is not None
                    else config.agent_provider
                ),
                model=config.agent_model,
                reasoning_effort=config.agent_reasoning_effort,
                input_text=message.text,
            )
            try:
                typing_reaction_id = await self._add_typing_reaction(message)
                stage = "record_inbound_message"
                self.session_store.record_message(
                    Message(
                        conversation_key=message.conversation_key,
                        direction="inbound",
                        message_id=message.message_id,
                        text=message.text,
                        created_at=started_at,
                        session_id=session_id,
                    )
                )
                context_builder = self._context_builder
                if context_builder is None or self._channel is None:
                    raise AgentRuntimeError("Agent runtime is not ready.")
                stage = "resolve_workspace"
                async with trace.span("workspace.resolve") as workspace_span:
                    context = context_builder.resolve_workspace()
                    workspace_span.update(metadata={"workspace_id": str(context.workspace_id)})
                workspace_id = context.workspace_id
                stage = "attach_workspace"
                self.session_store.attach_workspace(message.event_id, workspace_id)
                trace.update(metadata={"workspace_id": str(workspace_id)})
                self._raise_if_cancellation_requested(message.event_id)
                resume_session_id = session.agent_session_id
                if (
                    resume_session_id is not None
                    and session.workspace_id is not None
                    and session.workspace_id != workspace_id
                ):
                    stage = "clear_mismatched_agent_session"
                    self.session_store.clear_agent_session(session_id)
                    resume_session_id = None
                if resume_session_id is None:
                    stage = "load_history"
                    async with trace.span("history.load") as history_span:
                        history = self.session_store.load_history(
                            session_id,
                            conversation_key=message.conversation_key,
                            legacy_conversation_key=message.legacy_conversation_key,
                        )
                        history_span.update(metadata={"message_count": len(history)})
                    stage = "build_prompt"
                    async with trace.span("prompt.build") as prompt_span:
                        prompt = context_builder.build_prompt(context, history, message.text)
                        prompt_span.update(metadata={"prompt_length": len(prompt)})
                else:
                    prompt = context_builder.build_resume_prompt(context, message.text)
                trace.update(
                    input_text=prompt,
                    metadata={"resumed_agent_session": resume_session_id is not None},
                )
                runner = self.agent_runner
                if runner is None:
                    raise AgentRuntimeError("Agent runtime is not ready.")
                agent_provider = runner.provider
                stage = "record_run_started"
                self.session_store.record_run_started(
                    run_id=run_id,
                    event_id=message.event_id,
                    session_id=session_id,
                    conversation_key=message.conversation_key,
                    workspace_id=workspace_id,
                    agent_provider=agent_provider,
                    prompt_text=prompt,
                    started_at=started_at,
                )
                run_started = True
                reporter = _ProgressReporter(self._channel, message)
                stage = "run_agent"
                async with trace.span(
                    "codex.exec",
                    as_type="tool",
                    metadata={
                        "provider": runner.provider,
                        "model": config.agent_model,
                        "reasoning_effort": config.agent_reasoning_effort,
                        "resumed_agent_session": resume_session_id is not None,
                    },
                ) as codex_span:
                    result = await runner.run(
                        context.path,
                        prompt,
                        agent_session_id=resume_session_id,
                        on_progress=reporter.notify,
                    )
                    marker_flow_id, _marker_status, cleaned_result_text = extract_flow_selection(
                        result.final_text
                    )
                    if result.final_text is not None:
                        result = replace(
                            result,
                            final_text=cleaned_result_text,
                            flow_id=result.flow_id or marker_flow_id,
                        )
                    flow_id = _validated_flow_id(result.flow_id, context)
                    if flow_id is not None:
                        trace.update(metadata={"flow_id": flow_id})
                    result_metadata: dict[str, str | int | bool] = {
                        "status": result.status,
                        "progress_count": len(result.progress),
                        "return_code": (
                            result.return_code if result.return_code is not None else "none"
                        ),
                        "agent_session_available": result.agent_session_id is not None,
                    }
                    if result.error_code is not None:
                        result_metadata["error_code"] = result.error_code.value
                    codex_span.update(
                        metadata=result_metadata,
                        level=("ERROR" if result.status in {"failed", "timed_out"} else "DEFAULT"),
                        status_message=(
                            result.error_code.value if result.error_code is not None else None
                        ),
                    )
                self._raise_if_cancellation_requested(message.event_id)
                if resume_session_id is not None and result.status == "failed":
                    stage = "clear_failed_agent_session"
                    self.session_store.clear_agent_session(session_id)
                elif result.agent_session_id is not None:
                    stage = "bind_agent_session"
                    self.session_store.bind_agent_session(
                        session_id,
                        result.agent_session_id,
                    )
                status = result.status
                error_code = result.error_code.value if result.error_code is not None else None
                if result.status == "succeeded" and result.final_text:
                    stage = "sanitize_final_text"
                    final_text = sanitize_output(result.final_text)
                    stage = "send_final_reply"
                    async with trace.span(
                        "feishu.reply",
                        metadata={"reply_type": "final"},
                    ) as reply_span:
                        delivered = await self._send(message, final_text)
                        reply_metadata = _reply_metadata(delivered)
                        reply_span.update(metadata=reply_metadata)
                        trace.update(metadata=reply_metadata)
                        if not delivered:
                            reply_failed = True
                            trace_error_code = "feishu_reply_failed"
                    stage = "record_outbound_message"
                    self.session_store.record_message(
                        Message(
                            conversation_key=message.conversation_key,
                            direction="outbound",
                            message_id=None,
                            workspace_id=workspace_id,
                            text=final_text,
                            created_at=_timestamp(self._now()),
                            session_id=session_id,
                        )
                    )
                else:
                    if status == "succeeded":
                        status = "failed"
                        error_code = error_code or AgentErrorCode.EMPTY_RESULT.value
                    stage = "send_failure_reply"
                    async with trace.span(
                        "feishu.reply",
                        metadata={"reply_type": "failure"},
                    ) as reply_span:
                        delivered = await self._send(
                            message,
                            _failure_message(
                                error_code,
                                status=status,
                                agent_name=runner.display_name,
                            ),
                        )
                        reply_metadata = _reply_metadata(delivered)
                        reply_span.update(metadata=reply_metadata)
                        trace.update(metadata=reply_metadata)
                        if not delivered:
                            reply_failed = True
                            trace_error_code = "feishu_reply_failed"
                trace_status = "failed" if reply_failed else status
                completed = True
            except asyncio.CancelledError:
                if self.session_store.is_cancellation_requested(message.event_id):
                    trace_status = "cancelled"
                    error_code = "message_recalled"
                    if run_started:
                        self.session_store.mark_run_cancelled(
                            run_id,
                            _timestamp(self._now()),
                        )
                    self.session_store.mark_event_cancelled(message.event_id)
                elif run_started:
                    trace_status = "interrupted"
                    error_code = "interrupted"
                    self.session_store.mark_run_interrupted(
                        run_id,
                        _timestamp(self._now()),
                    )
                    # Leave the event in ``processing`` so the next service
                    # start can move it back to ``queued`` and recover it.
                raise
            except LumonError as exc:
                trace_status = "failed"
                error_code = _error_code(exc)
                failure_diagnostic = _safe_error_diagnostic(stage, exc)
                agent_name = self.agent_runner.display_name if self.agent_runner else "Agent CLI"
                async with trace.span(
                    "feishu.reply",
                    metadata={"reply_type": "failure"},
                ) as reply_span:
                    delivered = await self._send(
                        message,
                        _failure_message(error_code, agent_name=agent_name),
                    )
                    reply_metadata = _reply_metadata(delivered)
                    reply_span.update(metadata=reply_metadata)
                    trace.update(metadata=reply_metadata)
                    if not delivered:
                        reply_failed = True
                        trace_error_code = "feishu_reply_failed"
                completed = True
            except Exception as exc:
                trace_status = "failed"
                error_code = "agent_unexpected_error"
                failure_diagnostic = _safe_error_diagnostic(stage, exc)
                agent_name = self.agent_runner.display_name if self.agent_runner else "Agent CLI"
                async with trace.span(
                    "feishu.reply",
                    metadata={"reply_type": "failure"},
                ) as reply_span:
                    delivered = await self._send(
                        message,
                        _failure_message(error_code, agent_name=agent_name),
                    )
                    reply_metadata = _reply_metadata(delivered)
                    reply_span.update(metadata=reply_metadata)
                    trace.update(metadata=reply_metadata)
                    if not delivered:
                        reply_failed = True
                        trace_error_code = "feishu_reply_failed"
                completed = True
            finally:
                try:
                    await self._remove_typing_reaction(message, typing_reaction_id)
                    if completed:
                        ended_at = _timestamp(self._now())
                        self.session_store.record_result(
                            AgentRunResult(
                                run_id=run_id,
                                event_id=message.event_id,
                                conversation_key=message.conversation_key,
                                workspace_id=workspace_id,
                                status=status,
                                started_at=started_at,
                                ended_at=ended_at,
                                final_text=final_text,
                                agent_provider=agent_provider,
                                error_code=error_code,
                                session_id=session_id,
                                flow_id=flow_id,
                                prompt_text=prompt if run_started else None,
                                failure_diagnostic=failure_diagnostic,
                            )
                        )
                finally:
                    trace.finish(
                        status=trace_status,
                        error_code=trace_error_code or error_code,
                        final_text=final_text,
                    )

    async def _send(self, message: InboundMessage, text: str) -> bool:
        if self._channel is None:
            return False
        try:
            await self._channel.reply(message, sanitize_output(text))
        except AgentRuntimeError:
            return False
        return True

    async def _add_typing_reaction(self, message: InboundMessage) -> str | None:
        if self._channel is None:
            return None
        try:
            return await self._channel.add_typing(message.message_id)
        except AgentRuntimeError:
            return None

    async def _remove_typing_reaction(
        self,
        message: InboundMessage,
        reaction_id: str | None,
    ) -> None:
        if self._channel is None or reaction_id is None:
            return
        try:
            await self._channel.remove_typing(message.message_id, reaction_id)
        except AgentRuntimeError:
            return

    def _raise_if_cancellation_requested(self, event_id: str) -> None:
        if self.session_store.is_cancellation_requested(event_id):
            raise asyncio.CancelledError

    async def _shutdown_tasks(self) -> None:
        tasks = tuple(self._tasks)
        if not tasks:
            return
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
        self._tasks_by_event.clear()

    def _start_trace(
        self,
        *,
        run_id: str,
        session_id: str,
        event_id: str,
        sender_id: str,
        chat_type: str,
        workspace_id: UUID | None,
        provider: str,
        model: str,
        reasoning_effort: str,
        input_text: str,
    ) -> AgentTrace:
        telemetry = self._telemetry or NoopAgentTelemetry()
        try:
            return telemetry.start_trace(
                run_id=run_id,
                session_id=session_id,
                event_id=event_id,
                sender_id=sender_id,
                chat_type=chat_type,
                workspace_id=workspace_id,
                provider=provider,
                model=model,
                reasoning_effort=reasoning_effort,
                input_text=input_text,
            )
        except Exception as exc:
            logger.warning("Agent telemetry start failed (%s).", type(exc).__name__)
            return NoopAgentTelemetry().start_trace(
                run_id=run_id,
                session_id=session_id,
                event_id=event_id,
                sender_id=sender_id,
                chat_type=chat_type,
                workspace_id=workspace_id,
                provider=provider,
                model=model,
                reasoning_effort=reasoning_effort,
                input_text=input_text,
            )

    def _shutdown_telemetry(self) -> None:
        if self._telemetry_shutdown:
            return
        self._telemetry_shutdown = True
        if self._telemetry is None:
            return
        try:
            self._telemetry.shutdown()
        except Exception as exc:
            logger.warning("Agent telemetry shutdown failed (%s).", type(exc).__name__)

    def _task_finished(self, task: asyncio.Task[None]) -> None:
        self._tasks.discard(task)
        for event_id, registered_task in tuple(self._tasks_by_event.items()):
            if registered_task is task:
                self._tasks_by_event.pop(event_id, None)
        if not task.cancelled():
            task.exception()


class _ProgressReporter:
    """Throttle runner events so a busy Agent turn does not spam Feishu."""

    def __init__(self, channel: AgentFeishuChannel, message: InboundMessage) -> None:
        self.channel = channel
        self.message = message
        self.last_sent = 0.0
        self.sent = 0
        self._sent_phases: set[ProgressPhase] = set()

    async def notify(self, progress: AgentProgress) -> None:
        if not progress.notify_requested or progress.phase in self._sent_phases:
            return
        now = time.monotonic()
        if self.sent >= 2 or (self.sent and now - self.last_sent < 3.0):
            return
        text = sanitize_output(progress.message).strip()
        if not text or len(text) > 60:
            return
        self._sent_phases.add(progress.phase)
        self.sent += 1
        self.last_sent = now
        try:
            await self.channel.reply(self.message, sanitize_output(text))
        except AgentRuntimeError:
            return


def _failure_message(
    error_code: str | None,
    *,
    status: AgentRunStatus | None = None,
    agent_name: str = "Agent CLI",
) -> str:
    if error_code == AgentErrorCode.TIMEOUT.value or status == "timed_out":
        return f"{agent_name} 处理超时了。请稍后重试，或先运行 `lumon agent doctor` 检查本机环境。"
    if error_code == AgentErrorCode.CLI_NOT_FOUND.value:
        return (
            f"找不到当前配置的 Agent CLI（{agent_name}）。"
            "请安装并登录后，再运行 `lumon agent doctor`。"
        )
    if error_code == AgentErrorCode.EMPTY_RESULT.value:
        return "Agent 没有得到可用回答。请稍后重试。"
    return "Agent 暂时无法完成这次请求。请运行 `lumon agent doctor` 检查配置和运行环境。"


def _error_code(error: LumonError) -> str:
    if isinstance(error, AgentConfigError):
        return "agent_configuration_invalid"
    if isinstance(error, AgentRuntimeError):
        return "agent_runtime_error"
    return "agent_error"


def _timestamp(now: datetime) -> str:
    return now.astimezone(UTC).isoformat()


def _safe_error_diagnostic(stage: str, error: Exception) -> str:
    """Describe an exception without retaining its message or user data."""

    frames = traceback.extract_tb(error.__traceback__)
    location = ""
    if frames:
        frame = frames[-1]
        location = f":{Path(frame.filename).name}:{frame.name}:{frame.lineno}"
    return f"{stage}:{type(error).__name__}{location}"


def _reply_metadata(delivered: bool) -> dict[str, str | bool]:
    metadata: dict[str, str | bool] = {"delivered": delivered}
    if not delivered:
        metadata["error_code"] = "feishu_reply_failed"
    return metadata


def _validated_flow_id(flow_id: str | None, context: WorkspaceContext) -> str | None:
    """Keep only a flow ID present in the current Workspace catalog."""

    if not isinstance(flow_id, str) or not flow_id.strip():
        return None
    normalized = flow_id.strip()
    available_ids = {brief.flow_id for brief in FlowCatalog(context.path).discover().briefs}
    return normalized if normalized in available_ids else None
