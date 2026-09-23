"""Tests for Agent Workspace selection and prompt assembly."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from lumon.agents.agent.config import AgentConfig
from lumon.agents.agent.model import InboundMessage, Message
from lumon.agents.agent.prompt import PromptRenderer
from lumon.agents.agent.workspace_context import WorkspaceContextBuilder
from lumon.errors import AgentRuntimeError, WorkspaceNotFoundError
from lumon.flows.catalog import FlowCatalog
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


def _capability_content(brief: str = "Inspect AWS resources.") -> str:
    return (
        "---\n"
        'id = "aws-cli"\n'
        'name = "AWS CLI"\n'
        "enabled = true\n"
        f'brief = "{brief}"\n'
        "---\n\n"
        "# AWS CLI\n\n"
        "Use the local AWS CLI guidance.\n"
    )


def test_unique_workspace_is_resolved_and_prompt_contains_local_rules(
    tmp_path: Path,
) -> None:
    state_root = tmp_path / "state"
    target = _workspace(tmp_path, state_root, "review-lab")
    flow_path = target / "lumon" / "flows" / "test-case-generation.md"
    flow_path.write_text(_flow_content(), encoding="utf-8")
    capability_path = target / "lumon" / "capabilities" / "aws-cli.md"
    capability_path.write_text(_capability_content(), encoding="utf-8")
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
        channel_context=InboundMessage(
            event_id="event-1",
            message_id="om-source",
            chat_id="oc-current",
            chat_type="group",
            text="Inspect the README",
            sender_id="ou-user",
            sender_type="user",
            thread_id="omt-current",
            root_id="om-root",
        ).channel_context,
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
    assert context.capability_briefs[0].capability_id == "aws-cli"
    assert "<available-capabilities>" in prompt
    assert "id: aws-cli; brief: Inspect AWS resources." in prompt
    assert "full detail: lumon/capabilities/aws-cli.md" in prompt
    assert "<lumon-channel-context>" in prompt
    assert "chat_id: oc-current" in prompt
    assert "source_message_id: om-source" in prompt
    assert "delivery_mode: group_thread" in prompt
    assert "Use the local AWS CLI guidance." not in prompt
    assert "match hints:" not in prompt
    assert "Treat acceptance criteria as the primary authority" not in prompt


def test_resumed_prompt_keeps_only_current_message_context(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    _workspace(tmp_path, state_root, "flow-refresh-lab")
    builder = WorkspaceContextBuilder(_config(), WorkspaceRegistry(state_root))

    prompt = builder.build_resume_prompt("generate test cases")

    assert "<lumon-flow-context>" not in prompt
    assert "<lumon-capability-context>" not in prompt
    assert "<lumon-channel-context>" in prompt
    assert "<user-message>\ngenerate test cases\n</user-message>" in prompt


def test_channel_context_uses_direct_delivery_for_private_messages() -> None:
    message = InboundMessage(
        event_id="event-1",
        message_id="om-private",
        chat_id="oc-private",
        chat_type="p2p",
        text="send the file",
        sender_id="ou-user",
        sender_type="user",
    )

    context = message.channel_context

    assert context.chat_id == "oc-private"
    assert context.source_message_id == "om-private"
    assert context.delivery_mode == "private_direct"


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


def test_scheduled_flow_prompt_contains_only_the_explicitly_selected_flow(
    tmp_path: Path,
) -> None:
    state_root = tmp_path / "state"
    target = _workspace(tmp_path, state_root, "scheduled-flow-lab")
    selected = FlowCatalog(target).create(_flow_content())
    other = FlowCatalog(target).create(
        _flow_content().replace("test-case-generation", "other-flow")
    )
    builder = WorkspaceContextBuilder(_config(), WorkspaceRegistry(state_root))

    prompt = builder.build_prompt(
        builder.resolve_workspace(),
        (),
        f"Run the scheduled Workspace Flow '{selected.flow_id}' now.",
        scheduled_flow=selected,
    )

    assert f"Selected Flow ID: {selected.flow_id}" in prompt
    assert selected.content in prompt
    assert "Follow the Workspace flow." in prompt
    assert f"Selected Flow ID: {other.flow_id}" not in prompt
    assert "do not semantically select another Flow" in prompt
