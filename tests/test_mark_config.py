"""Tests for Mark configuration and user-level SOUL resolution."""

from __future__ import annotations

import stat
from pathlib import Path
from uuid import uuid4

import pytest

from lumon.agents.mark.config import MarkAgentConfig, MarkConfigStore
from lumon.agents.mark.soul import MarkSoulLoader
from lumon.errors import AgentConfigError


def _config() -> MarkAgentConfig:
    return MarkAgentConfig(
        enabled=True,
        default_workspace_id=uuid4(),
        feishu_app_id="cli_test",
        feishu_app_secret="secret-value",
    )


def test_mark_config_round_trip_is_owner_only_and_safe_dict_excludes_secret(
    tmp_path: Path,
) -> None:
    store = MarkConfigStore(tmp_path / "lumon")
    config = _config()

    store.save(config)

    assert store.load() == config
    assert config.agent_provider == "codex"
    assert config.agent_model is None
    assert stat.S_IMODE(store.path.stat().st_mode) == 0o600
    assert "secret-value" not in str(config.to_safe_dict())
    assert "app_secret" not in config.to_safe_dict()
    rendered = store.path.read_text(encoding="utf-8")
    assert 'agent_provider = "codex"' in rendered
    assert 'agent_model = ""' in rendered
    assert "codex_model" not in rendered


def test_invalid_config_does_not_expose_secret(tmp_path: Path) -> None:
    store = MarkConfigStore(tmp_path / "lumon")
    store.path.parent.mkdir(parents=True)
    store.path.write_text(
        'schema_version = 1\nenabled = true\ndefault_workspace_id = ""\n'
        'execution_mode = "full_access"\nresponse_mode = "progress_and_final"\n'
        'codex_model = ""\n[feishu]\napp_id = "cli_test"\napp_secret = "secret-value"\n',
        encoding="utf-8",
    )
    store.path.chmod(0o600)

    store.path.write_text("schema_version = 99\n", encoding="utf-8")
    with pytest.raises(AgentConfigError, match="schema") as error:
        store.load()
    assert "secret-value" not in str(error.value)


def test_legacy_codex_model_is_read_but_normalized_on_save(tmp_path: Path) -> None:
    store = MarkConfigStore(tmp_path / "lumon")
    store.path.parent.mkdir(parents=True)
    store.path.write_text(
        "schema_version = 1\n"
        "enabled = true\n"
        'default_workspace_id = ""\n'
        'execution_mode = "full_access"\n'
        'response_mode = "progress_and_final"\n'
        'codex_model = "gpt-test"\n'
        "[feishu]\n"
        'app_id = "cli_test"\n'
        'app_secret = "secret-value"\n',
        encoding="utf-8",
    )
    store.path.chmod(0o600)

    loaded = store.load()

    assert loaded.agent_provider == "codex"
    assert loaded.agent_model == "gpt-test"
    store.save(loaded)
    rendered = store.path.read_text(encoding="utf-8")
    assert 'agent_model = "gpt-test"' in rendered
    assert "codex_model" not in rendered


def test_packaged_soul_is_available_and_user_override_wins(tmp_path: Path) -> None:
    state_root = tmp_path / "lumon"
    loader = MarkSoulLoader(state_root)

    packaged = loader.load()
    assert "Mark" in packaged
    assert "Workspace" in packaged

    loader.override_path.parent.mkdir(parents=True)
    loader.override_path.write_text("user-owned Mark instructions\n", encoding="utf-8")

    assert loader.load() == "user-owned Mark instructions\n"
