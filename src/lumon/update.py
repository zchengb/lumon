"""GitHub Release based update support for the Lumon CLI."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Protocol, cast

from lumon.errors import UpdateError
from lumon.version import __version__

DEFAULT_GITHUB_REPOSITORY = "zchengb/lumon"
_GITHUB_API = "https://api.github.com"
_VERSION_PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True, slots=True, order=True)
class ReleaseVersion:
    """A comparable stable semantic version used by the release channel."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> ReleaseVersion:
        """Parse a stable ``MAJOR.MINOR.PATCH`` version or tag."""

        match = _VERSION_PATTERN.fullmatch(value.strip())
        if match is None:
            raise UpdateError(f"Unsupported release version: {value}")
        return cls(*(int(part) for part in match.groups()))

    def __str__(self) -> str:
        """Render the version without a leading tag prefix."""

        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    """A downloadable file attached to a GitHub Release."""

    name: str
    api_url: str
    download_url: str


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    """The stable release metadata needed by the updater."""

    tag_name: str
    version: ReleaseVersion
    assets: tuple[ReleaseAsset, ...]


@dataclass(frozen=True, slots=True)
class UpdateRequest:
    """The user-controlled options for one update check or update."""

    repository: str
    check_only: bool = False
    python_version: str = "3.12"


class UpdateStatus(StrEnum):
    """Stable result states exposed by the CLI."""

    UP_TO_DATE = "up_to_date"
    UPDATE_AVAILABLE = "update_available"
    UPDATED = "updated"


@dataclass(frozen=True, slots=True)
class UpdateResult:
    """A machine-readable update result."""

    status: UpdateStatus
    current_version: str
    latest_version: str
    repository: str

    def to_dict(self) -> dict[str, str]:
        """Convert the result to the public JSON shape."""

        return {
            "status": self.status.value,
            "current_version": self.current_version,
            "latest_version": self.latest_version,
            "repository": self.repository,
        }


class ReleaseSource(Protocol):
    """The internal seam used by the update service and its tests."""

    def latest(self, repository: str) -> ReleaseInfo:
        """Return the latest stable release for a repository."""

        ...

    def download(self, asset: ReleaseAsset) -> bytes:
        """Download one release asset."""

        ...


class ToolInstaller(Protocol):
    """The internal seam for replacing the installed CLI."""

    def install(self, wheel: Path, python_version: str) -> None:
        """Install a verified wheel into the CLI tool environment."""

        ...


