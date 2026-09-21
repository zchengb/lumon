"""Integration tests for Agent orchestration with local fakes."""

from __future__ import annotations

import asyncio
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast

from lumon.agents.agent.config import AgentConfig, AgentConfigStore
from lumon.agents.agent.feishu import AgentFeishuChannel, MessageHandler
from lumon.agents.agent.model import (
    AgentErrorCode,
    AgentEvent,
    AgentProgress,
    AgentResult,
    InboundImage,
    InboundMessage,
    ProgressPhase,
    RecalledMessage,
)
from lumon.agents.agent.runner import AgentEventCallback, ProgressCallback
from lumon.agents.agent.service import AgentService
from lumon.agents.agent.session_store import AgentSessionStore
from lumon.errors import AgentRuntimeError
from lumon.observability import (
    AgentTrace,
    ObservationType,
    TelemetryLevel,
    TelemetryMetadata,
    TelemetryStatus,
)
from lumon.skills.installer import SkillInstaller
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.model import InitRequest
from lumon.workspace.registry import WorkspaceRegistry


class FakeRunner:
    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.agent_session_ids: list[str | None] = []
        self.images: list[tuple[Path, ...]] = []
        self.next_flow_id: str | None = None
        self.next_final_text = "Workspace 已检查"
        self.next_events: tuple[AgentEvent, ...] = ()
        self.provider = "test-agent"
        self.display_name = "Test Agent"
        self.executable = "test-agent"

    def is_available(self) -> bool:
        return True

    def is_authenticated(self) -> bool:
        return True

    async def run(
        self,
        workspace: Path,
        prompt: str,
        *,
        agent_session_id: str | None = None,
        images: tuple[Path, ...] = (),
        on_progress: ProgressCallback | None = None,
        on_event: AgentEventCallback | None = None,
    ) -> AgentResult:
        del workspace
        self.prompts.append(prompt)
        self.agent_session_ids.append(agent_session_id)
        self.images.append(images)
        if on_event is not None:
            for event in getattr(self, "next_events", ()):
                await on_event(event)
        if on_progress is not None:
            await on_progress(
                AgentProgress(
                    phase=ProgressPhase.INSPECTING,
                    message="Test Agent 正在检查 Workspace 文件…",
                )
            )
        return AgentResult(
            status="succeeded",
            final_text=self.next_final_text,
            agent_session_id="provider-session-1",
            flow_id=self.next_flow_id,
        )


class BlockingRunner(FakeRunner):
    def __init__(self) -> None:
        super().__init__()
        self.started = asyncio.Event()

    async def run(
        self,
        workspace: Path,
        prompt: str,
        *,
        agent_session_id: str | None = None,
        images: tuple[Path, ...] = (),
        on_progress: ProgressCallback | None = None,
        on_event: AgentEventCallback | None = None,
    ) -> AgentResult:
        del workspace, prompt, agent_session_id, images, on_progress, on_event
        self.started.set()
        await asyncio.Event().wait()
        raise AssertionError("blocking runner should only finish by cancellation")


class FailingRunner(FakeRunner):
    async def run(
        self,
        workspace: Path,
        prompt: str,
        *,
        agent_session_id: str | None = None,
        images: tuple[Path, ...] = (),
        on_progress: ProgressCallback | None = None,
        on_event: AgentEventCallback | None = None,
    ) -> AgentResult:
        del workspace, prompt, agent_session_id, images, on_progress, on_event
        raise RuntimeError("private request content must not be stored")


class ProviderFailingRunner(FakeRunner):
    async def run(
        self,
        workspace: Path,
        prompt: str,
        *,
        agent_session_id: str | None = None,
        images: tuple[Path, ...] = (),
        on_progress: ProgressCallback | None = None,
        on_event: AgentEventCallback | None = None,
    ) -> AgentResult:
        del workspace, prompt, agent_session_id, images, on_progress, on_event
        return AgentResult(
            status="failed",
            error_code=AgentErrorCode.EXECUTION_FAILED,
            return_code=1,
            failure_diagnostic="app_secret=secret-value\nprovider failed",
        )


class TimedOutRunner(FakeRunner):
    async def run(
        self,
        workspace: Path,
        prompt: str,
        *,
        agent_session_id: str | None = None,
        images: tuple[Path, ...] = (),
        on_progress: ProgressCallback | None = None,
        on_event: AgentEventCallback | None = None,
    ) -> AgentResult:
        del workspace, prompt, agent_session_id, images, on_progress, on_event
        return AgentResult(status="timed_out", error_code=AgentErrorCode.TIMEOUT)


