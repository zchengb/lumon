"""Install bundled Skills into the user's global Agent directory."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from importlib.resources import as_file
from pathlib import Path

from lumon.errors import SkillInstallError
from lumon.skills.catalog import SkillCatalog


@dataclass(frozen=True, slots=True)
class SkillPreview:
    """One non-mutating installation decision."""

    name: str
    target: Path
    action: str


@dataclass(slots=True)
class SkillInstallResult:
    """Results and rollback information for one install transaction."""

    installed: tuple[str, ...]
    skipped_existing: tuple[str, ...]
    created_paths: tuple[Path, ...]
    skills_root: Path | None = None
    created_root: bool = False

    def rollback(self) -> None:
        """Remove only Skill directories created by this transaction."""

        for path in reversed(self.created_paths):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        if (
            self.created_root
            and self.skills_root is not None
            and self.skills_root.is_dir()
            and not any(self.skills_root.iterdir())
        ):
            self.skills_root.rmdir()


class SkillInstaller:
    """Install missing bundled Skills without overwriting existing paths."""

    def __init__(
        self,
        skills_root: Path | None = None,
        catalog: SkillCatalog | None = None,
    ) -> None:
        self.skills_root = (
            (skills_root or (Path.home() / ".agents" / "skills")).expanduser().resolve()
        )
        self.catalog = catalog or SkillCatalog()

    def preview(self) -> tuple[SkillPreview, ...]:
        """Plan installation without creating the global directory."""

        return tuple(
            SkillPreview(
                name=name,
                target=self.skills_root / name,
                action="skipped_existing" if (self.skills_root / name).exists() else "will_install",
            )
            for name in self.catalog.names()
        )

    def install(self) -> SkillInstallResult:
        """Install missing Skills and return a transaction that can roll back."""

        installed: list[str] = []
        skipped: list[str] = []
        created_paths: list[Path] = []
        created_root = False

        try:
            previews = self.preview()
            missing = [item for item in previews if item.action == "will_install"]
            if missing:
                root_existed = self.skills_root.exists()
                try:
                    self.skills_root.mkdir(parents=True, exist_ok=True)
                except OSError as exc:
                    raise SkillInstallError(
                        f"Global Skills directory is not writable: {self.skills_root}"
                    ) from exc
                created_root = not root_existed

            for item in missing:
                target = item.target
                try:
                    target.mkdir()
                except FileExistsError:
                    skipped.append(item.name)
                    continue

                created_paths.append(target)
                try:
                    source = self.catalog.source(item.name)
                    with as_file(source) as source_path:
                        _copy_tree_contents(source_path, target)
                except Exception as exc:
                    raise SkillInstallError(f"Unable to install Skill '{item.name}'") from exc
                installed.append(item.name)

            skipped.extend(item.name for item in previews if item.action == "skipped_existing")
        except Exception:
            SkillInstallResult(
                tuple(installed),
                tuple(skipped),
                tuple(created_paths),
                self.skills_root,
                created_root,
            ).rollback()
            raise

        return SkillInstallResult(
            tuple(installed),
            tuple(skipped),
            tuple(created_paths),
            self.skills_root,
            created_root,
        )


def _copy_tree_contents(source: Path, target: Path) -> None:
    """Copy a bundled Skill into an already-claimed empty target directory."""

    for source_path in sorted(source.rglob("*")):
        relative = source_path.relative_to(source)
        target_path = target / relative
        if source_path.is_dir():
            target_path.mkdir(parents=True, exist_ok=True)
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)
