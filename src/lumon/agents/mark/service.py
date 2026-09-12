"""Orchestrate Feishu messages, Workspace context, Codex, and persistence."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from lumon.agents.mark.codex import CodexRunner, sanitize_output
from lumon.agents.mark.config import MarkAgentConfig, MarkConfigStore
from lumon.agents.mark.feishu import MarkFeishuChannel
from lumon.agents.mark.model import InboundMessage, MarkRunResult, MarkRunStatus, Message
from lumon.agents.mark.session_store import MarkSessionStore
from lumon.agents.mark.soul import MarkSoulLoader
from lumon.agents.mark.workspace_context import WorkspaceContextBuilder
from lumon.errors import AgentConfigError, AgentRuntimeError, LumonError
from lumon.workspace.registry import WorkspaceRegistry


class MarkAgentService:
    """Coordinate the Mark message lifecycle with per-conversation ordering."""

    def __init__(
        self,
        config_store: MarkConfigStore | None = None,
        registry: WorkspaceRegistry | None = None,
        session_store: MarkSessionStore | None = None,
        soul_loader: MarkSoulLoader | None = None,
        codex_runner: CodexRunner | None = None,
        channel: MarkFeishuChannel | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.config_store = config_store or MarkConfigStore()
        self.registry = registry or WorkspaceRegistry()
        self.session_store = session_store or MarkSessionStore()
        self.soul_loader = soul_loader or MarkSoulLoader()
        self.codex_runner = codex_runner
        self._channel = channel
        self._now = now or (lambda: datetime.now(UTC))
        self._config: MarkAgentConfig | None = None
        self._context_builder: WorkspaceContextBuilder | None = None
        self._conversation_locks: dict[str, asyncio.Lock] = {}
        self._tasks: set[asyncio.Task[None]] = set()
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
                self._schedule(message)
        try:
            await self._channel.connect(self.handle_message)
        except asyncio.CancelledError:
            raise
        finally:
            await self._shutdown_tasks()
            await self._channel.disconnect()

    async def stop(self) -> None:
        """Request a graceful stop for the channel and in-flight message tasks."""

        if self._stop_event is not None:
            self._stop_event.set()
        if self._channel is not None:
            await self._channel.disconnect()
        await self._shutdown_tasks()

    async def handle_message(self, message: InboundMessage) -> None:
        """Admit one normalized message and enqueue it without duplicate work."""

        if not message.admitted:
            return
        self._ensure_runtime()
        if not self.session_store.claim_event(message.event_id, message):
            return
        self._schedule(message)

    async def wait_for_idle(self) -> None:
        """Wait for currently scheduled messages; useful for integration tests."""

        while self._tasks:
            await asyncio.gather(*tuple(self._tasks))

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
        if self.codex_runner is None:
            self.codex_runner = CodexRunner(model=config.codex_model)
        if self._channel is None:
            self._channel = MarkFeishuChannel(config)

    def _schedule(self, message: InboundMessage) -> None:
        task = asyncio.create_task(self._process(message))
        self._tasks.add(task)
        task.add_done_callback(self._task_finished)

    async def _process(self, message: InboundMessage) -> None:
        lock = self._conversation_locks.setdefault(message.conversation_key, asyncio.Lock())
        async with lock:
            self.session_store.mark_event_status(message.event_id, "processing")
            started_at = _timestamp(self._now())
            run_id = str(uuid4())
            workspace_id: UUID | None = None
            final_text: str | None = None
            status: MarkRunStatus = "failed"
            error_code: str | None = None
            completed = False
            try:
                self.session_store.record_message(
                    Message(
                        conversation_key=message.conversation_key,
                        direction="inbound",
                        message_id=message.message_id,
                        text=message.text,
                        created_at=started_at,
                    )
                )
                context_builder = self._context_builder
                if context_builder is None or self._channel is None:
                    raise AgentRuntimeError("Mark runtime is not ready.")
                context = context_builder.resolve_workspace()
                workspace_id = context.workspace_id
                self.session_store.attach_workspace(message.event_id, workspace_id)
                await self._send(message, "Mark 正在读取当前 Workspace…")
                history = self.session_store.load_history(message.conversation_key)
                prompt = context_builder.build_prompt(context, history, message.text)
                reporter = _ProgressReporter(self._channel, message)
                if self.codex_runner is None:
                    raise AgentRuntimeError("Codex runtime is not ready.")
                result = await self.codex_runner.run(
                    context.path,
                    prompt,
                    on_progress=reporter.notify,
                )
                status = result.status
                error_code = result.error_code
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
                        )
                    )
                else:
                    if status == "succeeded":
                        status = "failed"
                        error_code = error_code or "codex_empty_result"
                    await self._send(message, _failure_message(error_code))
                completed = True
            except asyncio.CancelledError:
                # Leave the event in ``processing`` so the next service start
                # can move it back to ``queued`` and recover it.
                raise
            except LumonError as exc:
                error_code = _error_code(exc)
                await self._send(message, _failure_message(error_code))
                completed = True
            except Exception:
                error_code = "mark_unexpected_error"
                await self._send(message, _failure_message(error_code))
                completed = True
            finally:
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
                            error_code=error_code,
                        )
                    )

    async def _send(self, message: InboundMessage, text: str) -> None:
        if self._channel is None:
            return
        try:
            await self._channel.reply(message, sanitize_output(text))
        except AgentRuntimeError:
            return

    async def _shutdown_tasks(self) -> None:
        tasks = tuple(self._tasks)
        if not tasks:
            return
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()

    def _task_finished(self, task: asyncio.Task[None]) -> None:
        self._tasks.discard(task)
        if not task.cancelled():
            task.exception()


class _ProgressReporter:
    """Throttle provider events so a busy Codex turn does not spam Feishu."""

    def __init__(self, channel: MarkFeishuChannel, message: InboundMessage) -> None:
        self.channel = channel
        self.message = message
        self.last_sent = 0.0
        self.sent = 0

    async def notify(self, text: str) -> None:
        now = time.monotonic()
        if self.sent >= 3 or (self.sent and now - self.last_sent < 2.0):
            return
        self.sent += 1
        self.last_sent = now
        try:
            await self.channel.reply(self.message, sanitize_output(text))
        except AgentRuntimeError:
            return


def _failure_message(error_code: str | None) -> str:
    if error_code == "codex_timeout":
        return "Mark 处理超时了。请稍后重试，或先运行 `lumon agent doctor` 检查本机环境。"
    if error_code == "codex_not_found":
        return "找不到本机 Codex CLI。请安装并登录 Codex 后，再运行 `lumon agent doctor`。"
    if error_code == "codex_empty_result":
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