class FakeChannel(AgentFeishuChannel):
    def __init__(self, config: AgentConfig) -> None:
        super().__init__(config)
        self.replies: list[str] = []
        self.typing_added: list[str] = []
        self.typing_removed: list[tuple[str, str]] = []
        self.fail_replies = False

    async def connect(
        self,
        on_message: MessageHandler,
        on_recalled: object = None,
    ) -> None:
        del on_message, on_recalled

    async def disconnect(self) -> None:
        return None

    async def reply(self, message: InboundMessage, text: str) -> None:
        del message
        if self.fail_replies:
            raise AgentRuntimeError("test reply failure")
        self.replies.append(text)

    async def add_typing(self, message_id: str) -> str:
        self.typing_added.append(message_id)
        return f"reaction:{message_id}"

    async def remove_typing(self, message_id: str, reaction_id: str) -> None:
        self.typing_removed.append((message_id, reaction_id))

    async def download_image(
        self,
        message: InboundMessage,
        image: InboundImage,
        destination: Path,
    ) -> Path:
        assert message.message_id
        path = destination / f"{image.file_key}.png"
        path.write_bytes(b"image")
        return path


class RecordingSpan:
    def __init__(self, name: str) -> None:
        self.name = name
        self.updates: list[dict[str, object]] = []
        self.children: list[RecordingSpan] = []

    def update(
        self,
        *,
        input_text: str | None = None,
        output_text: str | None = None,
        metadata: TelemetryMetadata | None = None,
        level: TelemetryLevel | None = None,
        status_message: str | None = None,
    ) -> None:
        self.updates.append(
            {
                "input_text": input_text,
                "output_text": output_text,
                "metadata": dict(metadata) if metadata else None,
                "level": level,
                "status_message": status_message,
            }
        )

    @asynccontextmanager
    async def span(
        self,
        name: str,
        *,
        as_type: ObservationType = "span",
        metadata: TelemetryMetadata | None = None,
    ):
        del as_type, metadata
        child = RecordingSpan(name)
        self.children.append(child)
        try:
            yield child
        finally:
            pass


class RecordingTrace:
    def __init__(self, arguments: dict[str, object]) -> None:
        self.arguments = arguments
        self.span_names: list[str] = []
        self.spans: list[RecordingSpan] = []
        self.finished: tuple[TelemetryStatus, str | None, str | None] | None = None
        self.updates: list[dict[str, object]] = []

    def update(
        self,
        *,
        input_text: str | None = None,
        output_text: str | None = None,
        metadata: TelemetryMetadata | None = None,
        level: TelemetryLevel | None = None,
        status_message: str | None = None,
    ) -> None:
        self.updates.append(
            {
                "input_text": input_text,
                "output_text": output_text,
                "metadata": dict(metadata) if metadata else None,
                "level": level,
                "status_message": status_message,
            }
        )

    def finish(
        self,
        *,
        status: TelemetryStatus,
        error_code: str | None = None,
        final_text: str | None = None,
    ) -> None:
        self.finished = (status, error_code, final_text)

    @asynccontextmanager
    async def span(
        self,
        name: str,
        *,
        as_type: ObservationType = "span",
        metadata: TelemetryMetadata | None = None,
    ):
        del as_type, metadata
        self.span_names.append(name)
        span = RecordingSpan(name)
        self.spans.append(span)
        try:
            yield span
        finally:
            pass


class RecordingTelemetry:
    def __init__(self) -> None:
        self.traces: list[RecordingTrace] = []
        self.shutdown_calls = 0

    def start_trace(
        self,
        *,
        run_id: str,
        session_id: str,
        event_id: str,
        sender_id: str,
        chat_type: str,
        workspace_id: object,
        provider: str,
        model: str,
        reasoning_effort: str,
        input_text: str,
    ) -> AgentTrace:
        arguments = {
            "run_id": run_id,
            "session_id": session_id,
            "event_id": event_id,
            "sender_id": sender_id,
            "chat_type": chat_type,
            "workspace_id": workspace_id,
            "provider": provider,
            "model": model,
            "reasoning_effort": reasoning_effort,
            "input_text": input_text,
        }
        trace = RecordingTrace(arguments)
        self.traces.append(trace)
        return trace

    def shutdown(self) -> None:
        self.shutdown_calls += 1


