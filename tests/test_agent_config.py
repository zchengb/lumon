"""Tests for Agent configuration and user-level SOUL resolution."""

from __future__ import annotations

import stat
from pathlib import Path
from uuid import uuid4

import pytest

from lumon.agents.agent.config import (
    DEFAULT_AGENT_MODEL,
    DEFAULT_AGENT_REASONING_EFFORT,
    DEFAULT_LANGFUSE_BASE_URL,
    AgentConfig,
    AgentConfigStore,
    ObservabilityConfig,
)
from lumon.agents.agent.soul import SoulLoader
from lumon.errors import AgentConfigError


def _config() -> AgentConfig:
    return AgentConfig(
        enabled=True,
        default_workspace_id=uuid4(),
        feishu_app_id="cli_test",
        feishu_app_secret="secret-value",
    )


def test_agent_config_round_trip_is_owner_only_and_safe_dict_excludes_secret(
    tmp_path: Path,
) -> None:
    store = AgentConfigStore(tmp_path / "lumon")
    config = _config()

    store.save(config)

    assert store.load() == config
    assert config.agent_provider == "codex"
    assert config.agent_model == DEFAULT_AGENT_MODEL
    assert config.agent_reasoning_effort == DEFAULT_AGENT_REASONING_EFFORT
    assert config.observability.base_url == DEFAULT_LANGFUSE_BASE_URL
    assert not config.observability.enabled
    assert config.observability.capture_content is True
    assert stat.S_IMODE(store.path.stat().st_mode) == 0o600
    assert "secret-value" not in str(config.to_safe_dict())
    assert "app_secret" not in config.to_safe_dict()
    rendered = store.path.read_text(encoding="utf-8")
    assert 'agent_provider = "codex"' in rendered
    assert f'agent_model = "{DEFAULT_AGENT_MODEL}"' in rendered
    assert f'agent_reasoning_effort = "{DEFAULT_AGENT_REASONING_EFFORT}"' in rendered
    assert "codex_model" not in rendered
    assert "[observability]" in rendered
    assert "capture_content = true" in rendered


def test_agent_model_and_reasoning_effort_can_be_overridden(tmp_path: Path) -> None:
    store = AgentConfigStore(tmp_path / "lumon")
    config = AgentConfig(
        enabled=True,
        agent_model="gpt-5.6-sol",
        agent_reasoning_effort="ultra",
        feishu_app_id="cli_test",
        feishu_app_secret="secret-value",
    )

    store.save(config)

    assert store.load().agent_model == "gpt-5.6-sol"
    assert store.load().agent_reasoning_effort == "ultra"
    assert 'agent_model = "gpt-5.6-sol"' in store.path.read_text(encoding="utf-8")


def test_existing_empty_model_config_uses_the_codex_default(tmp_path: Path) -> None:
    store = AgentConfigStore(tmp_path / "lumon")
    store.path.parent.mkdir(parents=True)
    store.path.write_text(
        "schema_version = 1\n"
        "enabled = true\n"
        'default_workspace_id = ""\n'
        'execution_mode = "full_access"\n'
        'response_mode = "progress_and_final"\n'
        'agent_provider = "codex"\n'
        'agent_model = ""\n'
        "[feishu]\n"
        'app_id = "cli_test"\n'
        'app_secret = "secret-value"\n',
        encoding="utf-8",
    )
    store.path.chmod(0o600)

    loaded = store.load()

    assert loaded.agent_model == DEFAULT_AGENT_MODEL
    assert loaded.agent_reasoning_effort == DEFAULT_AGENT_REASONING_EFFORT
    assert not loaded.observability.enabled
    assert loaded.observability.capture_content is True


def test_existing_disabled_content_capture_is_normalized_on_load(tmp_path: Path) -> None:
    store = AgentConfigStore(tmp_path / "lumon")
    store.path.parent.mkdir(parents=True)
    store.path.write_text(
        "schema_version = 1\n"
        "enabled = true\n"
        'default_workspace_id = ""\n'
        'execution_mode = "full_access"\n'
        'response_mode = "progress_and_final"\n'
        'agent_provider = "codex"\n'
        'agent_model = "gpt-5.6-luna"\n'
        'agent_reasoning_effort = "max"\n'
        "[feishu]\n"
        'app_id = "cli_test"\n'
        'app_secret = "secret-value"\n'
        "[observability]\n"
        "capture_content = false\n",
        encoding="utf-8",
    )
    store.path.chmod(0o600)

    loaded = store.load()

    assert loaded.observability.capture_content is True


def test_invalid_config_does_not_expose_secret(tmp_path: Path) -> None:
    store = AgentConfigStore(tmp_path / "lumon")
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
    store = AgentConfigStore(tmp_path / "lumon")
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
    assert loaded.agent_reasoning_effort == DEFAULT_AGENT_REASONING_EFFORT
    store.save(loaded)
    rendered = store.path.read_text(encoding="utf-8")
    assert 'agent_model = "gpt-test"' in rendered
    assert "codex_model" not in rendered


def test_observability_config_round_trip_is_safe(tmp_path: Path) -> None:
    store = AgentConfigStore(tmp_path / "lumon")
    config = AgentConfig(
        enabled=True,
        feishu_app_id="cli_test",
        feishu_app_secret="secret-value",
        observability=ObservabilityConfig(
            enabled=True,
            base_url="https://us.cloud.langfuse.com",
            capture_content=True,
            sample_rate=0.25,
            public_key="pk-lf-test",
            secret_key="sk-lf-test",
        ),
    )

    store.save(config)

    loaded = store.load()
    assert loaded.observability == config.observability
    assert loaded.to_safe_dict()["observability"] == {
        "enabled": True,
        "provider": "langfuse",
        "base_url": "https://us.cloud.langfuse.com",
        "capture_content": True,
        "sample_rate": 0.25,
    }
    assert "secret-value" not in str(loaded.to_safe_dict())
    assert "pk-lf-test" not in str(loaded.to_safe_dict())
    assert "sk-lf-test" not in str(loaded.to_safe_dict())


def test_invalid_observability_sample_rate_is_rejected() -> None:
    config = AgentConfig(
        feishu_app_id="cli_test",
        feishu_app_secret="secret-value",
        observability=ObservabilityConfig(sample_rate=1.1),
    )

    with pytest.raises(AgentConfigError, match="sample rate"):
        config.validate()


def test_packaged_soul_is_available_and_user_override_wins(tmp_path: Path) -> None:
    state_root = tmp_path / "lumon"
    loader = SoulLoader(state_root)

    assert loader.override_path == state_root / "agents" / "agent" / "templates" / "SOUL.md"
    packaged = loader.load()
    assert "Agent" in packaged
    assert "Workspace" in packaged

    loader.override_path.parent.mkdir(parents=True)
    loader.override_path.write_text("user-owned Agent instructions\n", encoding="utf-8")

    assert loader.load() == "user-owned Agent instructions\n"


def test_legacy_soul_override_is_read_without_becoming_the_new_write_path(tmp_path: Path) -> None:
    state_root = tmp_path / "lumon"
    loader = SoulLoader(state_root)
    legacy_path = state_root / "agents" / "mark" / "templates" / "SOUL.md"
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text("legacy Agent instructions\n", encoding="utf-8")

    assert loader.override_path != legacy_path
    assert loader.load() == "legacy Agent instructions\n"
