"""Expose the official GitHub MCP through the current ``gh`` login.

The token stays in this short-lived MCP process instead of the Agent environment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from lumon.errors import LumonError
from lumon.workspace.config import load_workspace_config
from lumon.workspace.layout import WorkspaceLayout

_HOST = re.compile(r"(?:github\.com|[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.ghe\.com)\Z")
_REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
_SCOPED_TOOLS = frozenset(
    {
        "get_commit",
        "get_file_contents",
        "list_branches",
        "list_commits",
        "search_code",
        "search_commits",
    }
)
_DISCOVERY_TOOLS = frozenset({"search_repositories", "list_branches"})
_METHODS = frozenset(
    {
        "initialize",
        "notifications/initialized",
        "notifications/cancelled",
        "ping",
        "tools/list",
        "tools/call",
    }
)
_MAX_RESPONSE = 8 * 1024 * 1024


def github_endpoint(host: str) -> str:
    """Return only an official GitHub MCP destination for an authenticated host."""

    if not _HOST.fullmatch(host):
        raise ValueError("Unsupported GitHub host.")
    if host == "github.com":
        return "https://api.githubcopilot.com/mcp/"
    return f"https://copilot-api.{host}/mcp"


def github_server_name(host: str) -> str:
    """Derive the same safe MCP name for a GitHub account and its Workspace."""

    github_endpoint(host)
    digest = hashlib.sha256(host.encode()).hexdigest()[:12]
    return f"lumon_github_{digest}"


def workspace_github_hosts(workspace: Path) -> tuple[str, ...]:
    layout = WorkspaceLayout.from_root(workspace)
    if not layout.workspace_config.is_file():
        return ()
    config = load_workspace_config(layout.workspace_config)
    hosts: set[str] = set()
    for repository in config.repositories:
        if not repository.mcp_server:
            continue
        host = urlsplit(repository.url).hostname
        try:
            if host and repository.mcp_server == github_server_name(host):
                hosts.add(host)
        except ValueError:
            continue
    return tuple(sorted(hosts))


def workspace_mcp_config(workspace: Path) -> tuple[str, ...]:
    """Attach a scoped GitHub MCP to this execution without changing user settings."""

    layout = WorkspaceLayout.from_root(workspace)
    result: list[str] = []
    for host in workspace_github_hosts(workspace):
        args = [
            "-m",
            "lumon.tools.github_mcp_proxy",
            "--host",
            host,
            "--workspace",
            str(layout.root),
        ]
        server = github_server_name(host)
        result.append(
            f"mcp_servers.{server}={{command={json.dumps(sys.executable)},args={json.dumps(args)}}}"
        )
    return tuple(result)


def github_credential_helper() -> str | None:
    executable = shutil.which("gh")
    if executable is None:
        for candidate in ("/opt/homebrew/bin/gh", "/usr/local/bin/gh"):
            if Path(candidate).is_file() and os.access(candidate, os.X_OK):
                executable = candidate
                break
    return f"!{shlex.quote(executable)} auth git-credential" if executable else None


def workspace_git_environment(
    workspace: Path, environment: Mapping[str, str] | None
) -> Mapping[str, str] | None:
    """Use the authenticated GH helper only inside this execution, not global Git config."""

    hosts = workspace_github_hosts(workspace)
    helper = github_credential_helper() if hosts else None
    if not helper:
        return environment
    result = dict(environment) if environment is not None else os.environ.copy()
    try:
        count = int(result.get("GIT_CONFIG_COUNT", "0"))
    except ValueError:
        return environment
    if count < 0 or count > 1000:
        return environment
    result.setdefault("GIT_TERMINAL_PROMPT", "0")
    for host in hosts:
        for value in ("", helper):
            result[f"GIT_CONFIG_KEY_{count}"] = f"credential.https://{host}.helper"
            result[f"GIT_CONFIG_VALUE_{count}"] = value
            count += 1
    result["GIT_CONFIG_COUNT"] = str(count)
    return result


def selected_repositories(workspace: Path, host: str, server: str) -> frozenset[str]:
    """Return only the GitHub Repositories explicitly selected by this Workspace."""

    config = load_workspace_config(WorkspaceLayout.from_root(workspace).workspace_config)
    names: set[str] = set()
    for repository in config.repositories:
        if repository.mcp_server != server:
            continue
        url = urlsplit(repository.url)
        name = url.path.strip("/").removesuffix(".git")
        if url.hostname == host and _REPOSITORY.fullmatch(name):
            names.add(name.casefold())
    return frozenset(names)


def allowed_tool_call(
    tool: str, arguments: object, *, discovery: bool, repositories: frozenset[str]
) -> bool:
    """Guard GitHub reads before they leave the local MCP proxy."""

    if tool not in (_DISCOVERY_TOOLS if discovery else _SCOPED_TOOLS):
        return False
    if not isinstance(arguments, dict):
        return False
    values = cast(dict[str, object], arguments)
    if discovery and tool == "search_repositories":
        return isinstance(values.get("query"), str) and bool(str(values["query"]).strip())
    if tool in {"search_code", "search_commits"}:
        query = values.get("query")
        if (
            not isinstance(query, str)
            or re.search(r"\b(?:OR|NOT)\b", query, re.I)
            or re.search(r"[\"'()]", query)
        ):
            return False
        scopes = re.findall(r"(?:^|\s)repo:([^\s]+)", query, re.I)
        return bool(scopes) and all(scope.casefold() in repositories for scope in scopes)
    owner = values.get("owner")
    repository = values.get("repo")
    if not isinstance(owner, str) or not isinstance(repository, str):
        return False
    name = f"{owner}/{repository}"
    return bool(_REPOSITORY.fullmatch(name)) and (discovery or name.casefold() in repositories)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args: object, **kwargs: object) -> None:
        return None


class GithubMcpProxy:
    """Forward bounded MCP requests while keeping credentials and scope local."""

    def __init__(self, host: str, workspace: Path | None) -> None:
        self.host = host
        self.endpoint = github_endpoint(host)
        self.workspace = workspace
        self.server = github_server_name(host)
        self.session: str | None = None
        self.version: str | None = None
        self._opener = build_opener(_NoRedirect)

    def handle(self, message: dict[str, object]) -> list[dict[str, object]]:
        method = message.get("method")
        params = message.get("params")
        if not isinstance(method, str) or method not in _METHODS:
            return [_error(message, "Unsupported GitHub MCP method.")] if "id" in message else []
        if method == "tools/call":
            if not isinstance(params, dict):
                return [_error(message, "Invalid MCP tool request.")]
            values = cast(dict[str, object], params)
            tool = values.get("name")
            repositories: frozenset[str] = (
                selected_repositories(self.workspace, self.host, self.server)
                if self.workspace is not None
                else frozenset[str]()
            )
            if not isinstance(tool, str) or not allowed_tool_call(
                tool,
                values.get("arguments"),
                discovery=self.workspace is None,
                repositories=repositories,
            ):
                return [_error(message, "Repository is outside the permitted Workspace scope.")]
        replies = self._request(message)
        if method == "initialize":
            for reply in replies:
                result = reply.get("result")
                if isinstance(result, dict):
                    values = cast(dict[str, object], result)
                    version = values.get("protocolVersion")
                    if isinstance(version, str):
                        self.version = version
        if method == "tools/list":
            allowed = _DISCOVERY_TOOLS if self.workspace is None else _SCOPED_TOOLS
            for reply in replies:
                result = reply.get("result")
                if isinstance(result, dict):
                    values = cast(dict[str, object], result)
                    entries = values.get("tools")
                    if isinstance(entries, list):
                        values["tools"] = [
                            item
                            for item in cast(list[object], entries)
                            if isinstance(item, dict)
                            and cast(dict[str, object], item).get("name") in allowed
                        ]
        return replies

    def _request(self, message: dict[str, object]) -> list[dict[str, object]]:
        token = _github_token(self.host)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        if self.version:
            headers["MCP-Protocol-Version"] = self.version
        request = Request(
            self.endpoint, data=json.dumps(message).encode(), headers=headers, method="POST"
        )
        try:
            with self._opener.open(request, timeout=30) as response:
                self.session = response.headers.get("Mcp-Session-Id") or self.session
                body = response.read(_MAX_RESPONSE + 1)
                content_type = response.headers.get("Content-Type", "")
        except (HTTPError, URLError, OSError, TimeoutError) as exc:
            raise ValueError("GitHub MCP request failed; check the connection and login.") from exc
        if len(body) > _MAX_RESPONSE:
            raise ValueError("GitHub MCP response exceeded the size limit.")
        if not body:
            return []
        text = body.decode("utf-8")
        if "text/event-stream" in content_type:
            frames = [line[5:].strip() for line in text.splitlines() if line.startswith("data:")]
        else:
            frames = [text]
        replies: list[dict[str, object]] = []
        for frame in frames:
            value: object = json.loads(frame)
            if isinstance(value, dict):
                replies.append(cast(dict[str, object], value))
        return replies


def _github_token(host: str) -> str:
    executable = shutil.which("gh")
    if executable is None:
        for candidate in ("/opt/homebrew/bin/gh", "/usr/local/bin/gh"):
            if Path(candidate).is_file() and os.access(candidate, os.X_OK):
                executable = candidate
                break
    if executable is None:
        raise ValueError("GitHub CLI is not available.")
    environment = os.environ.copy()
    environment["GH_PROMPT_DISABLED"] = "1"
    environment["GH_NO_UPDATE_NOTIFIER"] = "1"
    try:
        result = subprocess.run(
            [executable, "auth", "token", "--hostname", host],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("GitHub CLI authentication is unavailable.") from exc
    if result.returncode != 0 or not result.stdout.strip():
        raise ValueError("GitHub CLI authentication is unavailable.")
    return result.stdout.strip()


def _error(message: dict[str, object], description: str) -> dict[str, object]:
    return {
        "jsonrpc": "2.0",
        "id": message.get("id"),
        "error": {"code": -32000, "message": description},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--workspace", type=Path)
    arguments = parser.parse_args()
    try:
        proxy = GithubMcpProxy(arguments.host, arguments.workspace)
    except ValueError:
        raise SystemExit(2) from None
    for line in sys.stdin:
        message: dict[str, object] | None = None
        try:
            value: object = json.loads(line)
            if not isinstance(value, dict):
                continue
            message = cast(dict[str, object], value)
            replies = proxy.handle(message)
        except (LumonError, ValueError, OSError, UnicodeDecodeError):
            replies = (
                [_error(message, "GitHub MCP is unavailable.")]
                if message and "id" in message
                else []
            )
        for reply in replies:
            print(json.dumps(reply, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