def test_service_persists_and_deduplicates_message(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    workspace = tmp_path / "workspace"
    WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"),
        registry=WorkspaceRegistry(state_root),
    ).initialize(InitRequest(workspace, name="service-test"))
    (workspace / "lumon" / "flows" / "test-case-generation.md").write_text(
        "---\n"
        'id = "test-case-generation"\n'
        'name = "Test case generation"\n'
        "enabled = true\n"
        'brief = "Generate test cases."\n'
        "---\n\n"
        "# Test case generation\n",
        encoding="utf-8",
    )
    workspace_id = WorkspaceRegistry(state_root).list()[0].workspace_id
    config = AgentConfig(
        enabled=True,
        default_workspace_id=workspace_id,
        feishu_app_id="cli_test",
        feishu_app_secret="secret-value",
    )
    config_store = AgentConfigStore(state_root)
    config_store.save(config)
    channel = FakeChannel(config)
    runner = FakeRunner()
    runner.next_events = (
        AgentEvent(
            kind="progress",
            phase="inspecting",
            text="正在检查 Workspace。",
        ),
        AgentEvent(
            kind="command_execution",
            lifecycle="started",
            operation_id="command-1",
            command="printf hello",
        ),
        AgentEvent(
            kind="command_execution",
            lifecycle="completed",
            operation_id="command-1",
            output="hello",
            status="completed",
            exit_code=0,
        ),
    )
    telemetry = RecordingTelemetry()
    store = AgentSessionStore(state_root)
    service = AgentService(
        config_store=config_store,
        registry=WorkspaceRegistry(state_root),
        session_store=store,
        agent_runner=runner,
        channel=channel,
        telemetry=telemetry,
    )
    message = InboundMessage(
        event_id="evt-1",
        message_id="om-1",
        chat_id="oc-1",
        chat_type="p2p",
        text="请检查 README",
        sender_id="ou-1",
        sender_type="user",
        images=(InboundImage(file_key="img-1"),),
    )
    card = InboundMessage(
        event_id="evt-card",
        message_id="om-card",
        chat_id="oc-1",
        chat_type="p2p",
        text="转发邮件的卡片内容",
        sender_id="ou-1",
        sender_type="user",
        card_only=True,
    )

    async def run() -> None:
        await service.handle_message(card)
        await service.wait_for_idle()
        assert runner.prompts == []
        assert channel.replies == []
        await service.handle_message(message)
        await service.wait_for_idle()
        runner.next_final_text = (
            '<lumon-flow>{"flow_id":"test-case-generation","status":"selected"}</lumon-flow>\n'
            "Workspace 已检查"
        )
        follow_up = InboundMessage(
            event_id="evt-2",
            message_id="om-2",
            chat_id="oc-1",
            chat_type="p2p",
            text="请继续说明目录",
            sender_id="ou-1",
            sender_type="user",
            thread_id="a-new-feishu-thread-metadata-value",
        )
        await service.handle_message(follow_up)
        await service.wait_for_idle()
        await service.handle_message(message)
        await service.wait_for_idle()
        await service.stop()

    asyncio.run(run())

    assert channel.replies == [
        "Test Agent 正在检查 Workspace 文件…",
        "Workspace 已检查",
        "Test Agent 正在检查 Workspace 文件…",
        "Workspace 已检查",
    ]
    assert channel.typing_added == ["om-1", "om-2"]
    assert channel.typing_removed == [
        ("om-1", "reaction:om-1"),
        ("om-2", "reaction:om-2"),
    ]
    assert len(runner.prompts) == 2
    assert "<feishu-card-context>" in runner.prompts[0]
    assert "转发邮件的卡片内容" in runner.prompts[0]
    assert runner.agent_session_ids == [None, "provider-session-1"]
    assert runner.images[0][0].name == "img-1.png"
    assert not runner.images[0][0].exists()
    assert "<lumon-flow-context>" not in runner.prompts[1]
    assert "<lumon-capability-context>" not in runner.prompts[1]
    assert "test-case-generation" in runner.prompts[0]
    assert "<lumon-channel-context>" in runner.prompts[0]
    assert "chat_id: oc-1" in runner.prompts[0]
    assert "source_message_id: om-1" in runner.prompts[0]
    assert "delivery_mode: private_direct" in runner.prompts[0]
    assert "chat_id: oc-1" in runner.prompts[1]
    assert "source_message_id: om-2" in runner.prompts[1]
    assert "请继续说明目录" in runner.prompts[1]
    assert "请检查 README" not in runner.prompts[1]
    assert "Workspace 已检查" not in runner.prompts[1]
    assert store.event_status("evt-1") == "succeeded"
    with sqlite3.connect(store.path) as connection:
        rows = connection.execute(
            "SELECT status, session_id, prompt_text, flow_id FROM runs ORDER BY started_at"
        ).fetchall()
        session_row = connection.execute("SELECT agent_session_id FROM sessions").fetchone()
    assert len(rows) == 2
    assert rows[0][0] == "succeeded"
    assert rows[0][1] == rows[1][1]
    assert rows[0][2] == runner.prompts[0]
    assert rows[1][2] == runner.prompts[1]
    assert rows[0][3] is None
    assert rows[1][3] == "test-case-generation"
    assert session_row == ("provider-session-1",)
    assert len(telemetry.traces) == 2
    assert telemetry.traces[0].span_names == [
        "workspace.resolve",
        "history.load",
        "prompt.build",
        "codex.exec",
        "feishu.reply",
    ]
    assert telemetry.traces[1].span_names == [
        "workspace.resolve",
        "codex.exec",
        "feishu.reply",
    ]
    codex_span = telemetry.traces[0].spans[3]
    assert [child.name for child in codex_span.children] == [
        "codex.phase",
        "codex.command",
    ]
    command_updates = codex_span.children[1].updates
    assert any(update["input_text"] == "printf hello" for update in command_updates)
    assert any(update["output_text"] == "hello" for update in command_updates)
    assert any(
        isinstance(update["metadata"], dict) and "duration_ms" in update["metadata"]
        for update in command_updates
    )
    assert (
        telemetry.traces[0].arguments["session_id"] == telemetry.traces[1].arguments["session_id"]
    )
    assert telemetry.traces[0].finished == ("succeeded", None, "Workspace 已检查")
    assert telemetry.traces[1].finished == ("succeeded", None, "Workspace 已检查")
    assert any(
        update["metadata"] == {"flow_id": "test-case-generation"}
        for update in telemetry.traces[1].updates
    )
    assert telemetry.shutdown_calls == 1


