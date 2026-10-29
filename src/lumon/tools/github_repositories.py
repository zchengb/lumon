"""List account repositories with ``gh`` and search through GitHub MCP."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import cast
from urllib.parse import urlsplit

from lumon.errors import InvalidInputError, PreflightError
from lumon.tools.github_auth import github_authentication
from lumon.tools.github_mcp_proxy import GithubMcpProxy, github_endpoint, github_server_name
from lumon.workspace.model import RepositorySpec
from lumon.workspace.settings import validate_delivery_target_branch

_OWNER_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
_REPOSITORY_NAME = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")


@dataclass(frozen=True, slots=True)
class GithubRepository:
    name: str
    full_name: str
    clone_url: str
    branch: str
    mcp_server: str
    auto_scan: bool = True
    auto_delivery: bool = True


def resolve_github_binary() -> str | None:
    executable = shutil.which("gh")
    if executable is None:
        for candidate in ("/opt/homebrew/bin/gh", "/usr/local/bin/gh"):
            if os.access(candidate, os.X_OK):
                executable = candidate
                break
    return executable


def authenticated_hosts() -> tuple[str, ...]:
    """List authenticated GitHub hosts without exposing accounts or tokens."""
    authentication = github_authentication(resolve_github_binary())
    errors = {
        "missing": "GitHub CLI is not installed. See https://cli.github.com/.",
        "incompatible": (
            "Upgrade GitHub CLI: this version does not support JSON authentication status."
        ),
        "error": (
            "Could not check GitHub CLI authentication. Run `gh auth status` or `lumon doctor`."
        ),
    }
    if authentication.state in errors:
        raise PreflightError(errors[authentication.state])
    return authentication.hosts


def search_repositories(
    host: str, query: str = "", *, page: int = 1, organization: str = ""
) -> tuple[GithubRepository, ...]:
    """Return one page of at most 100 repositories; blank queries list the account.

    Callers must fetch the next page when a page contains 100 repositories.
    Invalid or incomplete pages fail instead of silently dropping repositories.
    """

    try:
        github_endpoint(host)
    except ValueError as exc:
        raise PreflightError("Unsupported GitHub host.") from exc
    if type(page) is not int or page < 1:
        raise PreflightError("Repository page must be an integer greater than zero.")
    if len(query) > 256:
        raise PreflightError("Repository search query must be at most 256 characters.")
    if host not in authenticated_hosts():
        raise PreflightError("GitHub CLI is not authenticated for this host.")
    if organization and not _OWNER_NAME.fullmatch(organization):
        raise PreflightError("Invalid GitHub organization.")
    query = query.strip()
    if query and organization:
        query = f"org:{organization} {query}"
    if query:
        items = _search_repository_page(host, query, page)
    else:
        items = _account_repository_page(host, page, organization)
    try:
        if not isinstance(items, list):
            raise ValueError("Invalid Repository page")
        entries = cast(list[object], items)
        if len(entries) > 100:
            raise ValueError("Invalid Repository page")
        return tuple(_repository(host, item) for item in entries)
    except ValueError as exc:
        raise PreflightError(
            "GitHub returned an invalid Repository list. No results from this page were returned."
        ) from exc


def _account_repository_page(host: str, page: int, organization: str = "") -> object:
    owner = f"/orgs/{organization}/repos" if organization else "/user/repos"
    return _github_api(host, f"{owner}?per_page=100&page={page}&sort=full_name&direction=asc")


def _github_api(host: str, endpoint: str) -> object:
    executable = resolve_github_binary()
    if executable is None:
        raise PreflightError("GitHub CLI is not available.")
    environment = os.environ.copy()
    environment["GH_PROMPT_DISABLED"] = "1"
    environment["GH_NO_UPDATE_NOTIFIER"] = "1"
    try:
        result = subprocess.run(
            [executable, "api", "--hostname", host, endpoint],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
            env=environment,
        )
        if result.returncode != 0:
            raise PreflightError(
                "Unable to list GitHub repositories. Check the connection and login."
            )
        payload: object = json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        raise PreflightError(
            "Unable to list GitHub repositories. Check the connection and login."
        ) from exc
    return payload


def _search_repository_page(host: str, query: str, page: int) -> object:
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
                    "arguments": {
                        "query": query,
                        "page": page,
                        "perPage": 100,
                        "minimal_output": False,
                    },
                },
            }
        )
        response = _payload(replies)
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        raise PreflightError("Unable to query GitHub MCP. Check its connection and login.") from exc
    if response.get("incomplete_results", False) is not False:
        raise PreflightError(
            "GitHub search returned incomplete results. Narrow the search and retry."
        )
    total_count = response.get("total_count")
    if isinstance(total_count, int) and total_count > 1000:
        raise PreflightError(
            "GitHub search is limited to 1,000 repositories. Narrow the search and retry."
        )
    return response.get("items")


def _repository(host: str, item: object) -> GithubRepository:
    if not isinstance(item, dict):
        raise ValueError("Invalid Repository metadata")
    repo = cast(dict[str, object], item)
    name, full_name = repo.get("name"), repo.get("full_name")
    clone_url, branch = repo.get("clone_url"), repo.get("default_branch")
    if not all(isinstance(value, str) and value for value in (name, full_name, clone_url, branch)):
        raise ValueError("Invalid Repository metadata")
    assert isinstance(name, str) and isinstance(full_name, str)
    assert isinstance(clone_url, str) and isinstance(branch, str)
    if len(name) > 128 or len(full_name) > 256 or len(clone_url) > 1024 or len(branch) > 256:
        raise ValueError("Invalid Repository metadata")
    if (
        not _REPOSITORY_NAME.fullmatch(full_name)
        or any(part in {".", ".."} for part in full_name.split("/"))
        or full_name.split("/")[-1] != name
    ):
        raise ValueError("Invalid Repository metadata")
    expected_url = f"https://{host}/{full_name}"
    if clone_url not in {expected_url, f"{expected_url}.git"}:
        raise ValueError("Invalid Repository metadata")
    return GithubRepository(name, full_name, clone_url, branch, github_server_name(host))


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


def repository_organizations(host: str, *, page: int = 1) -> tuple[str, ...]:
    """List one page of organizations available to the signed-in account."""
    _require_source(host)
    if type(page) is not int or page < 1:
        raise PreflightError("Invalid organization page.")
    payload = _github_api(host, f"/user/orgs?per_page=100&page={page}")
    if not isinstance(payload, list) or len(cast(list[object], payload)) > 100:
        raise PreflightError("GitHub returned invalid organization data.")
    organizations: list[str] = []
    for item in cast(list[object], payload):
        name = cast(dict[str, object], item).get("login") if isinstance(item, dict) else None
        if not isinstance(name, str) or not _OWNER_NAME.fullmatch(name):
            raise PreflightError("GitHub returned invalid organization data.")
        organizations.append(name)
    return tuple(organizations)


def repository_branches(host: str, repository: str, *, page: int = 1) -> tuple[str, ...]:
    """Read one page of branch names before a Workspace exists."""
    _require_source(host)
    if not _REPOSITORY_NAME.fullmatch(repository) or any(
        part in {".", ".."} for part in repository.split("/")
    ):
        raise PreflightError("Invalid GitHub repository.")
    if type(page) is not int or page < 1:
        raise PreflightError("Invalid branch page.")
    payload = _github_api(host, f"/repos/{repository}/branches?per_page=100&page={page}")
    if not isinstance(payload, list) or len(cast(list[object], payload)) > 100:
        raise PreflightError("GitHub returned invalid branch data.")
    branches: list[str] = []
    for item in cast(list[object], payload):
        name = cast(dict[str, object], item).get("name") if isinstance(item, dict) else None
        if not isinstance(name, str) or not name or name != name.strip():
            raise PreflightError("GitHub returned invalid branch data.")
        try:
            validate_delivery_target_branch(name)
        except InvalidInputError as exc:
            raise PreflightError("GitHub returned invalid branch data.") from exc
        branches.append(name)
    return tuple(branches)


def _require_source(host: str) -> None:
    try:
        github_endpoint(host)
    except ValueError as exc:
        raise PreflightError("Unsupported GitHub host.") from exc
    if host not in authenticated_hosts():
        raise PreflightError("GitHub CLI is not authenticated for this host. Run lumon doctor.")


def repository_spec(item: GithubRepository) -> RepositorySpec:
    """Validate a picked Repository consistently across HTTP and CLI callers."""
    try:
        parsed = urlsplit(item.clone_url)
        server = github_server_name(parsed.hostname or "")
        port = parsed.port
    except ValueError:
        raise InvalidInputError("Invalid GitHub MCP Repository source.") from None
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or port is not None
        or parsed.query
        or parsed.fragment
        or not _REPOSITORY_NAME.fullmatch(item.full_name)
        or any(part in {".", ".."} for part in item.full_name.split("/"))
        or parsed.path.removeprefix("/").removesuffix(".git") != item.full_name
        or item.full_name.split("/")[-1] != item.name
        or item.mcp_server != server
    ):
        raise InvalidInputError("Invalid GitHub MCP Repository source.")
    if not item.branch or item.branch != item.branch.strip():
        raise InvalidInputError("Select a target branch.")
    validate_delivery_target_branch(item.branch)
    return RepositorySpec(
        item.name, item.clone_url, item.branch, item.mcp_server, item.auto_scan, item.auto_delivery
    )
