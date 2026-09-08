"""The canonical v1 Workspace layout."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

CONTROL_DIR_NAME = "lumon"


@dataclass(frozen=True, slots=True)
class WorkspaceLayout:
    """Resolve every v1 Workspace path from one root."""

    root: Path

    @classmethod
    def from_root(cls, root: Path) -> WorkspaceLayout:
        """Return a normalized layout without touching the filesystem."""

        return cls(root.expanduser().resolve())

    @property
    def control_dir(self) -> Path:
        return self.root / CONTROL_DIR_NAME

    @property
    def workspace_config(self) -> Path:
        return self.control_dir / "workspace.toml"

    @property
    def manifest(self) -> Path:
        return self.control_dir / "manifest.json"

    @property
    def repositories_dir(self) -> Path:
        return self.root / "repos"

    @property
    def readme(self) -> Path:
        return self.root / "README.md"

    @property
    def agents_instructions(self) -> Path:
        return self.root / "AGENTS.md"

    @property
    def gitignore(self) -> Path:
        return self.root / ".gitignore"

    @property
    def runtime_directories(self) -> tuple[Path, ...]:
        return tuple(self.control_dir / name for name in ("runs", "artifacts", "logs", "tmp"))

    @property
    def generated_files(self) -> tuple[Path, ...]:
        return (
            self.readme,
            self.agents_instructions,
            self.gitignore,
            self.workspace_config,
            self.manifest,
        )

    @property
    def generated_paths(self) -> tuple[Path, ...]:
        return (self.control_dir, *self.runtime_directories, *self.generated_files)