def test_service_stores_safe_diagnostic_for_unexpected_errors(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    workspace = tmp_path / "workspace"
    WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"),
        registry=WorkspaceRegistry(state_root),
    ).initialize(InitRequest(workspace, name="failure-diagnostic-test"))
    workspace_id = WorkspaceRegistry(state_root).list()[0].workspace_id
    config = AgentConfig(
        enabled=True,
        default_workspace_id=workspace_id,
        feishu_app_id="cli_test",
        feishu_app_secret="secret-value",
    )
    config_store = AgentConfigStore(state_root)
    config_store.save(config)
    store = AgentSessionStore(state_root)
    channel = FakeChannel(config)
    telemetry = RecordingTelemetry()
    service = AgentService(
        config_store=config_store,
        registry=WorkspaceRegistry(state_root),
        session_store=store,
        agent_runner=FailingRunner(),
        channel=channel,
        telemetry=telemetry,
    )
    message = InboundMessage(
        event_id="evt-failure-diagnostic",
        message_id="om-failure-diagnostic",
        chat_id="oc-failure-diagnostic",
        chat_type="p2p",
        text="test request",
        sender_id="ou-1",
        sender_type="user",
    )

    async def run() -> None:
        await service.handle_message(message)
        await service.wait_for_idle()

    asyncio.run(run())

    with sqlite3.connect(store.path) as connection:
        run_row = connection.execute(
            "SELECT error_code, failure_diagnostic FROM runs WHERE event_id = ?",
            (message.event_id,),
        ).fetchone()

    assert run_row is not None
    assert run_row[0] == "agent_unexpected_error"
    assert run_row[1].startswith("workspace_error_log:lumon/logs/agent-errors/")
    error_log = workspace / run_row[1].split(":", 1)[1]
    assert error_log.is_file()
    assert "RuntimeError" in error_log.read_text(encoding="utf-8")
    assert "private request content" not in error_log.read_text(encoding="utf-8")
    assert channel.replies[-1].startswith("Agent 暂时无法完成这次请求")
    assert len(telemetry.traces) == 1
    assert telemetry.traces[0].finished == ("failed", "agent_unexpected_error", None)
    assert telemetry.traces[0].span_names[-2:] == ["codex.exec", "feishu.reply"]
    asyncio.run(service.stop())


