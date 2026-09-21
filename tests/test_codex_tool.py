"""Tests for the reusable local Codex execution tool."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from lumon.tools.codex import CodexRequest, CodexTool, parse_codex_line
from lumon.tools.safety import sanitize_output


def test_codex_tool_defaults_to_twelve_hour_timeout() -> None:
    assert CodexTool(binary="codex").timeout_seconds == 12 * 60 * 60


def test_codex_jsonl_parser_is_provider_specific_but_not_agent_specific() -> None:
    session = parse_codex_line('{"type":"thread.started","thread_id":"thread-1"}')
    final = parse_codex_line('{"type":"item","item":{"type":"agent_message","text":"done"}}')
    command = parse_codex_line(
        '{"type":"item.started","item":{"type":"command_execution",'
        '"id":"cmd-1","command":"printf hello"}}'
    )
    completed_command = parse_codex_line(
        '{"type":"item.completed","item":{"type":"command_execution",'
        '"id":"cmd-1","aggregated_output":"hello\\n","exit_code":0,'
        '"status":"completed"}}'
    )
    file_change = parse_codex_line('{"type":"item","item":{"type":"file_change"}}')

    assert session is not None and session.kind == "session"
    assert session.agent_session_id == "thread-1"
    assert final is not None and final.kind == "message" and final.text == "done"
    assert command is not None and command.kind == "command_execution"
    assert command.lifecycle == "started"
    assert command.operation_id == "cmd-1"
    assert command.command == "printf hello"
    assert completed_command is not None
    assert completed_command.lifecycle == "completed"
    assert completed_command.output == "hello"
    assert completed_command.exit_code == 0
    assert file_change is not None and file_change.kind == "file_change"
    assert "执行 Workspace" not in str(command.text)
    assert "[REDACTED]" in sanitize_output(
        "app_secret=secret-value https://open.feishu.cn/open-apis/bot/v2/hook/token"
    )


def test_codex_parser_ignores_advisory_item_errors_but_keeps_terminal_failures() -> None:
    advisory = parse_codex_line(
        '{"type":"item.completed","item":{"type":"error","message":"advisory"}}'
    )
    terminal = parse_codex_line('{"type":"turn.failed"}')

    assert advisory is None
    assert terminal is not None
    assert terminal.kind == "error"


def test_codex_parser_keeps_terminal_failure_message() -> None:
    terminal = parse_codex_line('{"type":"turn.failed","message":"provider failed"}')

    assert terminal is not None
    assert terminal.text == "provider failed"


def test_codex_tool_succeeds_after_advisory_item_error(tmp_path: Path) -> None:
    fake = tmp_path / "fake-codex"
    advisory_line = json.dumps(
        {"type": "item.completed", "item": {"type": "error", "message": "advisory"}}
    )
    message_line = json.dumps(
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": "done"},
        }
    )
    fake.write_text(
        "#!/bin/sh\n"
        "cat >/dev/null\n"
        f"printf '%s\\n' '{advisory_line}'\n"
        f"printf '%s\\n' '{message_line}'\n"
        "printf '%s\\n' '{\"type\":\"turn.completed\"}'\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    tool = CodexTool(binary=str(fake), timeout_seconds=5)

    result = asyncio.run(tool.execute(CodexRequest(tmp_path, "inspect this")))

    assert result.status == "succeeded"
    assert result.final_text == "done"


def test_codex_tool_keeps_redacted_stderr_for_failed_execution(tmp_path: Path) -> None:
    fake = tmp_path / "fake-codex"
    fake.write_text(
        "#!/bin/sh\n"
        "cat >/dev/null\n"
        "printf 'app_secret=secret-value\\nprovider failed\\n' >&2\n"
        "exit 7\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    tool = CodexTool(binary=str(fake), timeout_seconds=5)

    result = asyncio.run(tool.execute(CodexRequest(tmp_path, "inspect this")))

    assert result.status == "failed"
    assert result.return_code == 7
    assert result.failure_diagnostic is not None
    assert "provider failed" in result.failure_diagnostic
    assert "secret-value" not in result.failure_diagnostic
    assert "[REDACTED]" in result.failure_diagnostic


def test_codex_parser_accepts_explicit_agent_progress() -> None:
    event = parse_codex_line(
        '{"type":"item","item":{"type":"agent_message",'
        '"text":"<lumon-progress>{\\"phase\\":\\"inspecting\\",'
        '\\"message\\":\\"正在检查 Workspace。\\",\\"notify\\":true}'
        '</lumon-progress>"}}'
    )

    assert event is not None
    assert event.kind == "progress"
    assert event.phase == "inspecting"
    assert event.text == "正在检查 Workspace。"
    assert event.notify_requested


def test_codex_tool_uses_argument_vector_and_reads_stdin(tmp_path: Path) -> None:
    fake = tmp_path / "fake-codex"
    fake.write_text(
        "#!/bin/sh\n"
        "cat >/dev/null\n"
        'printf \'%s\\n\' \'{"type":"item","item":{"type":"agent_message","text":"done"}}\'\n',
        encoding="utf-8",
    )
    fake.chmod(0o755)
    tool = CodexTool(binary=str(fake), timeout_seconds=5)

    result = asyncio.run(tool.execute(CodexRequest(tmp_path, "inspect this")))

    assert result.status == "succeeded"
    assert result.final_text == "done"
    assert result.events[0].kind == "message"
    assert tool.build_command(tmp_path)[1:] == (
        "exec",
        "--json",
        "--cd",
        str(tmp_path),
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
    )


def test_codex_tool_attaches_images_before_the_prompt(tmp_path: Path) -> None:
    image = tmp_path / "screen.png"
    image.write_bytes(b"image")
    tool = CodexTool(binary="codex")

    assert tool.build_command(tmp_path, images=(image,))[1:] == (
        "exec",
        "--json",
        "--cd",
        str(tmp_path),
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "--image",
        str(image),
    )


def test_codex_tool_attaches_images_to_a_resumed_prompt(tmp_path: Path) -> None:
    image = tmp_path / "screen.png"
    image.write_bytes(b"image")
    tool = CodexTool(binary="codex")

    assert tool.build_command(tmp_path, "session-1", images=(image,))[1:] == (
        "exec",
        "--json",
        "--cd",
        str(tmp_path),
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "resume",
        "--image",
        str(image),
        "session-1",
        "-",
    )


def test_codex_tool_reads_jsonl_event_larger_than_asyncio_default_limit(
    tmp_path: Path,
) -> None:
    json_line = json.dumps(
        {
            "type": "item",
            "item": {"type": "command_execution", "output": "x" * 100_000},
        }
    )
    output_literal = json.dumps(json_line + "\n")
    fake = tmp_path / "fake-codex"
    fake.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        "sys.stdin.buffer.read()\n"
        f"sys.stdout.write({output_literal})\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    tool = CodexTool(binary=str(fake), timeout_seconds=5)

    result = asyncio.run(tool.execute(CodexRequest(tmp_path, "inspect this")))

    assert result.status == "succeeded"
    assert result.events[0].kind == "command_execution"


def test_codex_tool_resumes_a_native_session(tmp_path: Path) -> None:
    args_file = tmp_path / "args"
    fake = tmp_path / "fake-codex"
    fake.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$@\" > '{args_file}'\n"
        "cat >/dev/null\n"
        'printf \'%s\\n\' \'{"type":"thread.started","thread_id":"thread-1"}\'\n'
        'printf \'%s\\n\' \'{"type":"item","item":{"type":"agent_message","text":"continued"}}\'\n',
        encoding="utf-8",
    )
    fake.chmod(0o755)
    tool = CodexTool(binary=str(fake), timeout_seconds=5)

    result = asyncio.run(
        tool.execute(
            CodexRequest(
                tmp_path,
                "follow-up",
                resume_session_id="thread-1",
            )
        )
    )

    assert result.status == "succeeded"
    assert result.final_text == "continued"
    assert result.agent_session_id == "thread-1"
    assert args_file.read_text(encoding="utf-8").splitlines() == [
        "exec",
        "--json",
        "--cd",
        str(tmp_path),
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "resume",
        "thread-1",
        "-",
    ]


def test_codex_tool_success_does_not_require_final_text_for_flows(tmp_path: Path) -> None:
    fake = tmp_path / "fake-codex"
    fake.write_text(
        "#!/bin/sh\n"
        "cat >/dev/null\n"
        'printf \'%s\\n\' \'{"type":"item","item":{"type":"file_change"}}\'\n',
        encoding="utf-8",
    )
    fake.chmod(0o755)
    tool = CodexTool(binary=str(fake), timeout_seconds=5)

    result = asyncio.run(tool.execute(CodexRequest(tmp_path, "scan this")))

    assert result.status == "succeeded"
    assert result.final_text is None
    assert result.events == (result.events[0],)
    assert result.events[0].kind == "file_change"
