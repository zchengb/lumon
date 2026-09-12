"""Load Mark's packaged identity and an optional user-level override."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from lumon.errors import AgentConfigError
from lumon.workspace.registry import UserStateLayout


class MarkSoulLoader:
    """Resolve user-owned Mark instructions before the packaged default."""

    def __init__(self, state_root: Path | None = None, override_path: Path | None = None) -> None:
        layout = UserStateLayout.from_root(state_root)
        self.override_path = override_path or layout.root / "agents" / "mark" / "SOUL.md"

    def load(self) -> str:
        """Return the user override when present, otherwise the packaged SOUL."""

        if self.override_path.exists():
            try:
                value = self.override_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise AgentConfigError(
                    f"Unable to read Mark SOUL override: {self.override_path}"
                ) from exc
            if not value.strip():
                raise AgentConfigError(f"Mark SOUL override is empty: {self.override_path}")
            return value

        try:
            value = files("lumon.agents.mark").joinpath("SOUL.md").read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise AgentConfigError("Packaged Mark SOUL.md is unavailable.") from exc
        if not value.strip():
            raise AgentConfigError("Packaged Mark SOUL.md is empty.")
        return value
