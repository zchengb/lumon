"""Typed values used by Workspace capability discovery."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CapabilityBrief:
    """The bounded ID, brief, and detail locator Agent receives."""

    capability_id: str
    brief: str
    path: str


@dataclass(frozen=True, slots=True)
class CapabilityDefinition:
    """One validated, user-authored Markdown capability."""

    capability_id: str
    name: str
    enabled: bool
    brief: str
    path: Path
    content: str
    body: str

    @property
    def capability_brief(self) -> CapabilityBrief:
        """Return the prompt-safe summary for this capability."""

        return CapabilityBrief(
            capability_id=self.capability_id,
            brief=self.brief,
            path=self.path.as_posix(),
        )


@dataclass(frozen=True, slots=True)
class CapabilityDiagnostic:
    """A safe validation result for a capability file that cannot be loaded."""

    path: Path
    message: str


@dataclass(frozen=True, slots=True)
class CapabilityCatalogSnapshot:
    """All valid capability definitions and diagnostics found in a Workspace."""

    definitions: tuple[CapabilityDefinition, ...] = ()
    diagnostics: tuple[CapabilityDiagnostic, ...] = ()

    @property
    def enabled(self) -> tuple[CapabilityDefinition, ...]:
        """Return enabled definitions in deterministic order."""

        return tuple(item for item in self.definitions if item.enabled)

    @property
    def briefs(self) -> tuple[CapabilityBrief, ...]:
        """Return enabled capability briefs for prompt construction."""

        return tuple(item.capability_brief for item in self.enabled)
