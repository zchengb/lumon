"""Contract tests for global Skill installation."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import pytest

from lumon.errors import SkillInstallError
from lumon.skills.catalog import SkillCatalog
from lumon.skills.installer import SkillInstaller


def test_preview_is_read_only(skills_root: Path) -> None:
    installer = SkillInstaller(skills_root=skills_root)

    preview = installer.preview()

    assert [(item.name, item.action) for item in preview] == [
        ("lumon-story-planning", "will_install"),
        ("lumon-technical-planning", "will_install"),
    ]
    assert not skills_root.exists()


def test_catalog_contains_chinese_dual_mode_planning_skills() -> None:
    catalog = SkillCatalog()

    assert catalog.names() == ("lumon-story-planning", "lumon-technical-planning")
    with pytest.raises(KeyError):
        catalog.source("lumon-workspace")

    for name in catalog.names():
        content = catalog.source(name).joinpath("SKILL.md").read_text(encoding="utf-8")
        assert "twg jira workitem get" in content
        assert "独立项目模式" in content
        assert "AGENTS.md" in content


def test_existing_skill_directory_is_skipped_without_overwrite(skills_root: Path) -> None:
    existing = skills_root / "lumon-story-planning"
    existing.mkdir(parents=True)
    skill_file = existing / "SKILL.md"
    skill_file.write_text("keep this file\n", encoding="utf-8")

    result = SkillInstaller(skills_root=skills_root).install()

    assert result.installed == ("lumon-technical-planning",)
    assert result.skipped_existing == ("lumon-story-planning",)
    assert skill_file.read_text(encoding="utf-8") == "keep this file\n"


def test_new_skill_install_can_be_rolled_back(skills_root: Path) -> None:
    installer = SkillInstaller(skills_root=skills_root)

    result = installer.install()
    assert (skills_root / "lumon-story-planning").is_dir()
    assert (skills_root / "lumon-technical-planning").is_dir()

    result.rollback()

    assert not skills_root.exists()


class FailingCatalog(SkillCatalog):
    """Expose one valid Skill and one broken bundle for rollback tests."""

    def names(self) -> tuple[str, ...]:
        return ("lumon-story-planning", "missing-bundle")

    def source(self, name: str):
        if name == "lumon-story-planning":
            return resources.files("lumon.bundled_skills").joinpath("lumon-story-planning")
        raise KeyError(name)


def test_failed_bundle_install_removes_all_new_global_content(skills_root: Path) -> None:
    installer = SkillInstaller(skills_root=skills_root, catalog=FailingCatalog())

    with pytest.raises(SkillInstallError, match="missing-bundle"):
        installer.install()

    assert not skills_root.exists()
