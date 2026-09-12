"""Tests for the local Codex JSONL runner."""

from __future__ import annotations

import asyncio
from pathlib import Path

from lumon.agents.mark.codex import CodexRunner, parse_codex_line, sanitize_output


def test_codex_jsonl_parser_exposes_final_and_safe_progress() -> None:
    final = parse_codex_line('{"type":"item","item":{"type":"agent_message","text":"done"}}')
    progress = parse_codex_line('{"type":"item","item":{"type":"command_execution"}}')

    assert final is not None and final.kind == "final" and final.text == "done"
    assert progress is not None and progress.kind == "progress"
    assert "执行 Workspace" in (progress.text or "")
    assert "[REDACTED]" in sanitize_output(
        "app_secret=secret-value https://open.feishu.cn/open-apis/bot/v2/hook/token"
    )


def test_codex_runner_uses_argument_vector_and_reads_stdin(tmp_path: Path) -> None:
    fake = tmp_path / "fake-codex"
    fake.write_text(
        "#!/bin/sh\n"
        "cat >/dev/null\n"
        'printf \'%s\\n\' \'{"type":"item","item":{"type":"agent_message","text":"done"}}\'\n',
        encoding="utf-8",
    )
    fake.chmod(0o755)
    runner = CodexRunner(binary=str(fake), timeout_seconds=5)

    result = asyncio.run(runner.run(tmp_path, "inspect this"))

    assert result.status == "succeeded"
    assert result.final_text == "done"
    assert runner.build_command(tmp_path)[1:] == (
        "exec",
        "--json",
        "--cd",
        str(tmp_path),
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
    )
