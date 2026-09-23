"""Tests for Agent's conversational policy around the shared Codex tool."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from lumon.agents.agent.config import AgentConfig
from lumon.agents.agent.model import AgentErrorCode, AgentEvent
from lumon.agents.agent.runner import CodexAgentRunner, create_agent_runner
from lumon.tools.codex import CodexTool


def test_agent_requires_final_text_even_when_the_shared_tool_succeeds(tmp_path: Path) -> None:
    fake = tmp_path / "fake-codex"
    fake.write_text(
        "#!/bin/sh\n"
        "cat >/dev/null\n"
        'printf \'%s\\n\' \'{"type":"item","item":{"type":"command_execution"}}\'\n',
        encoding="utf-8",
    )
    fake.chmod(0o755)
    runner = CodexAgentRunner(tool=CodexTool(binary=str(fake), timeout_seconds=5))

    result = asyncio.run(runner.run(tmp_path, "inspect this"))

    assert result.status == "failed"
    assert result.error_code == AgentErrorCode.EMPTY_RESULT
    assert result.progress == ()


def test_agent_preserves_provider_failure_diagnostic(tmp_path: Path) -> None:
    fake = tmp_path / "fake-codex"
    fake.write_text(
        "#!/bin/sh\ncat >/dev/null\nprintf 'provider failed\\n' >&2\nexit 1\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    runner = CodexAgentRunner(tool=CodexTool(binary=str(fake), timeout_seconds=5))

    result = asyncio.run(runner.run(tmp_path, "inspect this"))

    assert result.status == "failed"
    assert result.failure_diagnostic == "provider failed"


def test_agent_extracts_a_flow_marker_emitted_before_the_final_reply(tmp_path: Path) -> None:
    fake = tmp_path / "fake-codex"
    fake.write_text(
        f"#!{sys.executable}\n"
        "import json\n"
        "import sys\n"
        "sys.stdin.buffer.read()\n"
        "for text in [\n"
        '    \'<lumon-flow>{"flow_id":"test-case-generation","status":"selected"}</lumon-flow>\',\n'
        "    'Generated test cases.',\n"
        "]:\n"
        "    event = {'type': 'item', 'item': {'type': 'agent_message', 'text': text}}\n"
        "    print(json.dumps(event))\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    runner = CodexAgentRunner(tool=CodexTool(binary=str(fake), timeout_seconds=5))

    result = asyncio.run(runner.run(tmp_path, "generate test cases"))

    assert result.status == "succeeded"
    assert result.flow_id == "test-case-generation"
    assert result.final_text == "Generated test cases."


def test_agent_forwards_codex_activity_events(tmp_path: Path) -> None:
    fake = tmp_path / "fake-codex"
    fake.write_text(
        f"#!{sys.executable}\n"
        "import json\n"
        "import sys\n"
        "sys.stdin.buffer.read()\n"
        "for event in [\n"
        "    {'type': 'item.started', 'item': {'type': 'command_execution',"
        " 'id': 'cmd-1', 'command': 'printf hello'}},\n"
        "    {'type': 'item.completed', 'item': {'type': 'command_execution',"
        " 'id': 'cmd-1', 'aggregated_output': 'hello', 'exit_code': 0,"
        " 'status': 'completed'}},\n"
        "    {'type': 'item.completed', 'item': {'type': 'agent_message',"
        " 'text': 'done'}},\n"
        "]:\n"
        "    print(json.dumps(event))\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    runner = CodexAgentRunner(tool=CodexTool(binary=str(fake), timeout_seconds=5))
    events: list[AgentEvent] = []

    async def record(event: AgentEvent) -> None:
        events.append(event)

    result = asyncio.run(runner.run(tmp_path, "inspect this", on_event=record))

    assert result.status == "succeeded"
    assert [(event.kind, event.lifecycle) for event in events] == [
        ("command_execution", "started"),
        ("command_execution", "completed"),
    ]
    assert events[0].command == "printf hello"
    assert events[1].output == "hello"


def test_agent_defaults_to_codex_luna_max(tmp_path: Path) -> None:
    runner = create_agent_runner()

    assert isinstance(runner, CodexAgentRunner)
    assert runner.tool.build_command(tmp_path)[1:] == (
        "exec",
        "--json",
        "--cd",
        str(tmp_path),
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "--model",
        "gpt-6-luna",
        "--config",
        'model_reasoning_effort="max"',
    )


def test_agent_uses_model_and_effort_from_agent_config(tmp_path: Path) -> None:
    config = AgentConfig(
        agent_model="gpt-5.6-sol",
        agent_reasoning_effort="ultra",
        feishu_app_id="cli_test",
        feishu_app_secret="secret-value",
    )
    runner = create_agent_runner(config)

    assert isinstance(runner, CodexAgentRunner)
    assert runner.tool.build_command(tmp_path, resume_session_id="thread-1")[1:] == (
        "exec",
        "--json",
        "--cd",
        str(tmp_path),
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "--model",
        "gpt-5.6-sol",
        "--config",
        'model_reasoning_effort="ultra"',
        "resume",
        "thread-1",
        "-",
    )
