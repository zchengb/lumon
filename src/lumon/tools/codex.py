"""Reusable local Codex execution tool for Lumon flows and Agents."""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from os import X_OK, access
from pathlib import Path
from typing import Literal, cast

from lumon.tools.safety import sanitize_output

CodexEventKind = Literal[
    "session",
    "message",
    "progress",
    "command_execution",
    "file_change",
    "error",
]
CodexEventLifecycle = Literal["started", "completed", "observed"]
CodexExecutionStatus = Literal["succeeded", "failed", "timed_out"]
CodexEventCallback = Callable[["CodexEvent"], Awaitable[None]]


class CodexErrorCode(StrEnum):
    """Stable errors produced by the local Codex process tool."""

    TIMEOUT = "timeout"
    CLI_NOT_FOUND = "cli_not_found"
    START_FAILED = "start_failed"
    EXECUTION_FAILED = "execution_failed"


# Codex JSONL events can include large tool outputs; keep the line buffer
# bounded while allowing records larger than asyncio's 64 KiB default.
_CODEX_STREAM_LIMIT_BYTES = 16 * 1024 * 1024
_CODEX_EVENT_TEXT_LIMIT = 16 * 1024


@dataclass(frozen=True, slots=True)
class CodexRequest:
    """Input required to execute one Codex request in a Workspace."""

    workspace: Path
    prompt: str
    resume_session_id: str | None = None
    images: tuple[Path, ...] = ()


@dataclass(frozen=True, slots=True)
class CodexEvent:
    """A safe, provider-specific event emitted by the Codex JSONL stream."""

    kind: CodexEventKind
    text: str | None = None
    phase: str | None = None
    notify_requested: bool = True
    agent_session_id: str | None = None
    lifecycle: CodexEventLifecycle | None = None
    operation_id: str | None = None
    command: str | None = None
    output: str | None = None
    status: str | None = None
    exit_code: int | None = None


@dataclass(frozen=True, slots=True)
class CodexExecutionResult:
    """The process outcome returned by the Codex tool.

    A successful process may have no ``final_text``. Callers that need a user
    facing answer, such as Agent, apply that policy themselves; file-oriented
    flows can use the successful status without requiring a textual response.
    """

    status: CodexExecutionStatus
    final_text: str | None = None
    events: tuple[CodexEvent, ...] = ()
    error_code: CodexErrorCode | None = None
    return_code: int | None = None
    agent_session_id: str | None = None


