"""CLI contract tests for the Mark lifecycle commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from lumon.agents.mark.config import MarkConfigStore
from lumon.cli.app import app


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


def test_agent_status_json_reports_stopped_without_creating_a_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LUMON_HOME", str(tmp_path / "lumon"))

    result = CliRunner().invoke(app, ["agent", "status", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["status"] == "stopped"
