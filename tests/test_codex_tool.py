"""Tests for the reusable local Codex execution tool."""

from __future__ import annotations

import asyncio
from pathlib import Path

from lumon.tools.codex import CodexRequest, CodexTool, parse_codex_line
from lumon.tools.safety import sanitize_output


def test_codex_jsonl_parser_is_provider_specific_but_not_mark_specific() -> None:
    final = parse_codex_line('{"type":"item","item":{"type":"agent_message","text":"done"}}')
    command = parse_codex_line('{"type":"item","item":{"type":"command_execution"}}')
    file_change = parse_codex_line('{"type":"item","item":{"type":"file_change"}}')

    assert final is not None and final.kind == "message" and final.text == "done"
    assert command is not None and command.kind == "command_execution"
    assert file_change is not None and file_change.kind == "file_change"
    assert "执行 Workspace" not in str(command.text)
    assert "[REDACTED]" in sanitize_output(
        "app_secret=secret-value https://open.feishu.cn/open-apis/bot/v2/hook/token"
    )


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
