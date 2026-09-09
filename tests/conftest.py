"""Shared fixtures for the Lumon v1 test surface."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from lumon.skills.installer import SkillInstaller
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.registry import WorkspaceRegistry
from lumon.workspace.settings import WorkspaceSettingsStore


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
