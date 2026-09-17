"""Typed values used by Workspace flow discovery."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FlowBrief:
    """The bounded ID, brief, and detail locator Mark receives."""

    flow_id: str
    brief: str
    path: str


@dataclass(frozen=True, slots=True)
class FlowDefinition:
    """One validated, user-authored Markdown flow."""

    flow_id: str
    name: str
    enabled: bool
    brief: str
    path: Path
    content: str
    body: str

    @property
    def flow_brief(self) -> FlowBrief:
        """Return the prompt-safe summary for this flow."""

        return FlowBrief(
            flow_id=self.flow_id,
            brief=self.brief,
            path=self.path.as_posix(),
        )


@dataclass(frozen=True, slots=True)
class FlowDiagnostic:
    """A safe validation result for a flow file that cannot be loaded."""

    path: Path
    message: str


@dataclass(frozen=True, slots=True)
class FlowCatalogSnapshot:
    """All valid flow definitions and diagnostics found in a Workspace."""

    definitions: tuple[FlowDefinition, ...] = ()
    diagnostics: tuple[FlowDiagnostic, ...] = ()

    @property
    def enabled(self) -> tuple[FlowDefinition, ...]:
        """Return enabled definitions in deterministic order."""

        return tuple(item for item in self.definitions if item.enabled)

    @property
    def briefs(self) -> tuple[FlowBrief, ...]:
        """Return enabled flow briefs for prompt construction."""

        return tuple(item.flow_brief for item in self.enabled)
