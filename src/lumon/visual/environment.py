"""Bounded local environment probes shared by Dashboard, CLI and Agent prompts.

These checks never boot devices, install dependencies, or run project scripts.
Readiness describes host prerequisites, not successful application verification.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import time
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Literal

from pydantic import BaseModel, ValidationError

Status = Literal["ready", "missing", "error", "unsupported"]
Platform = Literal["ios", "android", "web", "docker"]


@dataclass(frozen=True, slots=True)
class EnvironmentCheck:
    name: str
    status: Status


@dataclass(frozen=True, slots=True)
class VisualEnvironment:
    platform: Platform
    status: Status
    checks: tuple[EnvironmentCheck, ...]
    running: bool | None = None


@dataclass(frozen=True, slots=True)
class EnvironmentSnapshot:
    checked_at: str
    environments: tuple[VisualEnvironment, ...]
    application_status: Literal["unverified"] = "unverified"

    def prompt_text(self) -> str:
        """Return a compact snapshot without paths, credentials or command output."""
        return json.dumps(asdict(self), separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class CommandResult:
    ok: bool
    output: str = ""


class _SimulatorRuntime(BaseModel):
    identifier: str
    isAvailable: bool


class _SimulatorDevice(BaseModel):
    isAvailable: bool
    state: str


class _SimulatorList(BaseModel):
    runtimes: list[_SimulatorRuntime]
    devices: dict[str, list[_SimulatorDevice]]


def _run(arguments: tuple[str, ...]) -> CommandResult:
    try:
        completed = subprocess.run(
            arguments,
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired, UnicodeError):
        return CommandResult(False)
    # Raw stderr can contain account information; it never enters a snapshot.
    return CommandResult(completed.returncode == 0, completed.stdout)


class EnvironmentInspector:
    """Inspect installed host tools through an injectable command runner."""

    def __init__(
        self,
        *,
        system: str,
        machine: str,
        home: Path,
        environment: Mapping[str, str],
        which: Callable[[str], str | None],
        run: Callable[[tuple[str, ...]], CommandResult] = _run,
    ) -> None:
        self.system = system
        self.machine = machine
        self.home = home
        self.environment = environment
        self.which = which
        self.run = run

    def inspect(self) -> EnvironmentSnapshot:
        probes = (self._ios, self._android, self._web, self._docker)
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(probe) for probe in probes]
            environments = tuple(future.result() for future in futures)
        return EnvironmentSnapshot(datetime.now(UTC).isoformat(), environments)

    def _ios(self) -> VisualEnvironment:
        if self.system != "Darwin":
            return _report("ios", (EnvironmentCheck("xcode", "unsupported"),))
        xcrun = self.which("xcrun")
        if not xcrun:
            return _report("ios", (EnvironmentCheck("xcode", "missing"),))
        result = self.run((xcrun, "simctl", "list", "--json"))
        if not result.ok:
            return _report("ios", (EnvironmentCheck("xcode", "error"),))
        try:
            payload = _SimulatorList.model_validate_json(result.output)
            ios_ids = {
                runtime.identifier
                for runtime in payload.runtimes
                if runtime.isAvailable and ".iOS-" in runtime.identifier
            }
            available = [
                device
                for runtime_id in ios_ids
                for device in payload.devices.get(runtime_id, [])
                if device.isAvailable
            ]
        except ValidationError:
            return _report("ios", (EnvironmentCheck("ios_runtime", "error"),))
        return _report(
            "ios",
            (
                _check("xcode", True),
                _check("ios_runtime", bool(ios_ids)),
                _check("ios_device", bool(available)),
            ),
            running=any(device.state == "Booted" for device in available),
        )

    def _android(self) -> VisualEnvironment:
        sdk = self._sdk()
        emulator = self._executable(sdk / "emulator" / "emulator") or self.which("emulator")
        adb = self._executable(sdk / "platform-tools" / "adb") or self.which("adb")
        checks = [
            _check("android_sdk", sdk.is_dir()),
            _check("adb", bool(adb)),
            _check("emulator", bool(emulator)),
        ]
        if emulator:
            acceleration = self.run((emulator, "-accel-check"))
            checks.append(EnvironmentCheck("acceleration", "ready" if acceleration.ok else "error"))
            checks.append(_check("android_avd", self._has_compatible_avd(sdk)))
        return _report("android", tuple(checks))

    def _has_compatible_avd(self, sdk: Path) -> bool:
        user_home = Path(self.environment.get("ANDROID_USER_HOME", str(self.home / ".android")))
        avd_home = Path(self.environment.get("ANDROID_AVD_HOME", str(user_home / "avd")))
        abi = {"arm64": "arm64-v8a", "aarch64": "arm64-v8a", "x86_64": "x86_64"}.get(self.machine)
        if abi is None:
            return False
        for registration in avd_home.glob("*.ini"):
            metadata = _properties(registration)
            device_path = Path(metadata.get("path", str(avd_home / f"{registration.stem}.avd")))
            config = _properties(device_path / "config.ini")
            image_path = config.get("image.sysdir.1", "")
            if not image_path:
                continue
            image = sdk / image_path
            image_abi = _properties(image / "source.properties").get("SystemImage.Abi")
            if (
                image_abi == abi
                and config.get("abi.type", abi) == abi
                and (image / "system.img").is_file()
            ):
                return True
        return False

    def _sdk(self) -> Path:
        configured = self.environment.get("ANDROID_HOME") or self.environment.get(
            "ANDROID_SDK_ROOT"
        )
        default = self.home / ("Library/Android/sdk" if self.system == "Darwin" else "Android/Sdk")
        return Path(configured).expanduser() if configured else default

    def _web(self) -> VisualEnvironment:
        browser = (
            self.which("chromium") or self.which("chromium-browser") or self.which("google-chrome")
        )
        # Discovery alone does not prove an automation driver or project server works.
        return _report("web", (_check("browser", bool(browser)),))

    def _docker(self) -> VisualEnvironment:
        docker = self.which("docker")
        if not docker:
            return _report("docker", (EnvironmentCheck("docker_engine", "missing"),))
        # Docker is optional; an available engine does not imply a browser image exists.
        result = self.run((docker, "info", "--format", "{{.OSType}}"))
        return _report(
            "docker",
            (EnvironmentCheck("docker_engine", "ready" if result.ok else "error"),),
            running=result.ok,
        )

    @staticmethod
    def _executable(path: Path) -> str | None:
        return str(path) if path.is_file() and os.access(path, os.X_OK) else None


def _properties(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return {}
    return {
        key.strip(): value.strip()
        for line in lines
        if "=" in line
        for key, value in [line.split("=", 1)]
    }


def _check(name: str, present: bool) -> EnvironmentCheck:
    return EnvironmentCheck(name, "ready" if present else "missing")


def _report(
    name: Platform,
    checks: tuple[EnvironmentCheck, ...],
    *,
    running: bool | None = None,
) -> VisualEnvironment:
    status: Status = "ready"
    for priority in ("unsupported", "error", "missing"):
        if any(check.status == priority for check in checks):
            status = priority
            break
    return VisualEnvironment(name, status, checks, running)


_lock = Lock()
_snapshot: EnvironmentSnapshot | None = None
_expires_at = 0.0


def peek_environment() -> EnvironmentSnapshot | None:
    """Read the last immutable observation without waiting on probes or their lock."""
    return _snapshot


def _which(name: str) -> str | None:
    executable = shutil.which(name)
    if executable is None and name == "google-chrome" and platform.system() == "Darwin":
        chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        return str(chrome) if chrome.is_file() and os.access(chrome, os.X_OK) else None
    return executable


def get_environment(*, refresh: bool = False) -> EnvironmentSnapshot:
    """Cache passive checks for 30 seconds per process; explicit checks refresh them."""
    global _snapshot, _expires_at
    with _lock:
        if not refresh and _snapshot is not None and time.monotonic() < _expires_at:
            return _snapshot
        inspector = EnvironmentInspector(
            system=platform.system(),
            machine=platform.machine(),
            home=Path.home(),
            environment=os.environ,
            which=_which,
        )
        _snapshot = inspector.inspect()
        _expires_at = time.monotonic() + 30
        return _snapshot
