"""Small typed values shared by the Workspace modules."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

InitStatus = Literal["initialized", "already_initialized", "dry_run"]


@dataclass(frozen=True, slots=True)
class InitRequest:
    """Validated intent to initialize one explicit Workspace path."""

    target: Path
    name: str | None = None
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
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Convert the result at the CLI output seam."""

        value = asdict(self)
        value["workspace"] = str(value["workspace"])
        for key in ("created_paths", "planned_paths"):
            value[key] = [str(path) for path in value[key]]
        for key in ("installed_skills", "skipped_skills", "planned_skills", "warnings"):
            value[key] = list(value[key])
        return value
