"""Discover Skills bundled in the installed Lumon package."""

from __future__ import annotations

from importlib import resources
from importlib.resources.abc import Traversable

_BUNDLE_PACKAGE = "lumon.bundled_skills"


class SkillCatalog:
    """Expose only valid bundled Skill directories."""

    def __init__(self, package: str = _BUNDLE_PACKAGE) -> None:
        self._root = resources.files(package)

    def names(self) -> tuple[str, ...]:
        """Return bundled Skill names in deterministic order."""

        names = [
            entry.name
            for entry in self._root.iterdir()
            if entry.is_dir() and entry.joinpath("SKILL.md").is_file()
        ]
        return tuple(sorted(names))

    def source(self, name: str) -> Traversable:
        """Return one bundled Skill directory or raise a clear error."""

        source = self._root.joinpath(name)
        if not source.is_dir() or not source.joinpath("SKILL.md").is_file():
            raise KeyError(f"Unknown bundled Skill: {name}")
        return source
