"""The provider-neutral seam for local Agent CLI execution."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from lumon.agents.mark.model import AgentErrorCode, AgentResult
from lumon.errors import AgentConfigError
from lumon.tools.codex import (
    CodexErrorCode,
    CodexEvent,
    CodexRequest,
    CodexTool,
)

if TYPE_CHECKING:
    from lumon.agents.mark.config import MarkAgentConfig

ProgressCallback = Callable[[str], Awaitable[None]]


class CodexAgentRunner:
    """Adapt the shared Codex tool to Mark's conversational Agent contract."""

    provider = "codex"
    display_name = "Codex"

    def __init__(self, tool: CodexTool | None = None, model: str | None = None) -> None:
        self.tool = tool or CodexTool(model=model)

    @property
    def executable(self) -> str:
        """Return the Codex executable used by Mark."""

        return self.tool.executable

    def is_available(self) -> bool:
        """Return whether Mark can launch the shared Codex tool."""

        return self.tool.is_available()

    def is_authenticated(self) -> bool:
        """Return whether the local Codex session is ready for Mark."""

        return self.tool.is_authenticated()

    async def run(
        self,
        workspace: Path,
        prompt: str,
        on_progress: ProgressCallback | None = None,
    ) -> AgentResult:
        """Run Codex and apply Mark's requirement for a replyable final text."""

        progress: list[str] = []

        async def observe(event: CodexEvent) -> None:
            label = _progress_label(event)
            if label is None:
                return
            progress.append(label)
            if on_progress is not None:
                await on_progress(label)

        result = await self.tool.execute(
            CodexRequest(workspace=workspace, prompt=prompt),
            on_event=observe,
        )
        if result.status == "timed_out":
            return AgentResult(
                status="timed_out",
                progress=tuple(progress),
                error_code=AgentErrorCode.TIMEOUT,
            )
        if result.status == "failed":
            return AgentResult(
                status="failed",
                progress=tuple(progress),
                error_code=_map_error_code(result.error_code),
                return_code=result.return_code,
            )
        if not result.final_text:
            return AgentResult(
                status="failed",
                progress=tuple(progress),
                error_code=AgentErrorCode.EMPTY_RESULT,
                return_code=result.return_code,
            )
        return AgentResult(
            status="succeeded",
            final_text=result.final_text,
            progress=tuple(progress),
            return_code=result.return_code,
        )


class AgentRunner(Protocol):
    """Small interface used by Mark to run one request through an Agent CLI.

    Implementations own provider-specific command construction, event parsing,
    authentication checks, and error translation. Mark only depends on this
    interface and the provider-neutral :class:`AgentResult` contract.
    """

    @property
    def provider(self) -> str:
        """Return the stable provider identifier used for diagnostics and runs."""

        ...

    @property
    def display_name(self) -> str:
        """Return the human-readable provider name used in user messages."""

        ...

    @property
    def executable(self) -> str:
        """Return the resolved executable path or command name."""

        ...

    def is_available(self) -> bool:
        """Return whether the provider executable can be launched locally."""

        ...

    def is_authenticated(self) -> bool:
        """Return whether the local provider session is ready to use."""

        ...

    async def run(
        self,
        workspace: Path,
        prompt: str,
        on_progress: ProgressCallback | None = None,
    ) -> AgentResult:
        """Run one bounded request and return safe progress and final output."""

        ...


def create_agent_runner(config: MarkAgentConfig | None = None) -> AgentRunner:
    """Create the configured runner without leaking provider details to Mark.

    Codex is the only supported provider today. Keeping selection here makes
    adding another concrete runner a localized change instead of a service-wide
    conditional.
    """

    provider = config.agent_provider if config is not None else "codex"
    if provider == "codex":
        model = config.agent_model if config is not None else None
        return CodexAgentRunner(model=model)
    raise AgentConfigError(f"Unsupported Mark Agent provider: {provider}")


def _progress_label(event: CodexEvent) -> str | None:
    if event.kind == "command_execution":
        return "Codex 正在执行 Workspace 操作…"
    if event.kind == "file_change":
        return "Codex 正在检查 Workspace 文件…"
    return None


def _map_error_code(error_code: CodexErrorCode | None) -> AgentErrorCode:
    if error_code == CodexErrorCode.TIMEOUT:
        return AgentErrorCode.TIMEOUT
    if error_code == CodexErrorCode.CLI_NOT_FOUND:
        return AgentErrorCode.CLI_NOT_FOUND
    if error_code == CodexErrorCode.START_FAILED:
        return AgentErrorCode.START_FAILED
    return AgentErrorCode.EXECUTION_FAILED
