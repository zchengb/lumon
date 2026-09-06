"""Contract tests for Workspace initialization."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lumon.errors import InvalidInputError, PreflightError
from lumon.workspace.doctor import Doctor
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.layout import WorkspaceLayout
from lumon.workspace.model import InitRequest


def test_initialize_missing_workspace_and_install_missing_skill(
    initializer: WorkspaceInitializer, skills_root: Path, tmp_path: Path
) -> None:
    target = tmp_path / "workspaces" / "lumon-lab"

    result = initializer.initialize(InitRequest(target))

    assert result.status == "initialized"
    assert result.workspace == target.resolve()
    assert result.installed_skills == (
        "lumon-story-planning",
        "lumon-technical-planning",
    )
    assert result.skipped_skills == ()
    assert (target / "README.md").is_file()
    assert (target / "AGENTS.md").is_file()
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "Global Agent Skills live under `~/.agents/skills/`" in agents
    assert "lumon/manifest.json" in agents
    assert (target / ".gitignore").is_file()
    assert (target / "lumon" / "workspace.toml").read_text(encoding="utf-8") == (
        'schema_version = 1\nname = "lumon-lab"\n'
    )
    manifest = json.loads((target / "lumon" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["name"] == "lumon-lab"
    assert manifest["status"] == "initialized"
    assert "runtime_profile" not in manifest
    assert "repositories" not in manifest
    assert not (target / "skills").exists()
    assert (skills_root / "lumon-story-planning" / "SKILL.md").is_file()
    assert (skills_root / "lumon-technical-planning" / "SKILL.md").is_file()


def test_initialize_empty_workspace_uses_explicit_name(
    initializer: WorkspaceInitializer, tmp_path: Path
) -> None:
    target = tmp_path / "empty"
    target.mkdir()

    result = initializer.initialize(InitRequest(target, name="Review Lab"))

    assert result.status == "initialized"
    assert (target / "README.md").read_text(encoding="utf-8").startswith("# Review Lab\n")
    assert 'name = "Review Lab"' in (target / "lumon" / "workspace.toml").read_text(
        encoding="utf-8"
    )


def test_dry_run_does_not_create_workspace_or_skill_directory(
    initializer: WorkspaceInitializer, skills_root: Path, tmp_path: Path
) -> None:
    target = tmp_path / "not-created"

    result = initializer.initialize(InitRequest(target, dry_run=True))

    assert result.status == "dry_run"
    assert not target.exists()
    assert not skills_root.exists()
    assert result.planned_skills == (
        "lumon-story-planning",
        "lumon-technical-planning",
    )
    assert result.planned_paths


def test_dry_run_does_not_create_missing_parent_directories(
    initializer: WorkspaceInitializer, tmp_path: Path
) -> None:
    target = tmp_path / "missing" / "nested" / "workspace"

    initializer.initialize(InitRequest(target, dry_run=True))

    assert not (tmp_path / "missing").exists()


def test_non_empty_unmanaged_directory_is_rejected(
    initializer: WorkspaceInitializer, tmp_path: Path
) -> None:
    target = tmp_path / "existing"
    target.mkdir()
    (target / "keep.txt").write_text("user data", encoding="utf-8")

    with pytest.raises(PreflightError, match="non-empty"):
        initializer.initialize(InitRequest(target))

    assert (target / "keep.txt").read_text(encoding="utf-8") == "user data"
    assert not (target / "lumon").exists()


def test_existing_workspace_is_idempotent_and_skips_existing_skill(
    initializer: WorkspaceInitializer, skills_root: Path, tmp_path: Path
) -> None:
    target = tmp_path / "workspace"
    initializer.initialize(InitRequest(target))
    readme_before = (target / "README.md").read_text(encoding="utf-8")
    skill_file = skills_root / "lumon-story-planning" / "SKILL.md"
    skill_file.write_text("user-owned content\n", encoding="utf-8")

    result = initializer.initialize(InitRequest(target, name="A different name"))

    assert result.status == "already_initialized"
    assert result.installed_skills == ()
    assert result.skipped_skills == (
        "lumon-story-planning",
        "lumon-technical-planning",
    )
    assert (target / "README.md").read_text(encoding="utf-8") == readme_before
    assert skill_file.read_text(encoding="utf-8") == "user-owned content\n"


def test_existing_invalid_manifest_is_rejected(
    initializer: WorkspaceInitializer, tmp_path: Path
) -> None:
    target = tmp_path / "broken"
    layout = WorkspaceLayout.from_root(target)
    layout.control_dir.mkdir(parents=True)
    layout.manifest.write_text('{"schema_version": 99}\n', encoding="utf-8")

    with pytest.raises(PreflightError, match="Unsupported Workspace manifest schema"):
        initializer.initialize(InitRequest(target))


def test_root_initialization_is_rejected(initializer: WorkspaceInitializer) -> None:
    with pytest.raises(InvalidInputError, match="filesystem root"):
        initializer.initialize(InitRequest(Path("/")))


def test_doctor_accepts_a_creatable_missing_skills_parent(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    report = Doctor(home / ".agents" / "skills").inspect()

    skills_check = next(check for check in report.checks if check.name == "global_skills")
    assert skills_check.ok
    assert skills_check.detail.startswith("will create")
