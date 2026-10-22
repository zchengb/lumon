"""Environment prerequisites are observable without starting or installing anything."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from lumon.agents.agent.config import AgentConfig
from lumon.agents.agent.workspace_context import WorkspaceContextBuilder
from lumon.cli.app import app
from lumon.dashboard.routes import create_app
from lumon.dashboard.service import DashboardService
from lumon.visual import environment
from lumon.visual.environment import CommandResult, EnvironmentInspector
from lumon.visual.environment import get_environment as inspect_environment
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.model import InitRequest


def _client(service: DashboardService) -> httpx.Client:
    return TestClient(create_app(service))


def _inspector(
    tmp_path: Path,
    outputs: dict[str, CommandResult],
    calls: list[tuple[str, ...]],
    *,
    system: str = "Darwin",
    machine: str = "arm64",
) -> EnvironmentInspector:
    def run(command: tuple[str, ...]) -> CommandResult:
        calls.append(command)
        return outputs[command[0]]

    return EnvironmentInspector(
        system=system,
        machine=machine,
        home=tmp_path,
        environment={},
        which=lambda name: name if name in outputs else None,
        run=run,
    )


def _simulators(*, available: bool = True, state: str = "Shutdown") -> CommandResult:
    return CommandResult(
        True,
        json.dumps(
            {
                "runtimes": [
                    {
                        "identifier": "com.apple.CoreSimulator.SimRuntime.iOS-27-0",
                        "isAvailable": available,
                    }
                ],
                "devices": {
                    "com.apple.CoreSimulator.SimRuntime.iOS-27-0": [
                        {"isAvailable": True, "state": state}
                    ]
                },
            }
        ),
    )


def _avd(tmp_path: Path, abi: str = "arm64-v8a", *, with_image: bool = True) -> None:
    avds = tmp_path / ".android/avd"
    device = avds / "test.avd"
    device.mkdir(parents=True)
    (avds / "test.ini").write_text(f"path={device}\n")
    (device / "config.ini").write_text(f"abi.type={abi}\nimage.sysdir.1=system-images/test/{abi}\n")
    image = tmp_path / "Library/Android/sdk/system-images/test" / abi
    image.mkdir(parents=True)
    (image / "source.properties").write_text(f"SystemImage.Abi={abi}\n")
    if with_image:
        (image / "system.img").touch()


def test_ready_tools_do_not_claim_application_success_or_start_devices(tmp_path: Path) -> None:
    _avd(tmp_path)
    calls: list[tuple[str, ...]] = []
    outputs = {
        "xcrun": _simulators(),
        "adb": CommandResult(True),
        "emulator": CommandResult(True),
        "chromium": CommandResult(True),
        "docker": CommandResult(True, "linux"),
    }
    snapshot = _inspector(tmp_path, outputs, calls).inspect()
    assert [item.status for item in snapshot.environments] == ["ready"] * 4
    assert snapshot.environments[0].running is False
    assert snapshot.environments[1].running is None
    assert snapshot.application_status == "unverified"
    assert set(calls) == {
        ("xcrun", "simctl", "list", "--json"),
        ("emulator", "-accel-check"),
        ("docker", "info", "--format", "{{.OSType}}"),
    }


@pytest.mark.parametrize(
    "available,state,expected",
    [
        (True, "Booted", "ready"),
        (False, "Booted", "missing"),
    ],
)
def test_unavailable_ios_runtime_cannot_be_ready(
    tmp_path: Path,
    available: bool,
    state: str,
    expected: str,
) -> None:
    report = _inspector(
        tmp_path, {"xcrun": _simulators(available=available, state=state)}, []
    ).inspect()
    ios = report.environments[0]
    assert ios.status == expected
    assert ios.running is available


@pytest.mark.parametrize("abi,with_image", [("x86_64", True), ("arm64-v8a", False)])
def test_android_rejects_wrong_architecture_and_missing_image(
    tmp_path: Path,
    abi: str,
    with_image: bool,
) -> None:
    _avd(tmp_path, abi, with_image=with_image)
    report = _inspector(
        tmp_path, {"emulator": CommandResult(True), "adb": CommandResult(True)}, []
    ).inspect()
    assert report.environments[1].status == "missing"


def test_failures_stay_distinct_and_do_not_expose_raw_output(tmp_path: Path) -> None:
    report = _inspector(
        tmp_path,
        {
            "xcrun": CommandResult(True, '{"password":"secret"}'),
            "docker": CommandResult(False, "credential-secret"),
        },
        [],
    ).inspect()
    assert report.environments[0].status == "error"
    assert report.environments[1].status == "missing"
    assert report.environments[3].status == "error"
    assert "secret" not in report.prompt_text()


def test_linux_does_not_attempt_ios_commands(tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []
    report = _inspector(tmp_path, {}, calls, system="Linux").inspect()
    assert report.environments[0].status == "unsupported"
    assert calls == []


def test_cached_checks_expire_and_explicit_refresh_rechecks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ticks = [0.0]
    observations: list[environment.EnvironmentSnapshot] = []

    def inspect(self: EnvironmentInspector) -> environment.EnvironmentSnapshot:
        del self
        snapshot = environment.EnvironmentSnapshot(str(ticks[0]), ())
        observations.append(snapshot)
        return snapshot

    monkeypatch.setattr(environment, "_snapshot", None)
    monkeypatch.setattr(environment, "_expires_at", 0.0)
    monkeypatch.setattr(environment.time, "monotonic", lambda: ticks[0])
    monkeypatch.setattr(EnvironmentInspector, "inspect", inspect)
    first = inspect_environment()
    ticks[0] = 20
    assert inspect_environment() is first
    refreshed = inspect_environment(refresh=True)
    assert refreshed is not first
    ticks[0] = 51
    assert inspect_environment() is not refreshed
    assert len(observations) == 3


def test_timed_out_command_reports_error_without_raw_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def timeout(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs["timeout"] == 4
        assert args
        raise subprocess.TimeoutExpired("docker", 4, stderr="secret")

    monkeypatch.setattr(environment.subprocess, "run", timeout)
    inspector = EnvironmentInspector(
        system="Linux",
        machine="arm64",
        home=tmp_path,
        environment={},
        which=lambda name: "docker" if name == "docker" else None,
    )
    report = inspector.inspect()
    assert report.environments[3].status == "error"
    assert "secret" not in report.prompt_text()


def test_snapshot_shared_by_http_cli_and_new_and_resumed_agent_prompts(
    tmp_path: Path,
    initializer: WorkspaceInitializer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    initializer.initialize(InitRequest(workspace, name="test"))
    registration = initializer.registry.list()[0]
    snapshot = environment.EnvironmentSnapshot(
        "2026-10-22T01:23:45+00:00",
        (
            environment.VisualEnvironment(
                "android", "missing", (environment.EnvironmentCheck("android_avd", "missing"),)
            ),
        ),
    )
    refresh_calls: list[bool] = []

    def inspect(*, refresh: bool = False) -> environment.EnvironmentSnapshot:
        refresh_calls.append(refresh)
        return snapshot

    monkeypatch.setattr(environment, "get_environment", inspect)
    service = DashboardService(state_root=tmp_path / "lumon-home", registry=initializer.registry)
    with _client(service) as client:
        response = client.get(
            f"/api/workspaces/{registration.workspace_id}/environment?refresh=true"
        )
    assert response.status_code == 200
    assert response.json() == json.loads(snapshot.prompt_text())
    assert response.headers["Cache-Control"] == "no-store"
    result = CliRunner().invoke(app, ["doctor", "--visual", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == response.json()
    builder = WorkspaceContextBuilder(AgentConfig(), registry=initializer.registry)
    assert snapshot.prompt_text() in builder.build_prompt(
        builder.resolve_workspace(), (), "check UI"
    )
    assert snapshot.prompt_text() in builder.build_resume_prompt("check again")
    assert refresh_calls == [True, True, False, False]


def test_steering_prompt_does_not_wait_for_environment_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_probe(*, refresh: bool = False) -> environment.EnvironmentSnapshot:
        del refresh
        raise AssertionError("Steering must not wait on a tool probe")

    monkeypatch.setattr(environment, "get_environment", unexpected_probe)
    monkeypatch.setattr(environment, "_snapshot", None)
    prompt = WorkspaceContextBuilder(AgentConfig()).build_resume_prompt(
        "先不要 commit / push",
        inspect_environment=False,
    )
    assert "先不要 commit / push" in prompt
    assert "(not checked)" in prompt
