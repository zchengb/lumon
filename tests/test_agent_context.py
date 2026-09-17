"""Tests for Agent Workspace selection and prompt assembly."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from lumon.agents.agent.config import AgentConfig
from lumon.agents.agent.model import Message
from lumon.agents.agent.prompt import PromptRenderer
from lumon.agents.agent.workspace_context import WorkspaceContextBuilder
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


def _config(workspace_id: UUID | None = None) -> AgentConfig:
    return AgentConfig(
        enabled=True,
        default_workspace_id=workspace_id,
        feishu_app_id="cli_test",
        feishu_app_secret="secret-value",
    )


def _flow_content(brief: str = "Generate test cases.") -> str:
    return (
        "---\n"
        'id = "test-case-generation"\n'
        'name = "Test case generation"\n'
        "enabled = true\n"
        f'brief = "{brief}"\n'
        "---\n\n"
        "# Test case generation\n\n"
        "Follow the Workspace flow.\n"
    )


def test_unique_workspace_is_resolved_and_prompt_contains_local_rules(
    tmp_path: Path,
) -> None:
    state_root = tmp_path / "state"
    target = _workspace(tmp_path, state_root, "review-lab")
    flow_path = target / "lumon" / "flows" / "test-case-generation.md"
    flow_path.write_text(_flow_content(), encoding="utf-8")
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
    assert "不要读取、复制或在回复中暴露凭据" in prompt
    assert "<agent-soul>" in prompt
    assert "<conversation-history>" in prompt
    assert context.flow_briefs[0].flow_id == "test-case-generation"
    assert "<available-flows>" in prompt
    assert "id: test-case-generation; brief:" in prompt
    assert "full detail: lumon/flows/test-case-generation.md" in prompt
    assert "match hints:" not in prompt
    assert "Treat acceptance criteria as the primary authority" not in prompt


def test_resumed_prompt_reloads_workspace_flow_briefs(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    target = _workspace(tmp_path, state_root, "flow-refresh-lab")
    builder = WorkspaceContextBuilder(_config(), WorkspaceRegistry(state_root))
    context = builder.resolve_workspace()
    sample_path = target / "lumon" / "flows" / "test-case-generation.md"
    sample_path.write_text(
        _flow_content("Generate test cases with the refreshed brief."),
        encoding="utf-8",
    )

    prompt = builder.build_resume_prompt(context, "generate test cases")

    assert "Generate test cases with the refreshed brief." in prompt
    assert "Follow the Workspace flow." not in prompt
    assert "<lumon-flow-context>" in prompt


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


def test_prompt_renderer_can_use_a_local_template_without_changing_context_resolution(
    tmp_path: Path,
) -> None:
    state_root = tmp_path / "state"
    _workspace(tmp_path, state_root, "template-lab")
    builder = WorkspaceContextBuilder(
        _config(),
        WorkspaceRegistry(state_root),
        prompt_renderer=PromptRenderer("workspace=${workspace_name}\nmessage=${user_message}\n"),
    )

    prompt = builder.build_prompt(builder.resolve_workspace(), (), "Inspect the template")

    assert prompt == "workspace=template-lab\nmessage=Inspect the template\n"
