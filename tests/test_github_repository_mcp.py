"""Repository-scoped GitHub MCP behavior without a real account or network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lumon.tools.github_mcp_proxy import (
    GithubMcpProxy,
    allowed_tool_call,
    github_endpoint,
    github_server_name,
    selected_repositories,
    workspace_git_environment,
    workspace_mcp_config,
)
from lumon.tools.github_repositories import search_repositories
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


def test_search_validates_remote_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "lumon.tools.github_repositories.authenticated_hosts", lambda: ("team.ghe.com",)
    )

    def handle(self: GithubMcpProxy, message: dict[str, object]) -> list[dict[str, object]]:
        del self
        if message.get("method") != "tools/call":
            return []
        result = {
            "items": [
                {
                    "name": "app",
                    "full_name": "org/app",
                    "default_branch": "main",
                    "clone_url": "https://team.ghe.com/org/app.git",
                },
                {
                    "name": "bad",
                    "full_name": "org/bad",
                    "default_branch": "main",
                    "clone_url": "https://attacker.example/org/bad.git",
                },
            ]
        }
        return [{"result": {"content": [{"type": "text", "text": json.dumps(result)}]}}]

    monkeypatch.setattr(GithubMcpProxy, "handle", handle)
    results = search_repositories("team.ghe.com", "app")
    assert len(results) == 1
    assert (results[0].full_name, results[0].branch) == ("org/app", "main")