class CodexTool:
    """Execute Codex without imposing a caller-specific output policy."""

    provider = "codex"

    def __init__(
        self,
        binary: str | None = None,
        timeout_seconds: float = 900.0,
        environment: Mapping[str, str] | None = None,
        model: str | None = None,
        reasoning_effort: str | None = None,
    ) -> None:
        self.binary = binary or resolve_codex_binary()
        self.timeout_seconds = timeout_seconds
        self.environment = dict(environment) if environment is not None else None
        self.model = model or None
        self.reasoning_effort = reasoning_effort or None

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

    def build_command(
        self,
        workspace: Path,
        resume_session_id: str | None = None,
        *,
        images: tuple[Path, ...] = (),
    ) -> tuple[str, ...]:
        """Return the exact argument vector used for one execution."""

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
        if self.reasoning_effort:
            serialized_effort = json.dumps(self.reasoning_effort)
            command.extend(("--config", f"model_reasoning_effort={serialized_effort}"))
        for image in images:
            command.extend(("--image", str(image)))
        if resume_session_id:
            # ``--cd`` and the other execution options belong to the parent
            # ``exec`` command. They must precede the ``resume`` subcommand;
            # Codex rejects them when they appear after ``resume``.
            command.extend(("resume", resume_session_id, "-"))
        return tuple(command)

    async def execute(
        self,
        request: CodexRequest,
        on_event: CodexEventCallback | None = None,
    ) -> CodexExecutionResult:
        """Execute a request and optionally observe safe stream events."""

        try:
            return await asyncio.wait_for(
                self._execute_process(request, on_event),
                timeout=self.timeout_seconds,
            )
        except TimeoutError:
            return CodexExecutionResult(
                status="timed_out",
                error_code=CodexErrorCode.TIMEOUT,
            )
        except FileNotFoundError:
            return CodexExecutionResult(
                status="failed",
                error_code=CodexErrorCode.CLI_NOT_FOUND,
            )
        except OSError:
            return CodexExecutionResult(
                status="failed",
                error_code=CodexErrorCode.START_FAILED,
            )

    async def _execute_process(
        self,
        request: CodexRequest,
        on_event: CodexEventCallback | None,
    ) -> CodexExecutionResult:
        process: asyncio.subprocess.Process | None = None
        agent_session_id: str | None = None
        try:
            process = await asyncio.create_subprocess_exec(
                *self.build_command(
                    request.workspace,
                    request.resume_session_id,
                    images=request.images,
                ),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=request.workspace,
                env=self.environment,
                limit=_CODEX_STREAM_LIMIT_BYTES,
            )
            assert process.stdin is not None
            assert process.stdout is not None
            assert process.stderr is not None
            process.stdin.write(request.prompt.encode("utf-8"))
            await process.stdin.drain()
            process.stdin.close()
            await process.stdin.wait_closed()

            stderr_task = asyncio.create_task(process.stderr.read())
            events: list[CodexEvent] = []
            final_text: str | None = None
            error_seen = False
            async for raw_line in process.stdout:
                event = parse_codex_line(raw_line)
                if event is None:
                    continue
                events.append(event)
                if event.agent_session_id:
                    agent_session_id = event.agent_session_id
                if event.kind == "message" and event.text:
                    final_text = event.text
                elif event.kind == "error":
                    error_seen = True
                if on_event is not None:
                    await on_event(event)
            await process.wait()
            await stderr_task

            if process.returncode != 0 or error_seen:
                return CodexExecutionResult(
                    status="failed",
                    events=tuple(events),
                    error_code=CodexErrorCode.EXECUTION_FAILED,
                    return_code=process.returncode,
                    agent_session_id=agent_session_id,
                )
            return CodexExecutionResult(
                status="succeeded",
                final_text=final_text,
                events=tuple(events),
                return_code=process.returncode,
                agent_session_id=agent_session_id,
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


def parse_codex_line(raw_line: bytes | str) -> CodexEvent | None:
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
    agent_session_id = _extract_agent_session_id(payload)
    if agent_session_id is None and item_payload is not None:
        agent_session_id = _extract_agent_session_id(item_payload)
    if effective_type in {"thread.started", "session.started", "thread_start", "session_start"}:
        if agent_session_id is None:
            return None
        return CodexEvent("session", agent_session_id=agent_session_id)
    if effective_type in {"lumon_progress", "agent_progress", "progress"}:
        return _progress_event(
            item_payload if item_payload is not None else payload,
            agent_session_id=agent_session_id,
        )
    if effective_type in {"agent_message", "assistant_message", "message", "final"}:
        text = _extract_text(item_payload if item_payload is not None else payload)
        progress = _progress_marker(text, agent_session_id=agent_session_id)
        if progress is not None:
            return progress
        return CodexEvent(
            "message",
            sanitize_output(text) if text else None,
            agent_session_id=agent_session_id,
        )
    if effective_type in {"command_execution", "command", "tool_call"}:
        operation = item_payload if item_payload is not None else payload
        return CodexEvent(
            "command_execution",
            agent_session_id=agent_session_id,
            lifecycle=_event_lifecycle(event_type, operation),
            operation_id=_extract_operation_id(operation),
            command=_event_text(operation, "command"),
            output=_event_text(operation, "aggregated_output", "output", "stdout", "stderr"),
            status=_event_status(operation),
            exit_code=_event_int(operation, "exit_code", "exitCode"),
        )
    if effective_type in {"file_change", "file_changes"}:
        operation = item_payload if item_payload is not None else payload
        return CodexEvent(
            "file_change",
            agent_session_id=agent_session_id,
            lifecycle=_event_lifecycle(event_type, operation),
            operation_id=_extract_operation_id(operation),
        )
    if item_type == "error":
        # Codex can emit advisory item errors while the turn still succeeds.
        # The process exit code and terminal turn event determine execution status.
        return None
    if effective_type in {"error", "turn.failed", "response.failed"}:
        return CodexEvent("error", agent_session_id=agent_session_id)
    return None


_PROGRESS_MARKER = re.compile(
    r"<lumon-progress>\s*(?P<payload>\{.*?\})\s*</lumon-progress>",
    re.IGNORECASE | re.DOTALL,
)


def _progress_marker(
    text: str | None,
    *,
    agent_session_id: str | None = None,
) -> CodexEvent | None:
    """Extract one explicit progress marker emitted by the Agent."""

    if not text:
        return None
    match = _PROGRESS_MARKER.fullmatch(text.strip())
    if match is None:
        return None
    try:
        payload = json.loads(match.group("payload"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return _progress_event(
        cast(dict[str, object], payload),
        agent_session_id=agent_session_id,
    )


def _progress_event(
    payload: Mapping[str, object],
    *,
    agent_session_id: str | None = None,
) -> CodexEvent | None:
    phase = payload.get("phase")
    message = payload.get("message", payload.get("text"))
    notify_requested = payload.get("notify", True)
    if not isinstance(phase, str) or not isinstance(message, str):
        return None
    if not isinstance(notify_requested, bool):
        return None
    phase = phase.strip()
    message = message.strip()
    if not phase or not message:
        return None
    return CodexEvent(
        kind="progress",
        text=sanitize_output(message),
        phase=phase,
        notify_requested=notify_requested,
        agent_session_id=agent_session_id,
    )


def _extract_agent_session_id(payload: Mapping[str, object]) -> str | None:
    """Extract a native Codex thread ID without exposing arbitrary payloads."""

    for key in ("thread_id", "session_id"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    thread = payload.get("thread")
    if isinstance(thread, dict):
        nested = cast(dict[str, object], thread)
        for key in ("id", "thread_id", "session_id"):
            value = nested.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _event_lifecycle(
    event_type: str,
    payload: Mapping[str, object],
) -> CodexEventLifecycle:
    if event_type.endswith(".started") or event_type.endswith(".start"):
        return "started"
    if event_type.endswith(".completed") or event_type.endswith(".complete"):
        return "completed"
    status = _event_status(payload)
    if status in {"in_progress", "running", "started"}:
        return "started"
    if status in {"completed", "failed", "cancelled", "canceled", "succeeded"}:
        return "completed"
    return "observed"


def _extract_operation_id(payload: Mapping[str, object]) -> str | None:
    for key in ("id", "item_id", "call_id", "command_id"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _event_text(payload: Mapping[str, object], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        text = _extract_text(value)
        if text:
            return _bounded_event_text(sanitize_output(text))
    return None


def _event_status(payload: Mapping[str, object]) -> str | None:
    value = payload.get("status")
    if not isinstance(value, str) or not value.strip():
        return None
    return _bounded_event_text(sanitize_output(value.strip()), limit=80)


def _event_int(payload: Mapping[str, object], *keys: str) -> int | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def _bounded_event_text(value: str, *, limit: int = _CODEX_EVENT_TEXT_LIMIT) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"


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