def test_service_writes_provider_failure_log_under_workspace(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    workspace = tmp_path / "workspace"
    WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"),
        registry=WorkspaceRegistry(state_root),
    ).initialize(InitRequest(workspace, name="provider-failure-log-test"))
    workspace_id = WorkspaceRegistry(state_root).list()[0].workspace_id
    config = AgentConfig(
        enabled=True,
        default_workspace_id=workspace_id,
        feishu_app_id="cli_test",
        feishu_app_secret="secret-value",
    )
    config_store = AgentConfigStore(state_root)
    config_store.save(config)
    store = AgentSessionStore(state_root)
    telemetry = RecordingTelemetry()
    service = AgentService(
        config_store=config_store,
        registry=WorkspaceRegistry(state_root),
        session_store=store,
        agent_runner=ProviderFailingRunner(),
        channel=FakeChannel(config),
        telemetry=telemetry,
    )
    message = InboundMessage(
        event_id="evt-provider-failure-log",
        message_id="om-provider-failure-log",
        chat_id="oc-provider-failure-log",
        chat_type="p2p",
        text="test request",
        sender_id="ou-1",
        sender_type="user",
    )

    async def run() -> None:
        await service.handle_message(message)
        await service.wait_for_idle()

    asyncio.run(run())

    log_files = tuple((workspace / "lumon" / "logs" / "agent-errors").glob("*.log"))
    assert len(log_files) == 1
    log_text = log_files[0].read_text(encoding="utf-8")
    assert "provider failed" in log_text
    assert "secret-value" not in log_text
    assert "test request" not in log_text
    assert log_files[0].stat().st_mode & 0o777 == 0o600
    with sqlite3.connect(store.path) as connection:
        failure_diagnostic = connection.execute(
            "SELECT failure_diagnostic FROM runs WHERE event_id = ?",
            (message.event_id,),
        ).fetchone()[0]
    assert failure_diagnostic.startswith("workspace_error_log:lumon/logs/agent-errors/")
    error_log_metadata: dict[str, object] | None = None
    for update in telemetry.traces[0].updates:
        metadata_value = update.get("metadata")
        if not isinstance(metadata_value, dict):
            continue
        metadata = cast(dict[str, object], metadata_value)
        if isinstance(metadata.get("error_log"), str):
            error_log_metadata = metadata
            break
    assert error_log_metadata is not None
    error_log = error_log_metadata["error_log"]
    assert isinstance(error_log, str)
    assert error_log.startswith("lumon/logs/agent-errors/")
    asyncio.run(service.stop())


def test_service_records_timeout_in_trace(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    workspace = tmp_path / "workspace"
    WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"),
        registry=WorkspaceRegistry(state_root),
    ).initialize(InitRequest(workspace, name="timeout-test"))
    workspace_id = WorkspaceRegistry(state_root).list()[0].workspace_id
    config = AgentConfig(
        enabled=True,
        default_workspace_id=workspace_id,
        feishu_app_id="cli_test",
        feishu_app_secret="secret-value",
    )
    config_store = AgentConfigStore(state_root)
    config_store.save(config)
    store = AgentSessionStore(state_root)
    telemetry = RecordingTelemetry()
    service = AgentService(
        config_store=config_store,
        registry=WorkspaceRegistry(state_root),
        session_store=store,
        agent_runner=TimedOutRunner(),
        channel=FakeChannel(config),
        telemetry=telemetry,
    )
    message = InboundMessage(
        event_id="evt-timeout",
        message_id="om-timeout",
        chat_id="oc-timeout",
        chat_type="p2p",
        text="请检查状态",
        sender_id="ou-1",
        sender_type="user",
    )

    async def run() -> None:
        await service.handle_message(message)
        await service.wait_for_idle()

    asyncio.run(run())

    assert telemetry.traces[0].finished == ("timed_out", "timeout", None)
    asyncio.run(service.stop())


