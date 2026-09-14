"""Orchestrate Feishu messages, Workspace context, Agent execution, and persistence."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from lumon.agents.mark.config import MarkAgentConfig, MarkConfigStore
from lumon.agents.mark.feishu import MarkFeishuChannel
from lumon.agents.mark.model import (
    AgentErrorCode,
    AgentProgress,
    InboundMessage,
    MarkRunResult,
    MarkRunStatus,
    Message,
    ProgressPhase,
    RecalledMessage,
)
from lumon.agents.mark.runner import AgentRunner, create_agent_runner
from lumon.agents.mark.session_store import MarkSessionStore
from lumon.agents.mark.soul import MarkSoulLoader
from lumon.agents.mark.workspace_context import WorkspaceContextBuilder
from lumon.errors import AgentConfigError, AgentRuntimeError, LumonError
from lumon.tools.safety import sanitize_output
from lumon.workspace.registry import WorkspaceRegistry


class MarkAgentService:
    """Coordinate the Mark message lifecycle with per-conversation ordering."""

    def __init__(
        self,
        config_store: MarkConfigStore | None = None,
        registry: WorkspaceRegistry | None = None,
        session_store: MarkSessionStore | None = None,
        soul_loader: MarkSoulLoader | None = None,
        agent_runner: AgentRunner | None = None,
        channel: MarkFeishuChannel | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.config_store = config_store or MarkConfigStore()
        self.registry = registry or WorkspaceRegistry()
        self.session_store = session_store or MarkSessionStore()
        self.soul_loader = soul_loader or MarkSoulLoader()
        self.agent_runner = agent_runner
        self._channel = channel
        self._now = now or (lambda: datetime.now(UTC))
        self._config: MarkAgentConfig | None = None
        self._context_builder: WorkspaceContextBuilder | None = None
        self._conversation_locks: dict[str, asyncio.Lock] = {}
        self._tasks: set[asyncio.Task[None]] = set()
        self._tasks_by_event: dict[str, asyncio.Task[None]] = {}
        self._stop_event: asyncio.Event | None = None

    async def run_forever(self) -> None:
        """Start the Feishu WebSocket lifecycle and recover pending messages."""

        self._ensure_runtime()
        assert self._channel is not None
        if self._context_builder is None:
            raise AgentRuntimeError("Mark Workspace context is not ready.")
        self._context_builder.resolve_workspace()
        self._stop_event = asyncio.Event()
        for message in self.session_store.recover_pending():
            if message.admitted:
                session = self.session_store.get_or_create_session(message)
                self._schedule(message, session.session_id)
        try:
            await self._channel.connect(self.handle_message, self.handle_recalled)
        except asyncio.CancelledError:
            raise
        finally:
            await self._shutdown_tasks()
            await self._channel.disconnect()

    async def stop(self) -> None:
        """Request a graceful stop for the channel and in-flight message tasks."""

        if self._stop_event is not None:
            self._stop_event.set()
        await self._shutdown_tasks()
        if self._channel is not None:
            await self._channel.disconnect()

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
        """Cancel the active Mark request associated with a recalled message."""

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
            raise AgentConfigError("Mark is disabled. Enable it with `lumon agent configure`.")
        self._config = config
        self._context_builder = WorkspaceContextBuilder(
            config=config,
            registry=self.registry,
            soul_loader=self.soul_loader,
        )
        if self.agent_runner is None:
            self.agent_runner = create_agent_runner(config)
        if self._channel is None:
            self._channel = MarkFeishuChannel(config)

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
                raise AgentRuntimeError("Mark conversation session is not available.")
            started_at = _timestamp(self._now())
            run_id = str(uuid4())
            workspace_id: UUID | None = None
            final_text: str | None = None
            status: MarkRunStatus = "failed"
            error_code: str | None = None
            agent_provider: str | None = None
            prompt: str | None = None
            run_started = False
            completed = False
            typing_reaction_id: str | None = None
            try:
                typing_reaction_id = await self._add_typing_reaction(message)
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
                    raise AgentRuntimeError("Mark runtime is not ready.")
                context = context_builder.resolve_workspace()
                workspace_id = context.workspace_id
                self.session_store.attach_workspace(message.event_id, workspace_id)
                self._raise_if_cancellation_requested(message.event_id)
                resume_session_id = session.agent_session_id
                if (
                    resume_session_id is not None
                    and session.workspace_id is not None
                    and session.workspace_id != workspace_id
                ):
                    self.session_store.clear_agent_session(session_id)
                    resume_session_id = None
                if resume_session_id is None:
                    history = self.session_store.load_history(
                        session_id,
                        conversation_key=message.conversation_key,
                        legacy_conversation_key=message.legacy_conversation_key,
                    )
                    prompt = context_builder.build_prompt(context, history, message.text)
                else:
                    prompt = message.text
                runner = self.agent_runner
                if runner is None:
                    raise AgentRuntimeError("Agent runtime is not ready.")
                agent_provider = runner.provider
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
                result = await runner.run(
                    context.path,
                    prompt,
                    agent_session_id=resume_session_id,
                    on_progress=reporter.notify,
                )
                self._raise_if_cancellation_requested(message.event_id)
                if resume_session_id is not None and result.status == "failed":
                    self.session_store.clear_agent_session(session_id)
                elif result.agent_session_id is not None:
                    self.session_store.bind_agent_session(
                        session_id,
                        result.agent_session_id,
                    )
                status = result.status
                error_code = result.error_code.value if result.error_code is not None else None
                if result.status == "succeeded" and result.final_text:
                    final_text = sanitize_output(result.final_text)
                    await self._send(message, final_text)
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
                    await self._send(
                        message,
                        _failure_message(
                            error_code,
                            status=status,
                            agent_name=runner.display_name,
                        ),
                    )
                completed = True
            except asyncio.CancelledError:
                if self.session_store.is_cancellation_requested(message.event_id):
                    if run_started:
                        self.session_store.mark_run_cancelled(
                            run_id,
                            _timestamp(self._now()),
                        )
                    self.session_store.mark_event_cancelled(message.event_id)
                elif run_started:
                    self.session_store.mark_run_interrupted(
                        run_id,
                        _timestamp(self._now()),
                    )
                    # Leave the event in ``processing`` so the next service
                    # start can move it back to ``queued`` and recover it.
                raise
            except LumonError as exc:
                error_code = _error_code(exc)
                agent_name = self.agent_runner.display_name if self.agent_runner else "Agent CLI"
                await self._send(message, _failure_message(error_code, agent_name=agent_name))
                completed = True
            except Exception:
                error_code = "mark_unexpected_error"
                agent_name = self.agent_runner.display_name if self.agent_runner else "Agent CLI"
                await self._send(message, _failure_message(error_code, agent_name=agent_name))
                completed = True
            finally:
                await self._remove_typing_reaction(message, typing_reaction_id)
                if completed:
                    ended_at = _timestamp(self._now())
                    self.session_store.record_result(
                        MarkRunResult(
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
                            prompt_text=prompt if run_started else None,
                        )
                    )

    async def _send(self, message: InboundMessage, text: str) -> None:
        if self._channel is None:
            return
        try:
            await self._channel.reply(message, sanitize_output(text))
        except AgentRuntimeError:
            return

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

    def _task_finished(self, task: asyncio.Task[None]) -> None:
        self._tasks.discard(task)
        for event_id, registered_task in tuple(self._tasks_by_event.items()):
            if registered_task is task:
                self._tasks_by_event.pop(event_id, None)
        if not task.cancelled():
            task.exception()


class _ProgressReporter:
    """Throttle runner events so a busy Agent turn does not spam Feishu."""

    def __init__(self, channel: MarkFeishuChannel, message: InboundMessage) -> None:
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
    status: MarkRunStatus | None = None,
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
        return "Mark 没有得到可用回答。请稍后重试。"
    return "Mark 暂时无法完成这次请求。请运行 `lumon agent doctor` 检查配置和运行环境。"


def _error_code(error: LumonError) -> str:
    if isinstance(error, AgentConfigError):
        return "agent_configuration_invalid"
    if isinstance(error, AgentRuntimeError):
        return "agent_runtime_error"
    return "mark_error"


def _timestamp(now: datetime) -> str:
    return now.astimezone(UTC).isoformat()
