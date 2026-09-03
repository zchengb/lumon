"""Read-only environment and Workspace diagnostics."""

from __future__ import annotations

import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from lumon.workspace.layout import WorkspaceLayout
from lumon.workspace.manifest import load_manifest


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    """One diagnostic with a stable name and human detail."""

    name: str
    ok: bool
    detail: str


@dataclass(frozen=True, slots=True)
class DoctorReport:
    """The complete read-only diagnostic report."""

    checks: tuple[DoctorCheck, ...]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    def to_dict(self) -> dict[str, object]:
        return {"ok": self.ok, "checks": [asdict(check) for check in self.checks]}


class Doctor:
    """Inspect the package runtime, Skills directory, and optional Workspace."""

    def __init__(self, skills_root: Path | None = None) -> None:
        self.skills_root = (
            (skills_root or (Path.home() / ".agents" / "skills")).expanduser().resolve()
        )

    def inspect(self, workspace: Path | None = None) -> DoctorReport:
        checks = [
            DoctorCheck(
                "python_version",
                sys.version_info[:2] == (3, 12),
                f"Python {sys.version_info.major}.{sys.version_info.minor}",
            ),
            self._skills_check(),
        ]
        if workspace is None:
            checks.append(DoctorCheck("workspace", True, "not selected"))
        else:
            checks.append(self._workspace_check(workspace))
        return DoctorReport(tuple(checks))

    def _skills_check(self) -> DoctorCheck:
        if self.skills_root.exists():
            ok = self.skills_root.is_dir() and os.access(self.skills_root, os.W_OK)
            return DoctorCheck("global_skills", ok, str(self.skills_root))
        parent = _nearest_existing_parent(self.skills_root.parent)
        ok = parent.is_dir() and os.access(parent, os.W_OK)
        detail = f"will create {self.skills_root}" if ok else f"not writable: {self.skills_root}"
        return DoctorCheck("global_skills", ok, detail)

    def _workspace_check(self, workspace: Path) -> DoctorCheck:
        layout = WorkspaceLayout.from_root(workspace)
        if not layout.root.is_dir():
            return DoctorCheck("workspace", False, f"not a directory: {layout.root}")
        if not layout.manifest.is_file():
            return DoctorCheck("workspace", False, f"manifest missing: {layout.manifest}")
        try:
            load_manifest(layout.manifest)
        except Exception as exc:
            return DoctorCheck("workspace", False, str(exc))
        return DoctorCheck("workspace", True, str(layout.root))


def _nearest_existing_parent(path: Path) -> Path:
    current = path
    while not current.exists() and current != current.parent:
        current = current.parent
    return current
