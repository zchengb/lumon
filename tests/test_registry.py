"""Contract tests for the user-level Workspace registry and profiles."""

from __future__ import annotations

import json
import stat
from pathlib import Path

from lumon.skills.installer import SkillInstaller
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.manifest import load_manifest
from lumon.workspace.model import InitRequest
from lumon.workspace.registry import WorkspaceRegistry
from lumon.workspace.settings import WorkspaceSettingsStore


def _initialize(tmp_path: Path) -> tuple[Path, Path, WorkspaceRegistry, WorkspaceSettingsStore]:
    state_root = tmp_path / "user-state"
    registry = WorkspaceRegistry(state_root)
    settings = WorkspaceSettingsStore(state_root)
    target = tmp_path / "workspace"
    WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"),
        registry=registry,
        settings_store=settings,
    ).initialize(InitRequest(target))
    return target, state_root, registry, settings


def test_init_registers_workspace_and_creates_user_profile(tmp_path: Path) -> None:
    target, state_root, registry, settings = _initialize(tmp_path)

    manifest = load_manifest(target / "lumon" / "manifest.json")
    registrations = registry.list()
    assert len(registrations) == 1
    assert registrations[0].workspace_id == manifest.workspace_id
    assert registrations[0].path == target.resolve()

    profile = settings.path_for(manifest.workspace_id)
    assert profile.is_file()
    assert "url" not in profile.read_text(encoding="utf-8")
    assert stat.S_IMODE(profile.stat().st_mode) == 0o600
    assert "feishu" not in (target / "lumon" / "workspace.toml").read_text(encoding="utf-8")
    assert (state_root / "registry.toml").is_file()


def test_register_refreshes_a_moved_workspace_path_without_duplicate(tmp_path: Path) -> None:
    target, _, registry, _ = _initialize(tmp_path)
    manifest = json.loads((target / "lumon" / "manifest.json").read_text(encoding="utf-8"))

    registration = registry.register(target)

    assert str(registration.workspace_id) == manifest["workspace_id"]
    assert len(registry.list()) == 1


def test_dry_run_does_not_create_user_registry_or_profile(
    initializer: WorkspaceInitializer, tmp_path: Path
) -> None:
    state_root = initializer.registry.layout.root
    target = tmp_path / "workspace"

    initializer.initialize(InitRequest(target, dry_run=True))

    assert not state_root.exists()
