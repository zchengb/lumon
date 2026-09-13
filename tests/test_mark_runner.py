"""Tests for Mark's conversational policy around the shared Codex tool."""

from __future__ import annotations

import asyncio
from pathlib import Path

from lumon.agents.mark.model import AgentErrorCode
from lumon.agents.mark.runner import CodexAgentRunner
from lumon.tools.codex import CodexTool


def test_mark_requires_final_text_even_when_the_shared_tool_succeeds(tmp_path: Path) -> None:
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
