"""CLI contract checks for exact scheduled Flow dispatch."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import pytest
import typer
from typer.testing import CliRunner

from lumon.agents.agent.config import AgentConfig, AgentConfigStore
from lumon.agents.agent.model import AgentResult
from lumon.cli.app import app
from lumon.cli.commands import flow as flow_commands
from lumon.cli.commands.flow import poll
from lumon.flows.catalog import FlowCatalog
from lumon.skills.installer import SkillInstaller
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.model import InitRequest
from lumon.workspace.registry import WorkspaceRegistry
from lumon.workspace.settings import (
    FlowScheduleSettings,
    WorkspaceSettings,
    WorkspaceSettingsStore,
)


def test_new_flow_and_webhook_commands_are_registered() -> None:
    runner = CliRunner()

    flow_help = runner.invoke(app, ["flow", "poll", "--help"])
    webhook_help = runner.invoke(app, ["webhook", "send", "--help"])

    assert flow_help.exit_code == 0
    assert webhook_help.exit_code == 0


def test_flow_poll_skips_when_schedule_is_not_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_root = tmp_path / "state"
    monkeypatch.setenv("LUMON_HOME", str(state_root))
    registry = WorkspaceRegistry(state_root)
    WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"),
        registry=registry,
        settings_store=WorkspaceSettingsStore(state_root),
    ).initialize(InitRequest(tmp_path / "workspace", name="Flow Workspace"))

    result = CliRunner().invoke(
        app,
        [
            "flow",
            "poll",
            "--workspace",
            str(tmp_path / "workspace"),
            "--flow-id",
            "auto-guard",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert '"status": "disabled"' in result.stdout


def test_flow_poll_rejects_an_overlapping_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_root = tmp_path / "state"
    monkeypatch.setenv("LUMON_HOME", str(state_root))
    registry = WorkspaceRegistry(state_root)
    settings_store = WorkspaceSettingsStore(state_root)
    workspace = tmp_path / "workspace"
    WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"),
        registry=registry,
        settings_store=settings_store,
    ).initialize(InitRequest(workspace, name="Flow Workspace"))
    registration = registry.list()[0]
    FlowCatalog(workspace).create(
        "---\n"
        'id = "auto-guard"\n'
        'name = "Auto Guard"\n'
        "enabled = true\n"
        'brief = "Inspect production health."\n'
        "---\n\n"
        "# Auto Guard\n"
    )
    settings_store.save(
        WorkspaceSettings(
            registration.workspace_id,
            flow_schedules=(FlowScheduleSettings("auto-guard", enabled=True),),
        )
    )
    AgentConfigStore(state_root).save(
        AgentConfig(
            enabled=True,
            default_workspace_id=registration.workspace_id,
            feishu_app_id="cli_test",
            feishu_app_secret="secret-value",
        )
    )
    started = Event()
    release = Event()

    class _BlockingRunner:
        async def run(self, workspace: Path, prompt: str, **_: object) -> AgentResult:
            del workspace, prompt
            started.set()
            await asyncio.to_thread(release.wait, 5)
            return AgentResult(status="succeeded", final_text="done")

    def create_blocking_runner(_config: AgentConfig | None) -> _BlockingRunner:
        return _BlockingRunner()

    monkeypatch.setattr(flow_commands, "create_agent_runner", create_blocking_runner)
    with ThreadPoolExecutor(max_workers=1) as executor:
        first_run = executor.submit(
            poll,
            flow_id="auto-guard",
            workspace=workspace,
            workspace_id=str(registration.workspace_id),
            json_output=True,
        )
        assert started.wait(timeout=3), "the first scheduled Flow run did not start"
        try:
            with pytest.raises(typer.Exit) as error:
                poll(
                    flow_id="auto-guard",
                    workspace=workspace,
                    workspace_id=str(registration.workspace_id),
                    json_output=True,
                )
            assert error.value.exit_code != 0
        finally:
            release.set()
        first_run.result(timeout=3)