def test_service_records_feishu_reply_failure_without_changing_agent_result(
    tmp_path: Path,
) -> None:
    state_root = tmp_path / "state"
    workspace = tmp_path / "workspace"
    WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"),
        registry=WorkspaceRegistry(state_root),
    ).initialize(InitRequest(workspace, name="reply-failure-test"))
    workspace_id = WorkspaceRegistry(state_root).list()[0].workspace_id
    config = AgentConfig(
        enabled=True,
        default_workspace_id=workspace_id,
        feishu_app_id="cli_test",
        feishu_app_secret="secret-value",
    )
    config_store = AgentConfigStore(state_root)
    config_store.save(config)
    store = AgentSessionStore(state_root)
    channel = FakeChannel(config)
    channel.fail_replies = True
    telemetry = RecordingTelemetry()
    service = AgentService(
        config_store=config_store,
        registry=WorkspaceRegistry(state_root),
        session_store=store,
        agent_runner=FakeRunner(),
        channel=channel,
        telemetry=telemetry,
    )
    message = InboundMessage(
        event_id="evt-reply-failure",
        message_id="om-reply-failure",
        chat_id="oc-reply-failure",
        chat_type="p2p",
        text="请检查状态",
        sender_id="ou-1",
        sender_type="user",
    )

    async def run() -> None:
        await service.handle_message(message)
        await service.wait_for_idle()

    asyncio.run(run())

    assert channel.replies == []
    assert telemetry.traces[0].finished == ("failed", "feishu_reply_failed", "Workspace 已检查")
    assert telemetry.traces[0].spans[-1].updates[-1]["metadata"] == {
        "delivered": False,
        "error_code": "feishu_reply_failed",
    }
    asyncio.run(service.stop())


def test_service_leaves_interrupted_event_for_restart_recovery(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    workspace = tmp_path / "workspace"
    WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"),
        registry=WorkspaceRegistry(state_root),
    ).initialize(InitRequest(workspace, name="recovery-test"))
    workspace_id = WorkspaceRegistry(state_root).list()[0].workspace_id
    config = AgentConfig(
        enabled=True,
        default_workspace_id=workspace_id,
        feishu_app_id="cli_test",
        feishu_app_secret="secret-value",
    )
    config_store = AgentConfigStore(state_root)
    config_store.save(config)
    store = AgentSessionStore(state_root)
    runner = BlockingRunner()
    telemetry = RecordingTelemetry()
    service = AgentService(
        config_store=config_store,
        registry=WorkspaceRegistry(state_root),
        session_store=store,
        agent_runner=runner,
        channel=FakeChannel(config),
        telemetry=telemetry,
    )
    message = InboundMessage(
        event_id="evt-recovery",
        message_id="om-recovery",
        chat_id="oc-recovery",
        chat_type="p2p",
        text="继续处理",
        sender_id="ou-1",
        sender_type="user",
    )

    async def run() -> None:
        await service.handle_message(message)
        await runner.started.wait()
        await service.stop()

    asyncio.run(run())

    assert store.event_status(message.event_id) == "processing"
    assert store.recover_pending() == (message,)
    assert telemetry.traces[0].finished == ("interrupted", "interrupted", None)


def test_recalled_message_cancels_only_its_running_task(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    workspace = tmp_path / "workspace"
    WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"),
        registry=WorkspaceRegistry(state_root),
    ).initialize(InitRequest(workspace, name="recall-test"))
    workspace_id = WorkspaceRegistry(state_root).list()[0].workspace_id
    config = AgentConfig(
        enabled=True,
        default_workspace_id=workspace_id,
        feishu_app_id="cli_test",
        feishu_app_secret="secret-value",
    )
    config_store = AgentConfigStore(state_root)
    config_store.save(config)
    store = AgentSessionStore(state_root)
    channel = FakeChannel(config)
    runner = BlockingRunner()
    telemetry = RecordingTelemetry()
    service = AgentService(
        config_store=config_store,
        registry=WorkspaceRegistry(state_root),
        session_store=store,
        agent_runner=runner,
        channel=channel,
        telemetry=telemetry,
    )
    message = InboundMessage(
        event_id="evt-recall",
        message_id="om-recall",
        chat_id="oc-recall",
        chat_type="p2p",
        text="请检查 README",
        sender_id="ou-1",
        sender_type="user",
    )

    async def run() -> None:
        await service.handle_message(message)
        await runner.started.wait()
        await service.handle_recalled(
            RecalledMessage(event_id="recall-event", message_id=message.message_id)
        )
        await service.wait_for_idle()

    asyncio.run(run())

    assert store.event_status(message.event_id) == "cancelled"
    assert channel.replies == []
    assert channel.typing_added == [message.message_id]
    assert channel.typing_removed == [(message.message_id, f"reaction:{message.message_id}")]
    with sqlite3.connect(store.path) as connection:
        row = connection.execute(
            "SELECT status, error_code FROM runs WHERE event_id = ?",
            (message.event_id,),
        ).fetchone()
    assert row == ("cancelled", "message_recalled")
    assert telemetry.traces[0].finished == ("cancelled", "message_recalled", None)
