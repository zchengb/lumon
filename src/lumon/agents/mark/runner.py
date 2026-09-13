"""The provider-neutral seam for local Agent CLI execution."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from lumon.agents.mark.model import AgentResult
from lumon.errors import AgentConfigError

if TYPE_CHECKING:
    from lumon.agents.mark.config import MarkAgentConfig

ProgressCallback = Callable[[str], Awaitable[None]]


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

    from lumon.agents.mark.codex import CodexRunner

    provider = config.agent_provider if config is not None else "codex"
    if provider == "codex":
        model = config.agent_model if config is not None else None
        return CodexRunner(model=model)
    raise AgentConfigError(f"Unsupported Mark Agent provider: {provider}")
