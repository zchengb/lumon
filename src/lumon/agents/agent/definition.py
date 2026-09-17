"""The small, stable public identity of Agent."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgentDefinition:
    """Descriptive metadata used by diagnostics and future integrations."""

    name: str = "Agent"
    role: str = "Workspace Agent"
    channel: str = "Feishu"


AGENT_DEFINITION = AgentDefinition()
