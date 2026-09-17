"""Contract tests for Workspace lifecycle and default-selection commands."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
from typer.testing import CliRunner

from lumon.agents.agent.config import AgentConfig, AgentConfigStore
from lumon.cli.app import app
from lumon.skills.installer import SkillInstaller
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.model import InitRequest
from lumon.workspace.registry import WorkspaceRegistration, WorkspaceRegistry
from lumon.workspace.settings import WorkspaceSettingsStore


def _initialize(tmp_path: Path, state_root: Path, name: str) -> tuple[Path, WorkspaceRegistration]:
    target = tmp_path / name
    WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"),
        registry=WorkspaceRegistry(state_root),
        settings_store=WorkspaceSettingsStore(state_root),
    ).initialize(InitRequest(target, name=name))
    registration = WorkspaceRegistry(state_root).find_by_path(target)
    assert registration is not None
    return target, registration


def _agent_config(state_root: Path, default_workspace_id: UUID | None = None) -> None:
    AgentConfigStore(state_root).save(
        AgentConfig(
            enabled=True,
            default_workspace_id=default_workspace_id,
            feishu_app_id="cli_test",
            feishu_app_secret="secret-value",
        )
    )


def test_workspace_list_and_set_default_support_multiple_workspaces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_root = tmp_path / "lumon"
    monkeypatch.setenv("LUMON_HOME", str(state_root))
    _, first = _initialize(tmp_path, state_root, "first")
    _, second = _initialize(tmp_path, state_root, "second")
    _agent_config(state_root)

    listed = CliRunner().invoke(app, ["workspace", "list"])

    assert listed.exit_code == 0, listed.stdout
    assert first.name in listed.stdout
    assert second.name in listed.stdout
    assert "[ready]" in listed.stdout

    selected = CliRunner().invoke(app, ["workspace", "set-default", str(second.path)])

    assert selected.exit_code == 0, selected.stdout
    assert AgentConfigStore(state_root).load().default_workspace_id == second.workspace_id
    assert "Default Workspace set to second" in selected.stdout

    cleared = CliRunner().invoke(app, ["workspace", "set-default", "--clear"])

    assert cleared.exit_code == 0, cleared.stdout
    assert AgentConfigStore(state_root).load().default_workspace_id is None


def test_workspace_remove_unregisters_and_removes_profile_but_keeps_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_root = tmp_path / "lumon"
    monkeypatch.setenv("LUMON_HOME", str(state_root))
    target, registration = _initialize(tmp_path, state_root, "keep-files")

    result = CliRunner().invoke(
        app, ["workspace", "remove", str(registration.workspace_id), "--yes"]
    )

    assert result.exit_code == 0, result.stdout
    assert WorkspaceRegistry(state_root).find(registration.workspace_id) is None
    assert not WorkspaceSettingsStore(state_root).path_for(registration.workspace_id).exists()
    assert target.is_dir()
    assert "Workspace directory kept" in result.stdout


def test_workspace_remove_delete_requires_confirmation_and_deletes_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_root = tmp_path / "lumon"
    monkeypatch.setenv("LUMON_HOME", str(state_root))
    target, registration = _initialize(tmp_path, state_root, "delete-files")

    result = CliRunner().invoke(
        app,
        ["workspace", "remove", str(target), "--delete"],
        input="y\n",
    )

    assert result.exit_code == 0, result.stdout
    assert not target.exists()
    assert WorkspaceRegistry(state_root).find(registration.workspace_id) is None
    assert "Workspace directory deleted" in result.stdout


def test_workspace_remove_clears_agent_default_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_root = tmp_path / "lumon"
    monkeypatch.setenv("LUMON_HOME", str(state_root))
    target, registration = _initialize(tmp_path, state_root, "default")
    _agent_config(state_root, registration.workspace_id)

    result = CliRunner().invoke(
        app,
        ["workspace", "remove", str(registration.workspace_id), "--yes"],
    )

    assert result.exit_code == 0, result.stdout
    assert AgentConfigStore(state_root).load().default_workspace_id is None
    assert target.is_dir()
    assert WorkspaceRegistry(state_root).find(registration.workspace_id) is None
    assert "default Workspace cleared" in result.stdout
