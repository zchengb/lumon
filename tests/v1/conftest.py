"""Shared fixtures for the Lumon v1 test surface."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from lumon.skills.installer import SkillInstaller
from lumon.workspace.initializer import WorkspaceInitializer


@pytest.fixture
def skills_root(tmp_path: Path) -> Path:
    return tmp_path / "home" / ".agents" / "skills"


@pytest.fixture
def initializer(skills_root: Path) -> WorkspaceInitializer:
    return WorkspaceInitializer(
        skill_installer=SkillInstaller(skills_root=skills_root),
        now=lambda: datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
    )
