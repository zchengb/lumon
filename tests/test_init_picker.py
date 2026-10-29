"""MCP initialization uses shared discovery, preserves scopes, and never clones."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from lumon.cli.app import app
from lumon.cli.commands import init as init_command
from lumon.cli.commands import init_picker
from lumon.tools.github_mcp_proxy import github_server_name
from lumon.tools.github_repositories import GithubRepository
from lumon.tools.setup import DependencyCheck, SetupInspector, SetupReport
from lumon.workspace.config import load_workspace_config
from lumon.workspace.initializer import WorkspaceInitializer


@pytest.fixture
def discovery(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, int]]:
    repository = GithubRepository(
        "app",
        "org/app",
        "https://team.ghe.com/org/app.git",
        "main",
        github_server_name("team.ghe.com"),
    )
    calls: list[tuple[str, str, int]] = []

    def search(
        host: str, query: str = "", *, page: int = 1, organization: str = ""
    ) -> tuple[GithubRepository, ...]:
        del query
        calls.append((host, organization, page))
        return (repository,)

    monkeypatch.setattr(init_picker, "search_repositories", search)

    def organizations(host: str, *, page: int = 1) -> tuple[str, ...]:
        return ("org",)

    def branches(host: str, repository: str, *, page: int = 1) -> tuple[str, ...]:
        return ("main", "release")

    monkeypatch.setattr(init_picker, "repository_organizations", organizations)
    monkeypatch.setattr(init_picker, "repository_branches", branches)
    monkeypatch.setattr(init_command, "_interactive_terminal", lambda: True)
    report = SetupReport(
        tuple(DependencyCheck(name, "ready") for name in ("git", "gh", "codex")), ("team.ghe.com",)
    )

    def inspect(_self: SetupInspector) -> SetupReport:
        return report

    monkeypatch.setattr(SetupInspector, "inspect", inspect)
    return calls


def test_cli_selects_mcp_repo_branch_and_scope_without_clone(
    tmp_path: Path,
    initializer: WorkspaceInitializer,
    monkeypatch: pytest.MonkeyPatch,
    discovery: list[tuple[str, str, int]],
) -> None:
    monkeypatch.setenv("LUMON_HOME", str(tmp_path / "lumon-home"))
    monkeypatch.setattr(init_command, "WorkspaceInitializer", lambda: initializer)
    target = tmp_path / "workspace"
    result = CliRunner().invoke(app, ["init", str(target)], input="y\n1\n1\nd\n2\ny\nn\n")
    assert result.exit_code == 0, result.output
    record = load_workspace_config(target / "lumon/workspace.toml").repositories[0]
    assert record.branch == "release" and record.auto_scan and not record.auto_delivery
    assert record.mcp_server == github_server_name("team.ghe.com")
    assert discovery == [("team.ghe.com", "org", 1)]
    assert not (target / "repos/app").exists()
    assert "Agent is not configured" in result.output


def test_cancel_does_not_create_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, discovery: list[tuple[str, str, int]]
) -> None:
    monkeypatch.setenv("LUMON_HOME", str(tmp_path / "state"))
    target = tmp_path / "workspace"
    result = CliRunner().invoke(app, ["init", str(target)], input="y\n0\n", catch_exceptions=True)
    assert result.exit_code != 0
    assert not target.exists()


def test_invalid_choice_does_not_silently_select_a_repo(
    tmp_path: Path,
    initializer: WorkspaceInitializer,
    monkeypatch: pytest.MonkeyPatch,
    discovery: list[tuple[str, str, int]],
) -> None:
    monkeypatch.setenv("LUMON_HOME", str(tmp_path / "lumon-home"))
    monkeypatch.setattr(init_command, "WorkspaceInitializer", lambda: initializer)
    result = CliRunner().invoke(
        app, ["init", str(tmp_path / "workspace")], input="y\n0\n99\nd\n1\nd\n0\ny\ny\n"
    )
    assert result.exit_code == 0, result.output
    assert "Select displayed numbers" in result.output
    assert "Select at least one repository" in result.output


def test_json_reports_missing_tools_and_agent_without_prompt(
    tmp_path: Path, initializer: WorkspaceInitializer, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LUMON_HOME", str(tmp_path / "lumon-home"))
    monkeypatch.setattr(init_command, "WorkspaceInitializer", lambda: initializer)

    def inspect(_self: SetupInspector) -> SetupReport:
        return SetupReport((DependencyCheck("codex", "missing", "install codex"),), ())

    monkeypatch.setattr(SetupInspector, "inspect", inspect)
    result = CliRunner().invoke(app, ["init", str(tmp_path / "workspace"), "--json"])
    assert result.exit_code == 0
    assert '"warnings"' in result.output and "codex: missing; install codex" in result.output
    assert "Agent is not configured" in result.output and "Add a Repository?" not in result.output
