"""CLI contract tests for the Mark lifecycle commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from lumon.agents.mark.config import MarkAgentConfig, MarkConfigStore, ObservabilityConfig
from lumon.agents.mark.runner import AgentRunner, CodexAgentRunner
from lumon.cli.app import app
from lumon.cli.commands import agent as agent_commands
from lumon.tools.codex import CodexTool


def test_agent_configure_collects_secret_without_printing_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LUMON_HOME", str(tmp_path / "lumon"))
    result = CliRunner().invoke(app, ["agent", "configure"], input="cli_test\nsecret-value\n\n")

    assert result.exit_code == 0, result.stdout
    assert "secret-value" not in result.stdout
    config = MarkConfigStore(tmp_path / "lumon").load()
    assert config.feishu_app_id == "cli_test"
    assert config.feishu_app_secret == "secret-value"


def test_agent_doctor_json_is_safe_when_not_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LUMON_HOME", str(tmp_path / "lumon"))

    result = CliRunner().invoke(app, ["agent", "doctor", "--json"])

    assert result.exit_code == 3
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert "secret" not in result.stdout.casefold()


def test_agent_doctor_reports_the_configured_model_and_effort(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_root = tmp_path / "lumon"
    monkeypatch.setenv("LUMON_HOME", str(state_root))
    MarkConfigStore(state_root).save(
        MarkAgentConfig(
            enabled=True,
            agent_model="gpt-5.6-terra",
            agent_reasoning_effort="high",
            feishu_app_id="cli_test",
            feishu_app_secret="secret-value",
        )
    )

    def unavailable_runner(_config: MarkAgentConfig | None) -> AgentRunner:
        return CodexAgentRunner(tool=CodexTool(binary=str(tmp_path / "missing-codex")))

    monkeypatch.setattr(agent_commands, "create_agent_runner", unavailable_runner)
    result = CliRunner().invoke(app, ["agent", "doctor", "--json"])

    payload = json.loads(result.stdout)
    model_check = next(check for check in payload["checks"] if check["name"] == "agent_model")
    assert model_check["detail"] == ("Codex model: gpt-5.6-terra (reasoning effort: high)")


def test_agent_doctor_reports_langfuse_cloud_without_exposing_credentials(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_root = tmp_path / "lumon"
    monkeypatch.setenv("LUMON_HOME", str(state_root))
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    MarkConfigStore(state_root).save(
        MarkAgentConfig(
            enabled=True,
            feishu_app_id="cli_test",
            feishu_app_secret="secret-value",
            observability=ObservabilityConfig(enabled=True),
        )
    )

    def unavailable_runner(_config: MarkAgentConfig | None) -> AgentRunner:
        return CodexAgentRunner(tool=CodexTool(binary=str(tmp_path / "missing-codex")))

    monkeypatch.setattr(agent_commands, "create_agent_runner", unavailable_runner)
    result = CliRunner().invoke(app, ["agent", "doctor", "--json"])

    payload = json.loads(result.stdout)
    observability_check = next(
        check for check in payload["checks"] if check["name"] == "observability"
    )
    credentials_check = next(
        check for check in payload["checks"] if check["name"] == "observability_credentials"
    )
    assert "https://cloud.langfuse.com" in observability_check["detail"]
    assert credentials_check["ok"] is True
    assert "pk-lf-test" not in result.stdout
    assert "sk-lf-test" not in result.stdout


def test_agent_status_json_reports_stopped_without_creating_a_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LUMON_HOME", str(tmp_path / "lumon"))

    result = CliRunner().invoke(app, ["agent", "status", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["status"] == "stopped"
