"""Shared fixtures for the Lumon v1 test surface."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from lumon.skills.installer import SkillInstaller
from lumon.visual import environment
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.registry import WorkspaceRegistry
from lumon.workspace.settings import WorkspaceSettingsStore


@pytest.fixture(autouse=True)
def isolate_visual_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Request/prompt tests must not inspect the developer's SDKs or Docker daemon."""

    def snapshot(*, refresh: bool = False) -> environment.EnvironmentSnapshot:
        del refresh
        return environment.EnvironmentSnapshot("2026-10-22T00:00:00+00:00", ())

    monkeypatch.setattr(environment, "get_environment", snapshot)


@pytest.fixture
def skills_root(tmp_path: Path) -> Path:
    return tmp_path / "home" / ".agents" / "skills"


@pytest.fixture
def initializer(skills_root: Path, tmp_path: Path) -> WorkspaceInitializer:
    return WorkspaceInitializer(
        skill_installer=SkillInstaller(skills_root=skills_root),
        registry=WorkspaceRegistry(tmp_path / "lumon-home"),
        settings_store=WorkspaceSettingsStore(tmp_path / "lumon-home"),
        now=lambda: datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
    )
