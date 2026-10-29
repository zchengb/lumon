"""Dependency state and safe guidance without installed CLIs or real logins."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from lumon.dashboard.routes import create_app
from lumon.dashboard.service import DashboardService
from lumon.errors import PreflightError
from lumon.tools import github_repositories, setup
from lumon.tools.github_auth import DependencyState, GithubAuthentication, github_authentication
from lumon.tools.setup import SetupInspector


@pytest.fixture(autouse=True)
def isolate_setup_environment() -> None:
    """Override the suite's ready-report fake to exercise the real adapter."""


class Commands:
    def __init__(self) -> None:
        self.github = subprocess.CompletedProcess(
            [],
            0,
            json.dumps({"hosts": {"team.ghe.com": [{"active": True, "state": "success"}]}}),
            "",
        )
        self.codex = subprocess.CompletedProcess([], 0, "Logged in", "")
        self.calls: list[list[str]] = []
        self.failure: OSError | subprocess.TimeoutExpired | None = None

    def run(self, command: list[str], **_options: object) -> subprocess.CompletedProcess[str]:
        self.calls.append(command)
        if self.failure:
            raise self.failure
        return self.github if "gh" in command[0] else self.codex


@pytest.fixture
def commands(monkeypatch: pytest.MonkeyPatch) -> Commands:
    monkeypatch.setattr(setup, "resolve_github_binary", lambda: "/test/gh")
    monkeypatch.setattr(setup, "resolve_codex_binary", lambda: "/test/codex")

    def which(name: str) -> str:
        return name

    monkeypatch.setattr(setup.shutil, "which", which)
    return Commands()


def test_ready_tools_do_not_start_agent(commands: Commands) -> None:
    report = SetupInspector(commands.run).inspect()
    assert report.ready
    assert report.hosts == ("team.ghe.com",)
    assert commands.calls == [
        ["/test/gh", "auth", "status", "--json", "hosts"],
        ["/test/codex", "login", "status"],
    ]


def test_missing_tools_are_explicit_and_safe(
    commands: Commands, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(setup, "resolve_github_binary", lambda: None)

    def which(name: str) -> None:
        return None

    monkeypatch.setattr(setup.shutil, "which", which)
    report = SetupInspector(commands.run).inspect()
    assert not report.ready
    assert [check.state for check in report.checks] == ["missing", "missing", "missing"]
    assert "install.sh" in (report.checks[2].action or "")
    assert commands.calls == []


def test_old_gh_is_not_reported_as_logged_out(commands: Commands) -> None:
    commands.github = subprocess.CompletedProcess([], 1, "", "unknown flag: --json\nprivate-token")
    report = SetupInspector(commands.run).inspect()
    assert report.checks[1].state == "incompatible"
    assert "private-token" not in repr(report)


@pytest.mark.parametrize("state", ["error", "timeout"])
def test_json_exit_zero_does_not_prove_valid_auth(commands: Commands, state: str) -> None:
    commands.github.stdout = json.dumps(
        {"hosts": {"team.ghe.com": [{"active": True, "state": state}]}}
    )
    assert SetupInspector(commands.run).inspect().hosts == ()
    assert SetupInspector(commands.run).inspect().checks[1].state == "needs_login"


def test_codex_needs_login_differs_from_command_error(commands: Commands) -> None:
    commands.codex = subprocess.CompletedProcess([], 1, "", "Not logged in")
    assert SetupInspector(commands.run).inspect().checks[2].state == "needs_login"
    commands.codex.stderr = "private-upstream-error"
    report = SetupInspector(commands.run).inspect()
    assert report.checks[2].state == "error"
    assert "private-upstream-error" not in repr(report)


@pytest.mark.parametrize("failure", [OSError("private"), subprocess.TimeoutExpired("private", 1)])
def test_process_failure_is_not_a_login_instruction(
    commands: Commands, failure: OSError | subprocess.TimeoutExpired
) -> None:
    commands.failure = failure
    report = SetupInspector(commands.run).inspect()
    assert [check.state for check in report.checks] == ["ready", "error", "error"]
    assert "private" not in repr(report)


def test_bad_auth_json_is_explicit(commands: Commands) -> None:
    commands.github.stdout = "not-json-secret"
    assert github_authentication("/test/gh", runner=commands.run).state == "error"


@pytest.mark.parametrize(
    ("state", "message"),
    [("missing", "not installed"), ("incompatible", "Upgrade"), ("error", "Could not check")],
)
def test_source_listing_does_not_hide_setup_failures(
    monkeypatch: pytest.MonkeyPatch, state: DependencyState, message: str
) -> None:
    def authentication(binary: str | None) -> GithubAuthentication:
        return GithubAuthentication(state)

    monkeypatch.setattr(github_repositories, "github_authentication", authentication)
    with pytest.raises(PreflightError, match=message):
        github_repositories.authenticated_hosts()


@pytest.fixture
def client(tmp_path: Path, commands: Commands) -> Iterator[httpx.Client]:
    service = DashboardService(state_root=tmp_path, setup_inspector=SetupInspector(commands.run))
    with TestClient(create_app(service)) as session:
        yield session


def test_setup_api_distinguishes_tools_from_agent_configuration(client: httpx.Client) -> None:
    response = client.get("/api/setup")
    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["agent_configured"] is False
    assert response.headers["cache-control"] == "no-store"
    assert (
        client.get("/api/setup", headers={"Origin": "https://attacker.example"}).status_code == 403
    )
