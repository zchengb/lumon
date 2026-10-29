"""Read GitHub CLI authentication without exposing credential material."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, cast

from lumon.tools.github_mcp_proxy import github_endpoint

DependencyState = Literal["ready", "missing", "needs_login", "incompatible", "error"]
CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True, slots=True)
class GithubAuthentication:
    state: DependencyState
    hosts: tuple[str, ...] = ()


def github_authentication(
    executable: str | None, *, runner: CommandRunner | None = None
) -> GithubAuthentication:
    """Check the required JSON capability and active, healthy logins together."""

    if executable is None:
        return GithubAuthentication("missing")
    run = runner or subprocess.run
    try:
        result = run(
            [executable, "auth", "status", "--json", "hosts"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return GithubAuthentication("error")
    if "unknown flag: --json" in result.stderr:
        return GithubAuthentication("incompatible")
    if result.returncode != 0:
        return GithubAuthentication("error")
    try:
        payload: object = json.loads(result.stdout)
        hosts = _healthy_hosts(payload)
    except (ValueError, TypeError):
        return GithubAuthentication("error")
    return GithubAuthentication("ready" if hosts else "needs_login", hosts)


def _healthy_hosts(payload: object) -> tuple[str, ...]:
    if not isinstance(payload, dict):
        raise ValueError("Invalid GitHub status")
    hosts = cast(dict[str, object], payload).get("hosts")
    if not isinstance(hosts, dict):
        raise ValueError("Invalid GitHub status")
    healthy: list[str] = []
    for host, accounts in cast(dict[str, object], hosts).items():
        try:
            github_endpoint(host)
        except ValueError:
            continue
        if not isinstance(accounts, list):
            raise ValueError("Invalid GitHub accounts")
        for item in cast(list[object], accounts):
            if not isinstance(item, dict):
                raise ValueError("Invalid GitHub account")
            account = cast(dict[str, object], item)
            if account.get("active") is True and account.get("state", "success") == "success":
                healthy.append(host)
                break
    return tuple(sorted(healthy))
