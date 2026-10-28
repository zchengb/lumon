"""Discover GitHub repositories through the authenticated GitHub MCP."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import cast
from urllib.parse import urlsplit

from lumon.errors import PreflightError
from lumon.tools.github_mcp_proxy import GithubMcpProxy, github_endpoint, github_server_name


@dataclass(frozen=True, slots=True)
class GithubRepository:
    name: str
    full_name: str
    clone_url: str
    branch: str
    mcp_server: str
    auto_scan: bool = True
    auto_delivery: bool = True


def authenticated_hosts() -> tuple[str, ...]:
    """List authenticated GitHub hosts without exposing accounts or tokens."""

    executable = shutil.which("gh")
    if executable is None:
        for candidate in ("/opt/homebrew/bin/gh", "/usr/local/bin/gh"):
            if os.access(candidate, os.X_OK):
                executable = candidate
                break
    if executable is None:
        return ()
    try:
        result = subprocess.run(
            [executable, "auth", "status", "--json", "hosts"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        payload: object = json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return ()
    if result.returncode != 0 or not isinstance(payload, dict):
        return ()
    hosts = cast(dict[str, object], payload).get("hosts")
    if not isinstance(hosts, dict):
        return ()
    valid: list[str] = []
    for host, accounts in cast(dict[str, object], hosts).items():
        try:
            github_endpoint(host)
        except ValueError:
            continue
        if isinstance(accounts, list) and any(
            isinstance(account, dict) and cast(dict[str, object], account).get("active") is True
            for account in cast(list[object], accounts)
        ):
            valid.append(host)
    return tuple(sorted(valid))


def search_repositories(host: str, query: str) -> tuple[GithubRepository, ...]:
    """Search one GitHub MCP host and return safe clone metadata."""

    if not query.strip() or len(query) > 256:
        raise PreflightError("Enter a Repository or organization name to search.")
    if host not in authenticated_hosts():
        raise PreflightError("GitHub CLI is not authenticated for this host.")
    try:
        proxy = GithubMcpProxy(host, None)
        proxy.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "lumon", "version": "1"},
                },
            }
        )
        proxy.handle({"jsonrpc": "2.0", "method": "notifications/initialized"})
        replies = proxy.handle(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "search_repositories",
                    "arguments": {"query": query.strip(), "perPage": 100, "minimal_output": False},
                },
            }
        )
        response = _payload(replies)
    except (OSError, ValueError) as exc:
        raise PreflightError("Unable to query GitHub MCP. Check its connection and login.") from exc
    items = response.get("items")
    if not isinstance(items, list):
        raise PreflightError("GitHub MCP returned an invalid Repository list.")
    repositories: list[GithubRepository] = []
    for item in cast(list[object], items):
        if not isinstance(item, dict):
            continue
        repo = cast(dict[str, object], item)
        name, full_name = repo.get("name"), repo.get("full_name")
        clone_url, branch = repo.get("clone_url"), repo.get("default_branch")
        if not all(
            isinstance(value, str) and value for value in (name, full_name, clone_url, branch)
        ):
            continue
        assert isinstance(name, str) and isinstance(full_name, str)
        assert isinstance(clone_url, str) and isinstance(branch, str)
        parsed = urlsplit(clone_url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != host
            or parsed.username
            or parsed.password
            or parsed.path.removeprefix("/").removesuffix(".git") != full_name
            or full_name.split("/")[-1] != name
        ):
            continue
        repositories.append(
            GithubRepository(name, full_name, clone_url, branch, github_server_name(host))
        )
    return tuple(repositories)


def _payload(replies: list[dict[str, object]]) -> dict[str, object]:
    for reply in replies:
        result = reply.get("result")
        if not isinstance(result, dict):
            continue
        result = cast(dict[str, object], result)
        if result.get("isError"):
            break
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return cast(dict[str, object], structured)
        content = result.get("content")
        if isinstance(content, list):
            for block in cast(list[object], content):
                if isinstance(block, dict):
                    text = cast(dict[str, object], block).get("text")
                    if isinstance(text, str):
                        value: object = json.loads(text)
                        if isinstance(value, dict):
                            return cast(dict[str, object], value)
    raise ValueError("Invalid GitHub MCP response")
