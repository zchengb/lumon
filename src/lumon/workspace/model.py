"""Small typed values shared by the Workspace modules."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

InitStatus = Literal["initialized", "already_initialized", "updated", "dry_run"]
RepositoryResultStatus = Literal["cloned", "reused", "will_clone", "will_reuse"]


@dataclass(frozen=True, slots=True)
class RepositorySpec:
    """One user-provided Repository clone URL and its derived name."""

    name: str
    clone_url: str


@dataclass(frozen=True, slots=True)
class RepositoryRecord:
    """The inspectable Repository metadata persisted in a Workspace."""

    name: str
    url: str
    path: str
    branch: str
    revision: str


@dataclass(frozen=True, slots=True)
class RepositoryResult:
    """The outcome of preparing one Repository for initialization."""

    name: str
    path: Path
    status: RepositoryResultStatus
    branch: str | None = None
    revision: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Convert the result at the CLI output seam."""

        return {
            "name": self.name,
            "path": str(self.path),
            "status": self.status,
            "branch": self.branch,
            "revision": self.revision,
        }


@dataclass(frozen=True, slots=True)
class InitRequest:
    """Validated intent to initialize one explicit Workspace path."""

    target: Path
    name: str | None = None
    repositories: tuple[RepositorySpec, ...] = ()
    dry_run: bool = False


@dataclass(frozen=True, slots=True)
class InitResult:
    """The observable result of one initialization attempt."""

    status: InitStatus
    workspace: Path
    created_paths: tuple[Path, ...] = ()
    planned_paths: tuple[Path, ...] = ()
    installed_skills: tuple[str, ...] = ()
    skipped_skills: tuple[str, ...] = ()
    planned_skills: tuple[str, ...] = ()
    repositories: tuple[RepositoryResult, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Convert the result at the CLI output seam."""

        value = asdict(self)
        value["workspace"] = str(value["workspace"])
        for key in ("created_paths", "planned_paths"):
            value[key] = [str(path) for path in value[key]]
        for key in ("installed_skills", "skipped_skills", "planned_skills", "warnings"):
            value[key] = list(value[key])
        value["repositories"] = [repository.to_dict() for repository in self.repositories]
        return value
