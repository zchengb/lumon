"""Read-only version checks for the Codex executable used by Lumon."""

from __future__ import annotations

import asyncio
import http.client
import re
import subprocess
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field

from lumon.tools.codex import resolve_codex_binary

_LATEST_PACKAGE_URL = "https://registry.npmjs.org/@openai/codex/latest"
_STABLE_VERSION_PATTERN = r"[0-9]{1,8}\.[0-9]{1,8}\.[0-9]{1,8}"
_VERSION_PATTERN = re.compile(
    rf"({_STABLE_VERSION_PATTERN})(-[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*)?"
    r"(?:\+[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*)?"
)


class CodexCliUpdateStatus(StrEnum):
    """A failed check is never presented as an up-to-date installation."""

    UPDATE_AVAILABLE = "update_available"
    UP_TO_DATE = "up_to_date"
    CHECK_FAILED = "check_failed"
    CLI_UNAVAILABLE = "cli_unavailable"


@dataclass(frozen=True, slots=True)
class CodexCliStatus:
    """Display-safe version metadata, without account or configuration details."""

    status: CodexCliUpdateStatus
    binary_path: str
    installed_version: str | None = None
    latest_version: str | None = None


class _PackageVersion(BaseModel):
    version: str = Field(strict=True, pattern=rf"^{_STABLE_VERSION_PATTERN}$", max_length=26)


class CodexCliUpdateChecker:
    """Compare the active CLI with stable package metadata without upgrading it."""

    def __init__(
        self,
        binary: str | None = None,
        *,
        version_reader: Callable[[str], str] | None = None,
        latest_reader: Callable[[], str] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.binary = binary or resolve_codex_binary()
        self._version_reader = version_reader or _read_cli_version
        self._latest_reader = latest_reader or _read_latest_version
        self._clock = clock
        self._cached_release: tuple[float, str | None] | None = None
        self._release_lock = asyncio.Lock()

    async def check(self, *, refresh: bool = False) -> CodexCliStatus:
        """Re-read the installed version; manual refresh bypasses the release cache."""

        try:
            installed = await asyncio.to_thread(self._version_reader, self.binary)
            installed_order = _version_order(installed)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            return CodexCliStatus(CodexCliUpdateStatus.CLI_UNAVAILABLE, self.binary)

        latest = await self._latest_version(refresh=refresh)
        if latest is None:
            return CodexCliStatus(CodexCliUpdateStatus.CHECK_FAILED, self.binary, installed)
        status = CodexCliUpdateStatus.UP_TO_DATE
        if _version_order(latest) > installed_order:
            status = CodexCliUpdateStatus.UPDATE_AVAILABLE
        return CodexCliStatus(status, self.binary, installed, latest)

    async def _latest_version(self, *, refresh: bool) -> str | None:
        async with self._release_lock:
            if not refresh and self._cached_release is not None:
                checked_at, latest = self._cached_release
                cache_seconds = 600 if latest is not None else 60
                if self._clock() - checked_at < cache_seconds:
                    return latest
            try:
                latest = await asyncio.to_thread(self._latest_reader)
                if not re.fullmatch(_STABLE_VERSION_PATTERN, latest):
                    raise ValueError("Invalid Codex stable release version.")
            except (OSError, ValueError, http.client.HTTPException):
                latest = None
            self._cached_release = (self._clock(), latest)
            return latest


def _version_order(version: str) -> tuple[int, int, int, bool]:
    match = _VERSION_PATTERN.fullmatch(version)
    if match is None or len(version) > 80:
        raise ValueError("Invalid Codex CLI version.")
    major, minor, patch = match[1].split(".")
    # Only compare with stable releases: a same-version prerelease sorts below stable.
    return int(major), int(minor), int(patch), match[2] is None


def _read_cli_version(binary: str) -> str:
    completed = subprocess.run(
        [binary, "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        timeout=3,
        check=False,
    )
    prefix = "codex-cli "
    output = completed.stdout.strip()
    if completed.returncode != 0 or not output.startswith(prefix):
        raise ValueError("Unable to read Codex CLI version.")
    return output.removeprefix(prefix)


def _read_latest_version() -> str:
    request = urllib.request.Request(
        _LATEST_PACKAGE_URL,
        headers={"Accept": "application/json", "User-Agent": "Lumon Codex update check"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        if response.status != 200:
            raise ValueError("Codex package registry did not return release metadata.")
        payload = response.read(65_537)
    if len(payload) > 65_536:
        raise ValueError("Codex package metadata exceeded the response limit.")
    return _PackageVersion.model_validate_json(payload).version
