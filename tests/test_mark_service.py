"""Integration tests for Mark orchestration with local fakes."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

from lumon.agents.mark.config import MarkAgentConfig, MarkConfigStore
from lumon.agents.mark.feishu import MarkFeishuChannel, MessageHandler
from lumon.agents.mark.model import AgentResult, InboundMessage
from lumon.agents.mark.runner import ProgressCallback
from lumon.agents.mark.service import MarkAgentService
from lumon.agents.mark.session_store import MarkSessionStore
from lumon.skills.installer import SkillInstaller
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.model import InitRequest
from lumon.workspace.registry import WorkspaceRegistry


class FakeRunner:
    def __init__(self) -> None:
        self.prompts: list[str] = []
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
        on_progress: ProgressCallback | None = None,
    ) -> AgentResult:
        del workspace
        self.prompts.append(prompt)
        if on_progress is not None:
            await on_progress("Test Agent 正在检查 Workspace 文件…")
        return AgentResult(status="succeeded", final_text="Workspace 已检查")


class BlockingRunner(FakeRunner):
    def __init__(self) -> None:
        super().__init__()
        self.started = asyncio.Event()

    async def run(
        self,
        workspace: Path,
        prompt: str,
        on_progress: ProgressCallback | None = None,
    ) -> AgentResult:
        del workspace, prompt, on_progress
        self.started.set()
        await asyncio.Event().wait()
        raise AssertionError("blocking runner should only finish by cancellation")


class FakeChannel(MarkFeishuChannel):
    def __init__(self, config: MarkAgentConfig) -> None:
        super().__init__(config)
        self.replies: list[str] = []

    async def connect(self, on_message: MessageHandler) -> None:
        del on_message

    async def disconnect(self) -> None:
        return None

    async def reply(self, message: InboundMessage, text: str) -> None:
        del message
        self.replies.append(text)


def test_service_persists_and_deduplicates_message(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    workspace = tmp_path / "workspace"
    WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"),
        registry=WorkspaceRegistry(state_root),
    ).initialize(InitRequest(workspace, name="service-test"))
    workspace_id = WorkspaceRegistry(state_root).list()[0].workspace_id
    config = MarkAgentConfig(
        enabled=True,
        default_workspace_id=workspace_id,
        feishu_app_id="cli_test",
        feishu_app_secret="secret-value",
    )
    config_store = MarkConfigStore(state_root)
    config_store.save(config)
    channel = FakeChannel(config)
    runner = FakeRunner()
    store = MarkSessionStore(state_root)
    service = MarkAgentService(
        config_store=config_store,
        registry=WorkspaceRegistry(state_root),
        session_store=store,
        agent_runner=runner,
        channel=channel,
    )
    message = InboundMessage(
        event_id="evt-1",
        message_id="om-1",
        chat_id="oc-1",
        chat_type="p2p",
        text="请检查 README",
        sender_id="ou-1",
        sender_type="user",
    )

    async def run() -> None:
        await service.handle_message(message)
        await service.wait_for_idle()
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

    asyncio.run(run())

    assert channel.replies == [
        "Mark 正在读取当前 Workspace…",
        "Test Agent 正在检查 Workspace 文件…",
        "Workspace 已检查",
        "Mark 正在读取当前 Workspace…",
        "Test Agent 正在检查 Workspace 文件…",
        "Workspace 已检查",
    ]
    assert len(runner.prompts) == 2
    assert "请检查 README" in runner.prompts[1]
    assert "Workspace 已检查" in runner.prompts[1]
    assert store.event_status("evt-1") == "succeeded"
    with sqlite3.connect(store.path) as connection:
        rows = connection.execute(
            "SELECT status, session_id, prompt_text FROM runs ORDER BY started_at"
        ).fetchall()
    assert len(rows) == 2
    assert rows[0][0] == "succeeded"
    assert rows[0][1] == rows[1][1]
    assert rows[0][2] == runner.prompts[0]
    assert rows[1][2] == runner.prompts[1]


def test_service_leaves_interrupted_event_for_restart_recovery(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    workspace = tmp_path / "workspace"
    WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"),
        registry=WorkspaceRegistry(state_root),
    ).initialize(InitRequest(workspace, name="recovery-test"))
    workspace_id = WorkspaceRegistry(state_root).list()[0].workspace_id
    config = MarkAgentConfig(
        enabled=True,
        default_workspace_id=workspace_id,
        feishu_app_id="cli_test",
        feishu_app_secret="secret-value",
    )
    config_store = MarkConfigStore(state_root)
    config_store.save(config)
    store = MarkSessionStore(state_root)
    runner = BlockingRunner()
    service = MarkAgentService(
        config_store=config_store,
        registry=WorkspaceRegistry(state_root),
        session_store=store,
        agent_runner=runner,
        channel=FakeChannel(config),
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
