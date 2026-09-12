"""The small, stable public identity of Mark."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MarkDefinition:
    """Descriptive metadata used by diagnostics and future integrations."""

    name: str = "Mark"
    role: str = "Workspace Agent"
    channel: str = "Feishu"


MARK_DEFINITION = MarkDefinition()