class GitHubReleaseClient:
    """Read stable release metadata and assets from GitHub's API."""

    def __init__(self, token: str | None = None, timeout: float = 30.0) -> None:
        self.token = token
        self.timeout = timeout

    def latest(self, repository: str) -> ReleaseInfo:
        """Fetch the latest non-draft, non-prerelease GitHub Release."""

        _validate_repository(repository)
        payload = self._request_json(f"{_GITHUB_API}/repos/{repository}/releases/latest")
        try:
            tag_name = str(payload["tag_name"])
            version = ReleaseVersion.parse(tag_name)
            raw_assets = payload["assets"]
            if not isinstance(raw_assets, list):
                raise TypeError("assets is not a list")
            asset_payloads = cast(list[object], raw_assets)
            assets = tuple(self._asset_from_payload(item) for item in asset_payloads)
        except (KeyError, TypeError, ValueError) as exc:
            raise UpdateError("GitHub returned an invalid release description.") from exc
        return ReleaseInfo(tag_name, version, assets)

    def download(self, asset: ReleaseAsset) -> bytes:
        """Download a release asset without exposing credentials in output."""

        url = asset.api_url or asset.download_url
        if not url:
            raise UpdateError(f"Release asset has no download URL: {asset.name}")
        return self._request_bytes(url, accept="application/octet-stream")

    def _asset_from_payload(self, payload: object) -> ReleaseAsset:
        if not isinstance(payload, dict):
            raise TypeError("asset is not an object")
        fields = cast(dict[str, object], payload)
        name = fields.get("name")
        api_url = fields.get("url")
        download_url = fields.get("browser_download_url")
        if (
            not isinstance(name, str)
            or not name
            or not isinstance(api_url, str)
            or not api_url
            or not isinstance(download_url, str)
            or not download_url
        ):
            raise ValueError("asset fields are incomplete")
        return ReleaseAsset(name, api_url, download_url)

    def _request_json(self, url: str) -> dict[str, object]:
        try:
            payload = json.loads(self._request_bytes(url, accept="application/vnd.github+json"))
        except json.JSONDecodeError as exc:
            raise UpdateError("GitHub returned malformed JSON.") from exc
        if not isinstance(payload, dict):
            raise UpdateError("GitHub returned an invalid JSON response.")
        return cast(dict[str, object], payload)

    def _request_bytes(self, url: str, accept: str) -> bytes:
        headers = {
            "Accept": accept,
            "User-Agent": f"lumon/{__version__}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            raise UpdateError(f"GitHub request failed with HTTP {exc.code}.") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise UpdateError("Unable to reach GitHub to check for updates.") from exc


class UvToolInstaller:
    """Replace Lumon through the uv-managed isolated tool environment."""

    def install(self, wheel: Path, python_version: str) -> None:
        """Install a local wheel with ``uv`` without invoking a shell."""

        uv = shutil.which("uv")
        if uv is None:
            raise UpdateError("Cannot update Lumon because uv is not available on PATH.")
        try:
            subprocess.run(
                [uv, "tool", "install", "--force", "--python", python_version, str(wheel)],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise UpdateError("uv failed while installing the Lumon update.") from exc


class PythonVenvInstaller:
    """Replace Lumon inside the venv created by the Shell installer."""

    def __init__(self, python_executable: str) -> None:
        self.python_executable = python_executable

    def install(self, wheel: Path, python_version: str) -> None:
        """Install a verified wheel into the current Python virtual environment."""

        del python_version
        try:
            subprocess.run(
                [
                    self.python_executable,
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    "--no-cache-dir",
                    "--force-reinstall",
                    str(wheel),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise UpdateError("pip failed while installing the Lumon update.") from exc


class UpdateService:
    """Coordinate release discovery, verification, and CLI replacement."""

    def __init__(
        self,
        source: ReleaseSource,
        installer: ToolInstaller,
        current_version: str = __version__,
    ) -> None:
        self.source = source
        self.installer = installer
        self.current_version = ReleaseVersion.parse(current_version)

    def update(self, request: UpdateRequest) -> UpdateResult:
        """Check for the latest release and optionally install it."""

        latest = self.source.latest(request.repository)
        current = self.current_version
        if latest.version <= current:
            return UpdateResult(
                UpdateStatus.UP_TO_DATE,
                str(current),
                str(latest.version),
                request.repository,
            )
        if request.check_only:
            return UpdateResult(
                UpdateStatus.UPDATE_AVAILABLE,
                str(current),
                str(latest.version),
                request.repository,
            )

        wheel = _find_wheel(latest)
        checksums = _find_asset(latest, "SHA256SUMS")
        wheel_bytes = self.source.download(wheel)
        checksum_bytes = self.source.download(checksums)
        expected = _checksum_for(checksum_bytes, wheel.name)
        actual = sha256(wheel_bytes).hexdigest()
        if actual != expected:
            raise UpdateError(f"Checksum verification failed for release asset {wheel.name}.")

        with tempfile.TemporaryDirectory(prefix="lumon-update-") as directory:
            wheel_path = Path(directory) / wheel.name
            wheel_path.write_bytes(wheel_bytes)
            self.installer.install(wheel_path, request.python_version)
        return UpdateResult(
            UpdateStatus.UPDATED,
            str(current),
            str(latest.version),
            request.repository,
        )


def default_repository() -> str:
    """Resolve the repository without introducing a global config file."""

    return os.environ.get("LUMON_GITHUB_REPOSITORY", DEFAULT_GITHUB_REPOSITORY)


def default_service() -> UpdateService:
    """Build the production update service from process-local settings."""

    return UpdateService(
        source=GitHubReleaseClient(token=os.environ.get("LUMON_GITHUB_TOKEN")),
        installer=default_installer(),
    )


def default_installer() -> ToolInstaller:
    """Select the installer that matches the current Lumon installation."""

    shell_marker = Path(sys.prefix).parent / ".lumon-shell-install"
    if shell_marker.is_file():
        return PythonVenvInstaller(sys.executable)
    return UvToolInstaller()


def _validate_repository(repository: str) -> None:
    if repository.count("/") != 1 or any(part == "" for part in repository.split("/")):
        raise UpdateError("GitHub repository must use the OWNER/REPOSITORY format.")


def _find_wheel(release: ReleaseInfo) -> ReleaseAsset:
    expected = f"lumon-{release.version}-py3-none-any.whl"
    return _find_asset(release, expected)


def _find_asset(release: ReleaseInfo, name: str) -> ReleaseAsset:
    matches = tuple(asset for asset in release.assets if asset.name == name)
    if len(matches) != 1:
        raise UpdateError(f"Release {release.tag_name} is missing required asset {name}.")
    return matches[0]


def _checksum_for(payload: bytes, filename: str) -> str:
    for line in payload.decode("utf-8").splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[1].lstrip("*") == filename:
            digest = fields[0].lower()
            if re.fullmatch(r"[0-9a-f]{64}", digest):
                return digest
    raise UpdateError(f"SHA256SUMS does not contain a valid digest for {filename}.")


def python_version() -> str:
    """Return the minor Python version used by the installed Lumon tool."""

    return f"{sys.version_info.major}.{sys.version_info.minor}"
