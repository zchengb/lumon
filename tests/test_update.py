"""Contract tests for GitHub Release based CLI updates."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from lumon.errors import UpdateError
from lumon.update import (
    PythonVenvInstaller,
    ReleaseAsset,
    ReleaseInfo,
    ReleaseVersion,
    UpdateRequest,
    UpdateService,
    UpdateStatus,
)


class FakeReleaseSource:
    """In-memory release source for update service tests."""

    def __init__(self, release: ReleaseInfo, payloads: dict[str, bytes]) -> None:
        self.release = release
        self.payloads = payloads
        self.downloaded: list[str] = []

    def latest(self, repository: str) -> ReleaseInfo:
        assert repository == "zchengb/lumon"
        return self.release

    def download(self, asset: ReleaseAsset) -> bytes:
        self.downloaded.append(asset.name)
        return self.payloads[asset.name]


class FakeToolInstaller:
    """Capture the verified wheel passed to the installation seam."""

    def __init__(self) -> None:
        self.installed_bytes: bytes | None = None
        self.python_version: str | None = None

    def install(self, wheel: Path, python_version: str) -> None:
        self.installed_bytes = wheel.read_bytes()
        self.python_version = python_version


def _release(
    wheel_bytes: bytes, checksum: str | None = None
) -> tuple[ReleaseInfo, dict[str, bytes]]:
    version = ReleaseVersion(1, 0, 1)
    wheel_name = f"lumon-{version}-py3-none-any.whl"
    digest = checksum or sha256(wheel_bytes).hexdigest()
    assets = (
        ReleaseAsset(wheel_name, f"api://{wheel_name}", f"download://{wheel_name}"),
        ReleaseAsset("SHA256SUMS", "api://SHA256SUMS", "download://SHA256SUMS"),
    )
    payloads = {
        wheel_name: wheel_bytes,
        "SHA256SUMS": f"{digest}  {wheel_name}\n".encode(),
    }
    return ReleaseInfo("v1.0.1", version, assets), payloads


def test_update_installs_verified_wheel() -> None:
    wheel_bytes = b"verified wheel"
    release, payloads = _release(wheel_bytes)
    source = FakeReleaseSource(release, payloads)
    installer = FakeToolInstaller()

    result = UpdateService(source, installer).update(
        UpdateRequest("zchengb/lumon", python_version="3.12")
    )

    assert result.status is UpdateStatus.UPDATED
    assert result.current_version == "1.0.0"
    assert result.latest_version == "1.0.1"
    assert source.downloaded == ["lumon-1.0.1-py3-none-any.whl", "SHA256SUMS"]
    assert installer.installed_bytes == wheel_bytes
    assert installer.python_version == "3.12"


def test_check_only_reports_available_without_downloading() -> None:
    release, payloads = _release(b"verified wheel")
    source = FakeReleaseSource(release, payloads)
    installer = FakeToolInstaller()

    result = UpdateService(source, installer).update(
        UpdateRequest("zchengb/lumon", check_only=True)
    )

    assert result.status is UpdateStatus.UPDATE_AVAILABLE
    assert source.downloaded == []
    assert installer.installed_bytes is None


def test_update_is_noop_when_current_version_is_latest() -> None:
    version = ReleaseVersion(1, 0, 0)
    release = ReleaseInfo("v1.0.0", version, ())
    source = FakeReleaseSource(release, {})
    installer = FakeToolInstaller()

    result = UpdateService(source, installer).update(UpdateRequest("zchengb/lumon"))

    assert result.status is UpdateStatus.UP_TO_DATE
    assert result.current_version == "1.0.0"
    assert result.latest_version == "1.0.0"
    assert installer.installed_bytes is None


def test_update_rejects_a_checksum_mismatch() -> None:
    release, payloads = _release(b"actual wheel", checksum="0" * 64)
    source = FakeReleaseSource(release, payloads)
    installer = FakeToolInstaller()

    with pytest.raises(UpdateError, match="Checksum verification failed"):
        UpdateService(source, installer).update(UpdateRequest("zchengb/lumon"))

    assert installer.installed_bytes is None


def test_python_venv_installer_uses_pip_without_uv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(command: list[str], **kwargs: object) -> None:
        calls.append((command, kwargs))

    monkeypatch.setattr("lumon.update.subprocess.run", fake_run)
    wheel = tmp_path / "lumon-1.0.1-py3-none-any.whl"
    wheel.write_bytes(b"wheel")

    PythonVenvInstaller("/private/venv/bin/python").install(wheel, "3.12")

    assert calls == [
        (
            [
                "/private/venv/bin/python",
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-cache-dir",
                "--force-reinstall",
                str(wheel),
            ],
            {"check": True, "capture_output": True, "text": True},
        )
    ]
