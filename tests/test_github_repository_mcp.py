"""Repository-scoped GitHub MCP behavior without a real account or network."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from lumon.errors import PreflightError
from lumon.tools import github_repositories
from lumon.tools.github_mcp_proxy import (
    GithubMcpProxy,
    allowed_tool_call,
    github_endpoint,
    github_server_name,
    selected_repositories,
    workspace_git_environment,
    workspace_mcp_config,
)
from lumon.tools.github_repositories import authenticated_hosts, search_repositories
from lumon.workspace.config import WorkspaceConfig
from lumon.workspace.model import RepositoryRecord


def test_only_official_github_hosts_are_accepted() -> None:
    assert github_endpoint("team.ghe.com") == "https://copilot-api.team.ghe.com/mcp"
    with pytest.raises(ValueError):
        github_endpoint("team.ghe.com.attacker.example")


def test_mcp_calls_are_limited_to_selected_repositories() -> None:
    selected = frozenset({"org/app"})
    assert allowed_tool_call(
        "get_file_contents", {"owner": "Org", "repo": "App"}, discovery=False, repositories=selected
    )
    assert not allowed_tool_call(
        "get_file_contents",
        {"owner": "Org", "repo": "other"},
        discovery=False,
        repositories=selected,
    )
    assert allowed_tool_call(
        "search_code", {"query": "repo:org/app invoice"}, discovery=False, repositories=selected
    )
    for query in (
        '"repo:org/app" invoice',
        "repo:org/app OR secret",
        "repo:org/app repo:org/other",
    ):
        assert not allowed_tool_call(
            "search_code", {"query": query}, discovery=False, repositories=selected
        )
    assert not allowed_tool_call("push_files", {}, discovery=False, repositories=selected)


def test_runtime_config_and_proxy_filter_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    server = github_server_name("team.ghe.com")
    workspace = tmp_path / "workspace"
    config_path = workspace / "lumon" / "workspace.toml"
    WorkspaceConfig(
        "Example",
        (
            RepositoryRecord(
                "app", "https://team.ghe.com/org/app.git", "repos/app", "main", server
            ),
            RepositoryRecord(
                "legacy", "https://team.ghe.com/org/legacy.git", "repos/legacy", "main"
            ),
        ),
    ).write(config_path)
    assert selected_repositories(workspace, "team.ghe.com", server) == frozenset({"org/app"})
    arguments = workspace_mcp_config(workspace)
    assert len(arguments) == 1 and server in arguments[0]
    assert str(workspace) in arguments[0]
    monkeypatch.setattr(
        "lumon.tools.github_mcp_proxy.github_credential_helper", lambda: "!gh auth git-credential"
    )
    environment = workspace_git_environment(
        workspace,
        {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "safe.key", "GIT_CONFIG_VALUE_0": "safe"},
    )
    assert environment is not None
    assert environment["GIT_CONFIG_COUNT"] == "3"
    assert environment["GIT_CONFIG_VALUE_0"] == "safe"
    assert environment["GIT_CONFIG_KEY_1"] == "credential.https://team.ghe.com.helper"
    assert environment["GIT_CONFIG_VALUE_2"] == "!gh auth git-credential"
    proxy = GithubMcpProxy("team.ghe.com", workspace)
    sent: list[dict[str, object]] = []

    def request(message: dict[str, object]) -> list[dict[str, object]]:
        sent.append(message)
        return [{"result": {"tools": [{"name": "get_file_contents"}, {"name": "push_files"}]}}]

    monkeypatch.setattr(proxy, "_request", request)
    replies = proxy.handle({"id": 1, "method": "tools/list"})
    assert replies == [{"result": {"tools": [{"name": "get_file_contents"}]}}]
    denied = proxy.handle(
        {
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "get_file_contents",
                "arguments": {"owner": "org", "repo": "legacy"},
            },
        }
    )
    assert "error" in denied[0] and len(sent) == 1
    resources = proxy.handle({"id": 3, "method": "resources/read", "params": {"uri": "other"}})
    assert "error" in resources[0] and len(sent) == 1


def _repository_metadata(
    host: str = "team.ghe.com", name: str = "app", owner: str = "org"
) -> dict[str, object]:
    return {
        "name": name,
        "full_name": f"{owner}/{name}",
        "default_branch": "main",
        "clone_url": f"https://{host}/{owner}/{name}.git",
    }


class _Discovery:
    def __init__(self) -> None:
        self.items: object = [_repository_metadata()]
        self.pages: dict[int, object] | None = None
        self.cli_calls: list[list[str]] = []
        self.mcp_calls: list[dict[str, object]] = []
        self.cli_returncode = 0
        self.cli_stdout: str | None = None
        self.failure: OSError | subprocess.TimeoutExpired | None = None

    def run(
        self,
        command: list[str],
        *,
        capture_output: bool,
        text: bool,
        check: bool,
        timeout: int,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        assert capture_output and text and not check and timeout == 30
        assert env["GH_PROMPT_DISABLED"] == env["GH_NO_UPDATE_NOTIFIER"] == "1"
        self.cli_calls.append(command)
        if self.failure:
            raise self.failure
        items = self.items
        if self.pages is not None:
            page = int(parse_qs(urlsplit(command[-1]).query)["page"][0])
            items = self.pages.get(page, [])
        stdout = self.cli_stdout if self.cli_stdout is not None else json.dumps(items)
        return subprocess.CompletedProcess(
            command, self.cli_returncode, stdout, "private-upstream-detail"
        )

    def handle(self, message: dict[str, object]) -> list[dict[str, object]]:
        self.mcp_calls.append(message)
        if self.failure:
            raise self.failure
        if message.get("method") != "tools/call":
            return []
        return [{"result": {"content": [{"type": "text", "text": "{}"}]}}]


@pytest.fixture
def discovery(monkeypatch: pytest.MonkeyPatch) -> _Discovery:
    remote = _Discovery()
    monkeypatch.setattr(
        github_repositories, "authenticated_hosts", lambda: ("team.ghe.com", "github.com")
    )
    monkeypatch.setattr(github_repositories, "resolve_github_binary", lambda: "/test/bin/gh")
    monkeypatch.setattr(github_repositories.subprocess, "run", remote.run)

    def handle(self: GithubMcpProxy, message: dict[str, object]) -> list[dict[str, object]]:
        del self
        return remote.handle(message)

    monkeypatch.setattr(GithubMcpProxy, "handle", handle)
    return remote


@pytest.mark.parametrize("query", ["", " \t\n "])
@pytest.mark.parametrize("host", ["team.ghe.com", "github.com"])
def test_blank_query_lists_account_repositories(
    discovery: _Discovery, host: str, query: str
) -> None:
    discovery.items = [_repository_metadata(host)]
    results = search_repositories(host, query)
    assert [(repo.full_name, repo.branch, repo.mcp_server) for repo in results] == [
        ("org/app", "main", github_server_name(host))
    ]
    assert discovery.cli_calls == [
        [
            "/test/bin/gh",
            "api",
            "--hostname",
            host,
            "/user/repos?per_page=100&page=1&sort=full_name&direction=asc",
        ]
    ]
    assert discovery.mcp_calls == []


def test_account_listing_can_fetch_past_search_limit(discovery: _Discovery) -> None:
    discovery.items = [_repository_metadata(name=f"app-{index}") for index in range(100)]
    assert len(search_repositories("team.ghe.com", page=11)) == 100
    discovery.items = []
    assert search_repositories("team.ghe.com", page=12) == ()
    assert [command[-1] for command in discovery.cli_calls] == [
        "/user/repos?per_page=100&page=11&sort=full_name&direction=asc",
        "/user/repos?per_page=100&page=12&sort=full_name&direction=asc",
    ]
    assert discovery.mcp_calls == []


@pytest.mark.parametrize("host", ["team.ghe.com", "github.com"])
def test_search_filters_all_accessible_pages(discovery: _Discovery, host: str) -> None:
    discovery.pages = {
        1: [_repository_metadata(host, f"other-{index}") for index in range(100)],
        2: [_repository_metadata(host, f"other-{index}") for index in range(99)]
        + [_repository_metadata(host, "Momento-app", "personal")],
        3: [_repository_metadata(host, "momento-backend", "team")],
    }
    results = search_repositories(host, " MoMeNtO ")
    assert [repo.full_name for repo in results] == ["personal/Momento-app", "team/momento-backend"]
    assert len(discovery.cli_calls) == 3
    assert all("/user/repos?" in call[-1] for call in discovery.cli_calls)
    assert discovery.mcp_calls == []


def test_search_paginates_filtered_results(discovery: _Discovery) -> None:
    discovery.pages = {
        1: [_repository_metadata(name=f"app-{index:03}") for index in range(100)],
        2: [_repository_metadata(name=f"other-{index:03}") for index in range(20)]
        + [_repository_metadata(name=f"app-{index:03}") for index in range(100, 180)],
        3: [_repository_metadata(name=f"app-{index:03}") for index in range(180, 203)],
    }
    results = [search_repositories("team.ghe.com", "app", page=page) for page in (1, 2, 3)]
    assert [len(result) for result in results] == [100, 100, 3]
    assert [repo.name for page in results for repo in page] == [
        f"app-{index:03}" for index in range(203)
    ]


@pytest.mark.parametrize("query", ["", "app"])
def test_search_limits_organization_to_accessible_repositories(
    discovery: _Discovery, query: str
) -> None:
    discovery.items = [
        _repository_metadata(name="app", owner="Team"),
        _repository_metadata(name="app", owner="other"),
    ]
    results = search_repositories("team.ghe.com", query, organization="team")
    assert [repo.full_name for repo in results] == ["Team/app"]
    assert "/user/repos?" in discovery.cli_calls[0][-1]


def test_search_can_find_repositories_beyond_first_thousand(discovery: _Discovery) -> None:
    discovery.pages = {
        page: [_repository_metadata(name=f"other-{page}-{index}") for index in range(100)]
        for page in range(1, 11)
    }
    discovery.pages[11] = [_repository_metadata(name="target-app")]
    results = search_repositories("team.ghe.com", "target")
    assert [repo.full_name for repo in results] == ["org/target-app"]
    assert len(discovery.cli_calls) == 11


@pytest.mark.parametrize("query", ["", "app"])
def test_empty_page_is_a_success(discovery: _Discovery, query: str) -> None:
    discovery.items = []
    assert search_repositories("team.ghe.com", query, page=2) == ()


@pytest.mark.parametrize("query", ["", "app"])
@pytest.mark.parametrize(
    "invalid",
    [
        None,
        {},
        {"default_branch": None},
        {"name": "other"},
        {"full_name": "org/team/app"},
        {"clone_url": "https://attacker.example/org/app.git"},
        {"clone_url": "https://team.ghe.com.attacker.example/org/app.git"},
        {"clone_url": "http://team.ghe.com/org/app.git"},
        {"clone_url": "https://user:private-upstream-detail@team.ghe.com/org/app.git"},
        {"clone_url": "https://team.ghe.com:443/org/app.git"},
        {"clone_url": "https://team.ghe.com/org/other.git"},
        {"clone_url": "https://team.ghe.com/org/app.git?token=private-upstream-detail"},
        {"clone_url": "https://team.ghe.com/org/app.git#private-upstream-detail"},
        {"clone_url": "https://[broken/org/app.git"},
        {"clone_url": "https://team.ghe.com/org/app.git\n"},
        {"full_name": "../app", "clone_url": "https://team.ghe.com/../app.git"},
        {"default_branch": "x" * 257},
    ],
)
def test_invalid_metadata_fails_whole_page(
    discovery: _Discovery, query: str, invalid: dict[str, object] | None
) -> None:
    metadata = {**_repository_metadata(), **invalid} if invalid else invalid
    discovery.items = [_repository_metadata(), metadata]
    with pytest.raises(PreflightError, match="invalid Repository list") as error:
        search_repositories("team.ghe.com", query)
    assert "No results from this page were returned" in str(error.value)
    assert "private-upstream-detail" not in str(error.value)


@pytest.mark.parametrize("query", ["", "app"])
@pytest.mark.parametrize("items", [None, {}, "invalid", [_repository_metadata()] * 101])
def test_invalid_repository_page_is_explicit(
    discovery: _Discovery, query: str, items: object
) -> None:
    discovery.items = items
    with pytest.raises(PreflightError, match="invalid Repository list"):
        search_repositories("team.ghe.com", query)


def test_search_does_not_return_partial_results_when_later_page_fails(
    discovery: _Discovery, monkeypatch: pytest.MonkeyPatch
) -> None:
    def api(host: str, endpoint: str) -> object:
        if "page=1&" in endpoint:
            return [_repository_metadata(name="app")] + [
                _repository_metadata(name=f"other-{index}") for index in range(99)
            ]
        raise PreflightError("Unable to list GitHub repositories. Check the connection and login.")

    monkeypatch.setattr(github_repositories, "_github_api", api)
    with pytest.raises(PreflightError, match="Unable to list GitHub repositories"):
        search_repositories("team.ghe.com", "app")


@pytest.mark.parametrize("query", ["", "app"])
@pytest.mark.parametrize(
    "failure",
    [
        OSError("private-upstream-detail"),
        subprocess.TimeoutExpired("gh", 30, stderr="private-upstream-detail"),
    ],
)
def test_discovery_failures_are_safe(
    discovery: _Discovery, query: str, failure: OSError | subprocess.TimeoutExpired
) -> None:
    discovery.failure = failure
    with pytest.raises(PreflightError, match="Check|check") as error:
        search_repositories("team.ghe.com", query)
    assert "private-upstream-detail" not in str(error.value)


@pytest.mark.parametrize(
    "returncode, stdout", [(1, "[]"), (1, "private-upstream-detail"), (0, "bad-json")]
)
def test_cli_errors_are_not_empty_results(
    discovery: _Discovery, returncode: int, stdout: str
) -> None:
    discovery.cli_returncode, discovery.cli_stdout = returncode, stdout
    with pytest.raises(PreflightError, match="Unable to list GitHub repositories") as error:
        search_repositories("team.ghe.com")
    assert "private-upstream-detail" not in str(error.value)


@pytest.mark.parametrize("page", [0, -1, True, False])
def test_invalid_page_never_calls_remote(discovery: _Discovery, page: int) -> None:
    with pytest.raises(PreflightError, match="page must be an integer"):
        search_repositories("team.ghe.com", page=page)
    assert discovery.cli_calls == discovery.mcp_calls == []


@pytest.mark.parametrize(
    "host",
    [
        "attacker.example",
        "team.ghe.com.attacker.example",
        "https://github.com",
        "github.com:443",
        "user@github.com",
        "github.com/path",
        "github.com?x=1",
        "github.com\n",
        "GitHub.com",
    ],
)
def test_invalid_host_never_checks_authentication(
    discovery: _Discovery, monkeypatch: pytest.MonkeyPatch, host: str
) -> None:
    def no_auth() -> tuple[str, ...]:
        pytest.fail("Host validation must run before authentication")

    monkeypatch.setattr(github_repositories, "authenticated_hosts", no_auth)
    with pytest.raises(PreflightError, match="Unsupported GitHub host"):
        search_repositories(host)
    assert discovery.cli_calls == discovery.mcp_calls == []


@pytest.mark.parametrize("query", ["", "app"])
def test_unauthenticated_host_fails_before_discovery(
    discovery: _Discovery, monkeypatch: pytest.MonkeyPatch, query: str
) -> None:
    monkeypatch.setattr(github_repositories, "authenticated_hosts", lambda: ())
    with pytest.raises(PreflightError, match="not authenticated"):
        search_repositories("team.ghe.com", query)
    assert discovery.cli_calls == discovery.mcp_calls == []


def test_query_limit_is_checked_before_discovery(discovery: _Discovery) -> None:
    with pytest.raises(PreflightError, match="at most 256 characters"):
        search_repositories("team.ghe.com", "a" * 257)
    assert discovery.cli_calls == discovery.mcp_calls == []


def test_missing_cli_is_explicit(discovery: _Discovery, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(github_repositories, "resolve_github_binary", lambda: None)
    with pytest.raises(PreflightError, match="GitHub CLI is not available"):
        search_repositories("team.ghe.com")
    assert discovery.cli_calls == discovery.mcp_calls == []


def test_cli_fallback_path_is_shared_with_authentication(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def which(_name: str) -> None:
        return None

    def access(path: str, _mode: int) -> bool:
        return path == "/usr/local/bin/gh"

    monkeypatch.setattr(github_repositories.shutil, "which", which)
    monkeypatch.setattr(github_repositories.os, "access", access)

    def run(command: list[str], **_options: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if command[1] == "auth":
            payload: object = {"hosts": {"team.ghe.com": [{"active": True}]}}
        else:
            payload = [_repository_metadata()]
        return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")

    monkeypatch.setattr(github_repositories.subprocess, "run", run)
    assert authenticated_hosts() == ("team.ghe.com",)
    assert len(search_repositories("team.ghe.com")) == 1
    assert all(command[0] == "/usr/local/bin/gh" for command in calls)
