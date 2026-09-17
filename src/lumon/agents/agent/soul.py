"""Load Agent's packaged identity and an optional user-level override."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from lumon.errors import AgentConfigError
from lumon.workspace.registry import UserStateLayout


class SoulLoader:
    """Resolve user-owned Agent instructions before the packaged default."""

    def __init__(self, state_root: Path | None = None, override_path: Path | None = None) -> None:
        layout = UserStateLayout.from_root(state_root)
        self.override_path = (
            override_path or layout.root / "agents" / "agent" / "templates" / "SOUL.md"
        )
        self._legacy_override_paths = (
            (
                layout.root / "agents" / "agent" / "SOUL.md",
                layout.root / "agents" / "mark" / "templates" / "SOUL.md",
                layout.root / "agents" / "mark" / "SOUL.md",
            )
            if override_path is None
            else ()
        )

    def load(self) -> str:
        """Return the user override when present, otherwise the packaged SOUL."""

        for override_path in self._override_paths():
            if override_path.exists():
                return self._read_override(override_path)

        try:
            value = (
                files("lumon.agents.agent.templates")
                .joinpath("SOUL.md")
                .read_text(encoding="utf-8")
            )
        except (ModuleNotFoundError, OSError, UnicodeDecodeError) as exc:
            raise AgentConfigError("Packaged Agent SOUL.md is unavailable.") from exc
        if not value.strip():
            raise AgentConfigError("Packaged Agent SOUL.md is empty.")
        return value

    def _override_paths(self) -> tuple[Path, ...]:
        return (self.override_path, *self._legacy_override_paths)

    @staticmethod
    def _read_override(path: Path) -> str:
        try:
            value = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise AgentConfigError(f"Unable to read Agent SOUL override: {path}") from exc
        if not value.strip():
            raise AgentConfigError(f"Agent SOUL override is empty: {path}")
        return value
