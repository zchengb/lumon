"""Behavior checks for per-Flow macOS scheduling."""

from __future__ import annotations

import plistlib
import stat
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

import lumon.flows.scheduler as scheduler_module
from lumon.errors import PreflightError
from lumon.flows.catalog import FlowCatalog
from lumon.flows.scheduler import LaunchdFlowScheduler
from lumon.workspace.settings import FlowScheduleSettings


def _flow(enabled: bool = True) -> str:
    return (
        "---\n"
        'id = "auto-guard"\n'
        'name = "Auto Guard"\n'
        f"enabled = {'true' if enabled else 'false'}\n"
        'brief = "Inspect production health."\n'
        "---\n\n"
        "# Auto Guard\n"
    )


def test_scheduler_installs_private_plist_for_the_exact_flow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    FlowCatalog(workspace).create(_flow())
    launch_agents = tmp_path / "LaunchAgents"
    state_root = tmp_path / "state"
    workspace_id = uuid4()
    calls: list[list[str]] = []

    def run(arguments: list[str], **_: object) -> SimpleNamespace:
        calls.append(arguments)
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(
        scheduler_module,
        "sys",
        SimpleNamespace(platform="darwin", executable="/usr/bin/python3"),
    )
    monkeypatch.setattr(scheduler_module.subprocess, "run", run)
    scheduler = LaunchdFlowScheduler(state_root, launch_agents)

    scheduler.apply(
        workspace,
        workspace_id,
        FlowScheduleSettings("auto-guard", enabled=True, schedule_expression="0 8 * * 1-5"),
    )

    plist_path = scheduler.plist_path(workspace_id, "auto-guard")
    payload = plistlib.loads(plist_path.read_bytes())
    assert payload["ProgramArguments"][-3:] == [
        "--flow-id",
        "auto-guard",
        "--json",
    ]
    assert payload["StartCalendarInterval"] == [
        {"Hour": 8, "Minute": 0, "Weekday": day} for day in range(1, 6)
    ]
    assert stat.S_IMODE(plist_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(launch_agents.stat().st_mode) == 0o700
    assert [call[0] for call in calls] == ["launchctl", "launchctl"]


def test_disabled_or_flow_disabled_schedule_removes_the_launch_agent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    catalog = FlowCatalog(workspace)
    catalog.create(_flow(enabled=False))
    workspace_id = uuid4()
    launch_agents = tmp_path / "LaunchAgents"
    launch_agents.mkdir()
    state_root = tmp_path / "state"
    scheduler = LaunchdFlowScheduler(state_root, launch_agents)
    plist_path = scheduler.plist_path(workspace_id, "auto-guard")
    plist_path.write_text("stale", encoding="utf-8")
    monkeypatch.setattr(scheduler_module, "sys", SimpleNamespace(platform="linux"))

    scheduler.apply(
        workspace,
        workspace_id,
        FlowScheduleSettings("auto-guard", enabled=True),
    )

    assert not plist_path.exists()

    scheduler.apply(
        workspace,
        workspace_id,
        FlowScheduleSettings("auto-guard", enabled=False),
    )
    assert not plist_path.exists()


def test_enabled_schedule_refuses_non_macos_and_unsupported_cron(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    FlowCatalog(workspace).create(_flow())
    scheduler = LaunchdFlowScheduler(tmp_path / "state", tmp_path / "LaunchAgents")
    workspace_id = uuid4()
    monkeypatch.setattr(scheduler_module, "sys", SimpleNamespace(platform="linux"))

    with pytest.raises(PreflightError, match="requires macOS"):
        scheduler.apply(workspace, workspace_id, FlowScheduleSettings("auto-guard", True))

    monkeypatch.setattr(
        scheduler_module,
        "sys",
        SimpleNamespace(platform="darwin", executable="/usr/bin/python3"),
    )
    with pytest.raises(PreflightError, match="minute/hour"):
        scheduler.apply(
            workspace,
            workspace_id,
            FlowScheduleSettings(
                "auto-guard",
                enabled=True,
                schedule_expression="0 8 1 * *",
            ),
        )
    with pytest.raises(PreflightError, match="invalid weekday"):
        scheduler.apply(
            workspace,
            workspace_id,
            FlowScheduleSettings(
                "auto-guard",
                enabled=True,
                schedule_expression="0 8 * * */5",
            ),
        )
