from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


FilesystemMode = Literal["none", "workspace_read", "worktree_rw"]


@dataclass(frozen=True)
class AgentCapabilities:
    actions: tuple[str, ...] = ()
    read_scopes: tuple[str, ...] = ()
    filesystem_mode: FilesystemMode = "workspace_read"
    network_profile: str = "allow"
    secret_profile: str = "isolated"
    # Legacy fields kept for gradual migration / tests.
    direct_workspace_write: bool = False
    allowed_workflows: tuple[str, ...] = ()
    allowed_mutations: tuple[str, ...] = ()
    external_side_effects: tuple[str, ...] = ()

    def allows(self, action: str) -> bool:
        return str(action or "").strip() in set(self.actions)

    @property
    def harness_mode(self) -> str:
        """The Host mode is shared; role capabilities never widen its seam."""
        return "unshackled"
