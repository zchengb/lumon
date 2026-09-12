"""Tests for Mark Workspace selection and prompt assembly."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from lumon.agents.mark.config import MarkAgentConfig
from lumon.agents.mark.model import Message
from lumon.agents.mark.workspace_context import WorkspaceContextBuilder
from lumon.errors import AgentRuntimeError, WorkspaceNotFoundError
from lumon.skills.installer import SkillInstaller
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.model import InitRequest
from lumon.workspace.registry import WorkspaceRegistry


def _workspace(tmp_path: Path, state_root: Path, name: str) -> Path:
    target = tmp_path / name
    WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / f"skills-{name}"),
        registry=WorkspaceRegistry(state_root),
    ).initialize(InitRequest(target, name=name))
    return target


def _config(workspace_id: UUID | None = None) -> MarkAgentConfig:
    return MarkAgentConfig(
        enabled=True,
        default_workspace_id=workspace_id,
        feishu_app_id="cli_test",
        feishu_app_secret="secret-value",
    )


def test_unique_workspace_is_resolved_and_prompt_contains_local_rules(
    tmp_path: Path,
) -> None:
    state_root = tmp_path / "state"
    target = _workspace(tmp_path, state_root, "review-lab")
    registration = WorkspaceRegistry(state_root).list()[0]
    builder = WorkspaceContextBuilder(_config(), WorkspaceRegistry(state_root))

    context = builder.resolve_workspace()
    prompt = builder.build_prompt(
        context,
        (
            Message(
                conversation_key="chat",
                direction="inbound",
                text="What is here?",
                created_at="now",
            ),
        ),
        "Inspect the README",
    )

    assert context.path == target.resolve()
    assert context.workspace_id == registration.workspace_id
    assert "Inspect the README" in prompt
    assert "AGENTS.md" in prompt
    assert "Do not store secrets" in prompt


def test_explicit_missing_workspace_does_not_fallback(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    _workspace(tmp_path, state_root, "available")
    builder = WorkspaceContextBuilder(_config(uuid4()), WorkspaceRegistry(state_root))

    with pytest.raises(WorkspaceNotFoundError, match="not registered"):
        builder.resolve_workspace()


def test_multiple_workspaces_require_explicit_default(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    _workspace(tmp_path, state_root, "first")
    _workspace(tmp_path, state_root, "second")
    builder = WorkspaceContextBuilder(_config(), WorkspaceRegistry(state_root))

    with pytest.raises(AgentRuntimeError, match="multiple Workspaces"):
        builder.resolve_workspace()
