"""Discover model choices through the same local Codex CLI used for execution."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from lumon.agents.agent.config import AGENT_REASONING_EFFORT_PATTERN
from lumon.errors import AgentRuntimeError
from lumon.tools.codex import resolve_codex_binary
from lumon.version import __version__


@dataclass(frozen=True, slots=True)
class CodexModel:
    """Display-safe model capabilities, without account or authentication data."""

    model: str
    display_name: str
    description: str
    default_reasoning_effort: str
    supported_reasoning_efforts: tuple[str, ...]


class _Reply(BaseModel):
    model_config = ConfigDict(strict=True)

    id: int | str | None = None
    result: dict[str, object] | None = None
    error: object | None = None


class _Effort(BaseModel):
    model_config = ConfigDict(strict=True)

    reasoning_effort: str = Field(
        alias="reasoningEffort", pattern=AGENT_REASONING_EFFORT_PATTERN, max_length=32
    )


class _Model(BaseModel):
    model_config = ConfigDict(strict=True)

    model: str = Field(pattern=r"^\S+$", max_length=256)
    display_name: str = Field(alias="displayName", min_length=1, max_length=256)
    description: str = Field(default="", max_length=4096)
    hidden: bool = False
    default_reasoning_effort: str = Field(
        alias="defaultReasoningEffort", pattern=AGENT_REASONING_EFFORT_PATTERN, max_length=32
    )
    supported_reasoning_efforts: list[_Effort] = Field(
        alias="supportedReasoningEfforts", min_length=1, max_length=32
    )


class _Page(BaseModel):
    model_config = ConfigDict(strict=True)

    data: list[_Model] = Field(max_length=1000)
    next_cursor: str | None = Field(default=None, alias="nextCursor", max_length=4096)


class CodexModelCatalog:
    """Read a bounded, paginated catalog without starting an Agent turn."""

    def __init__(
        self,
        binary: str | None = None,
        *,
        timeout_seconds: float = 20,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        self.binary = binary or resolve_codex_binary()
        self.timeout_seconds = timeout_seconds
        self.environment = dict(environment) if environment is not None else None

    async def list_models(self) -> tuple[CodexModel, ...]:
        """Query Codex's current catalog, keeping diagnostics and tokens private."""

        try:
            return await asyncio.wait_for(self._discover(), timeout=self.timeout_seconds)
        except TimeoutError as exc:
            raise AgentRuntimeError(
                "Codex model discovery timed out. Try refreshing again."
            ) from exc
        except OSError as exc:
            raise AgentRuntimeError(
                "Could not start Codex model discovery. Check the local Codex installation."
            ) from exc
        except (ValidationError, ValueError) as exc:
            raise AgentRuntimeError(
                "Codex returned an invalid model catalog. Update Codex and try again."
            ) from exc

    async def _discover(self) -> tuple[CodexModel, ...]:
        process = await asyncio.create_subprocess_exec(
            self.binary,
            "app-server",
            "--listen",
            "stdio://",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env=self.environment,
            limit=1024 * 1024,
        )
        try:
            await _request(
                process,
                0,
                "initialize",
                {"clientInfo": {"name": "lumon", "title": "Lumon", "version": __version__}},
            )
            assert process.stdin is not None
            process.stdin.write(b'{"method":"initialized"}\n')
            await process.stdin.drain()
            return await _read_models(process)
        finally:
            if process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
            await process.wait()


async def _request(
    process: asyncio.subprocess.Process,
    request_id: int,
    method: str,
    params: dict[str, object],
) -> dict[str, object]:
    assert process.stdin is not None and process.stdout is not None
    request = {"id": request_id, "method": method, "params": params}
    process.stdin.write((json.dumps(request) + "\n").encode("utf-8"))
    await process.stdin.drain()
    while raw_line := await process.stdout.readline():
        reply = _Reply.model_validate_json(raw_line)
        if reply.id != request_id:
            continue
        if reply.error is not None or reply.result is None:
            raise AgentRuntimeError(
                "Codex model discovery failed. Check Codex login and connectivity, then refresh."
            )
        return reply.result
    raise AgentRuntimeError("Codex closed model discovery before returning a catalog.")


async def _read_models(process: asyncio.subprocess.Process) -> tuple[CodexModel, ...]:
    models: dict[str, CodexModel] = {}
    cursor: str | None = None
    seen_cursors: set[str] = set()
    for page_number in range(1, 21):
        response = await _request(
            process,
            page_number,
            "model/list",
            {"limit": 100, "includeHidden": False, "cursor": cursor},
        )
        page = _Page.model_validate(response)
        for model in page.data:
            if model.hidden:
                continue
            efforts = tuple(option.reasoning_effort for option in model.supported_reasoning_efforts)
            if model.default_reasoning_effort not in efforts:
                raise ValueError("Invalid model reasoning default.")
            models.setdefault(
                model.model,
                CodexModel(
                    model=model.model,
                    display_name=model.display_name,
                    description=model.description,
                    default_reasoning_effort=model.default_reasoning_effort,
                    supported_reasoning_efforts=efforts,
                ),
            )
        if page.next_cursor is None:
            return tuple(models.values())
        if page.next_cursor in seen_cursors:
            break
        seen_cursors.add(page.next_cursor)
        cursor = page.next_cursor
    raise AgentRuntimeError("Codex model discovery returned too many or repeated catalog pages.")
