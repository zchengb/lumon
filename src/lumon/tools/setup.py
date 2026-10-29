"""Shared, read-only setup checks for CLI and Dashboard onboarding."""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass

from lumon.tools.codex import resolve_codex_binary
from lumon.tools.github_auth import CommandRunner, DependencyState, github_authentication
from lumon.tools.github_repositories import resolve_github_binary


@dataclass(frozen=True, slots=True)
class DependencyCheck:
    name: str
    state: DependencyState
    action: str | None = None
    documentation_url: str | None = None


@dataclass(frozen=True, slots=True)
class SetupReport:
    checks: tuple[DependencyCheck, ...]
    hosts: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return all(check.state == "ready" for check in self.checks)


class SetupInspector:
    """Inspect executable and login boundaries without starting an Agent."""

    def __init__(self, runner: CommandRunner | None = None) -> None:
        self._run = runner or subprocess.run

    def inspect(self) -> SetupReport:
        github = github_authentication(resolve_github_binary(), runner=self._run)
        github_action = {
            "missing": "brew install gh" if sys.platform == "darwin" else "https://cli.github.com/",
            "incompatible": "brew upgrade gh"
            if sys.platform == "darwin"
            else "https://cli.github.com/",
            "needs_login": "gh auth login --hostname <github-host> --web",
            "error": "gh auth status",
        }.get(github.state)
        git_available = bool(shutil.which("git"))
        git_install = (
            "brew install git" if sys.platform == "darwin" else "https://git-scm.com/downloads"
        )
        git = DependencyCheck(
            "git",
            "ready" if git_available else "missing",
            None if git_available else git_install,
            "https://git-scm.com/downloads",
        )
        return SetupReport(
            (
                git,
                DependencyCheck("gh", github.state, github_action, "https://cli.github.com/"),
                self._codex_check(),
            ),
            github.hosts,
        )

    def _codex_check(self) -> DependencyCheck:
        documentation = "https://developers.openai.com/codex/cli/"
        binary = resolve_codex_binary()
        if not shutil.which(binary):
            return DependencyCheck(
                "codex",
                "missing",
                "curl -fsSL https://chatgpt.com/codex/install.sh | sh",
                documentation,
            )
        try:
            result = self._run(
                [binary, "login", "status"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return DependencyCheck("codex", "error", "codex login status", documentation)
        if result.returncode == 0:
            return DependencyCheck("codex", "ready", documentation_url=documentation)
        # A non-zero status can be a CLI failure, not only a missing login.
        if "not logged in" in (result.stdout + result.stderr).lower():
            return DependencyCheck("codex", "needs_login", "codex login", documentation)
        return DependencyCheck("codex", "error", "codex login status", documentation)
