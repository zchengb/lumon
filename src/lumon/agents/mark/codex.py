"""Run the local Codex CLI and reduce JSONL events to safe typed results."""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from os import X_OK, access
from pathlib import Path
from typing import Literal, cast

from lumon.agents.mark.model import AgentErrorCode, AgentResult
from lumon.agents.mark.runner import ProgressCallback
from lumon.agents.mark.safety import sanitize_output

CodexEventKind = Literal["final", "progress", "error"]


@dataclass(frozen=True, slots=True)
class ParsedCodexEvent:
    """The deliberately small event shape consumed by the runner."""

    kind: CodexEventKind
    text: str | None = None


class CodexRunner:
    """Execute one isolated full-access Codex turn in a Workspace."""

    provider = "codex"
    display_name = "Codex"

    def __init__(
        self,
        binary: str | None = None,
        timeout_seconds: float = 900.0,
        environment: Mapping[str, str] | None = None,
        model: str | None = None,
    ) -> None:
        self.binary = binary or resolve_codex_binary()
        self.timeout_seconds = timeout_seconds
        self.environment = dict(environment) if environment is not None else None
        self.model = model or None

    @property
    def executable(self) -> str:
        """Return the resolved Codex executable for diagnostics."""

        return self.binary

    def is_available(self) -> bool:
        """Return whether the configured Codex executable is runnable."""

        path = Path(self.executable)
        return path.is_file() and access(path, X_OK)

    def is_authenticated(self) -> bool:
        """Return whether the local Codex session reports a successful login."""

        try:
            result = subprocess.run(
                [self.executable, "login", "status"],
                check=False,
                capture_output=True,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return result.returncode == 0

    def build_command(self, workspace: Path) -> tuple[str, ...]:
        """Return the exact argument vector used for one Codex execution."""

        command = [
            self.binary,
            "exec",
            "--json",
            "--cd",
            str(workspace),
            "--skip-git-repo-check",
            "--dangerously-bypass-approvals-and-sandbox",
        ]
        if self.model:
            command.extend(("--model", self.model))
        return tuple(command)

    async def run(
        self,
        workspace: Path,
        prompt: str,
        on_progress: ProgressCallback | None = None,
    ) -> AgentResult:
        """Run Codex with a bounded timeout and no shell interpolation."""

        try:
            return await asyncio.wait_for(
                self._run_process(workspace, prompt, on_progress),
                timeout=self.timeout_seconds,
            )
        except TimeoutError:
            return AgentResult(status="timed_out", error_code=AgentErrorCode.TIMEOUT)
        except FileNotFoundError:
            return AgentResult(status="failed", error_code=AgentErrorCode.CLI_NOT_FOUND)
        except OSError:
            return AgentResult(status="failed", error_code=AgentErrorCode.START_FAILED)

    async def _run_process(
        self,
        workspace: Path,
        prompt: str,
        on_progress: ProgressCallback | None,
    ) -> AgentResult:
        process: asyncio.subprocess.Process | None = None
        try:
            process = await asyncio.create_subprocess_exec(
                *self.build_command(workspace),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace,
                env=self.environment,
            )
            assert process.stdin is not None
            assert process.stdout is not None
            assert process.stderr is not None
            process.stdin.write(prompt.encode("utf-8"))
            await process.stdin.drain()
            process.stdin.close()
            await process.stdin.wait_closed()

            stderr_task = asyncio.create_task(process.stderr.read())
            progress: list[str] = []
            final_text: str | None = None
            error_seen = False
            async for raw_line in process.stdout:
                event = parse_codex_line(raw_line)
                if event is None:
                    continue
                if event.kind == "final" and event.text:
                    final_text = event.text
                elif event.kind == "progress" and event.text:
                    progress.append(event.text)
                    if on_progress is not None:
                        await on_progress(event.text)
                elif event.kind == "error":
                    error_seen = True
            await process.wait()
            await stderr_task

            if process.returncode != 0 or error_seen:
                return AgentResult(
                    status="failed",
                    progress=tuple(progress),
                    error_code=AgentErrorCode.EXECUTION_FAILED,
                    return_code=process.returncode,
                )
            if not final_text:
                return AgentResult(
                    status="failed",
                    progress=tuple(progress),
                    error_code=AgentErrorCode.EMPTY_RESULT,
                    return_code=process.returncode,
                )
            return AgentResult(
                status="succeeded",
                final_text=sanitize_output(final_text),
                progress=tuple(progress),
                return_code=process.returncode,
            )
        except asyncio.CancelledError:
            if process is not None and process.returncode is None:
                process.kill()
                await process.wait()
            raise


def resolve_codex_binary() -> str:
    """Find Codex using PATH first and the standard local install fallback."""

    located = shutil.which("codex")
    if located:
        return located
    local = Path.home() / ".local" / "bin" / "codex"
    return str(local)


def parse_codex_line(raw_line: bytes | str) -> ParsedCodexEvent | None:
    """Parse one Codex JSONL line without exposing arbitrary event payloads."""

    try:
        value = json.loads(raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict):
        return None

    payload = cast(dict[str, object], value)
    event_type = str(payload.get("type", ""))
    item: object = payload.get("item")
    item_payload = cast(dict[str, object], item) if isinstance(item, dict) else None
    item_type = str(item_payload.get("type", "")) if item_payload is not None else ""
    effective_type = item_type or event_type
    if effective_type in {"agent_message", "assistant_message", "message", "final"}:
        text = _extract_text(item_payload if item_payload is not None else payload)
        return ParsedCodexEvent("final", sanitize_output(text) if text else None)
    if effective_type in {
        "command_execution",
        "command",
        "file_change",
        "file_changes",
        "tool_call",
    }:
        return ParsedCodexEvent("progress", _progress_label(effective_type))
    if effective_type in {"error", "turn.failed", "response.failed"}:
        return ParsedCodexEvent("error")
    return None


def _extract_text(value: object) -> str | None:
    if isinstance(value, dict):
        payload = cast(dict[str, object], value)
        for key in ("text", "message", "content", "output"):
            candidate = payload.get(key)
            text = _extract_text(candidate)
            if text:
                return text
        return None
    if isinstance(value, list):
        parts = [_extract_text(item) for item in cast(list[object], value)]
        text = "".join(part for part in parts if part)
        return text or None
    if isinstance(value, str):
        return value.strip() or None
    return None


def _progress_label(event_type: str) -> str:
    if event_type in {"command_execution", "command", "tool_call"}:
        return "Codex 正在执行 Workspace 操作…"
    if event_type in {"file_change", "file_changes"}:
        return "Codex 正在检查 Workspace 文件…"
    return "Codex 正在处理 Workspace…"
