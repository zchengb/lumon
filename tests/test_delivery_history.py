"""Delivery history, safe live progress, and interrupted-poll recovery."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from lumon.dashboard.routes import create_app
from lumon.dashboard.service import DashboardService
from lumon.delivery.model import (
    DeliveryActivity,
    DeliveryPoll,
    DeliveryPollState,
    DeliveryRun,
    DeliveryState,
)
from lumon.delivery.scheduler import delivery_lock
from lumon.delivery.service import DeliveryService
from lumon.delivery.store import DeliveryRunStore
from lumon.errors import PreflightError
from lumon.skills.installer import SkillInstaller
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.model import InitRequest
from lumon.workspace.registry import WorkspaceRegistry
from lumon.workspace.settings import AutoDeliverySettings, WorkspaceSettings, WorkspaceSettingsStore


def test_story_progress_is_durable_and_duplicate_start_preserves_history(tmp_path: Path) -> None:
    workspace_id = uuid4()
    store = WorkspaceSettingsStore(tmp_path / "state")
    store.save(WorkspaceSettings(workspace_id, auto_delivery=AutoDeliverySettings(enabled=True)))
    now = datetime(2026, 10, 7, 10, 0, tzinfo=UTC)
    service = DeliveryService(settings_store=store, now=lambda: now)
    run = DeliveryRun.claim(
        "story-1", "MBPAS-1", "Version bump", now=now, workspace_id=workspace_id
    )
    service.start(tmp_path, workspace_id, run)
    updated = service.progress(
        tmp_path, run, phase="verification", detail="Checking version strings."
    )
    completed, _ = service.complete(
        tmp_path, workspace_id, updated, "Local verification passed.", phase="handoff"
    )
    assert service.run_store.load(tmp_path, run.run_id) == completed
    assert [event.phase for event in service.run_store.activity(tmp_path, run.run_id)] == [
        "claim",
        "verification",
        "handoff",
    ]
    with pytest.raises(PreflightError, match="already exists"):
        service.start(tmp_path, workspace_id, run)
    with pytest.raises(PreflightError, match="finished"):
        service.progress(tmp_path, completed, phase="implementation", detail="Must not restart.")
    with pytest.raises(PreflightError, match="finished"):
        service.fail(tmp_path, workspace_id, completed, "Must not overwrite.", phase="handoff")
    assert service.run_store.load(tmp_path, run.run_id).state == DeliveryState.COMPLETED


def test_history_skips_unrelated_invalid_and_symlink_receipts(tmp_path: Path) -> None:
    store = DeliveryRunStore()
    run = DeliveryRun.claim("story-1", "MBPAS-1", "Safe")
    store.save(tmp_path, run)
    directory = store.path_for(tmp_path, run.run_id)
    assert (directory.stat().st_mode & 0o777) == 0o700
    assert ((directory / "run.json").stat().st_mode & 0o777) == 0o600
    invalid = tmp_path / "lumon/runs/auto-guard"
    invalid.mkdir()
    (invalid / "run.json").write_text('{"state":"running"}', encoding="utf-8")
    (tmp_path / "lumon/runs/linked").symlink_to(directory, target_is_directory=True)
    assert store.list(tmp_path) == (run,)
    assert store.list_polls(tmp_path) == ()
    with pytest.raises(PreflightError, match="outside"):
        store.load(tmp_path, "linked")
    with pytest.raises(PreflightError, match="unsafe"):
        store.path_for(tmp_path, "../other")
    (directory / "activity.json").symlink_to(directory / "run.json")
    with pytest.raises(PreflightError, match="symbolic link"):
        store.activity(tmp_path, run.run_id)


def test_activity_keeps_recent_summaries_and_redacts_tokens(tmp_path: Path) -> None:
    store = DeliveryRunStore()
    now = datetime(2026, 10, 7, tzinfo=UTC)
    for index in range(202):
        store.record_activity(
            tmp_path, "poll-1", DeliveryActivity(now, "discover", f"Check {index}; password=hidden")
        )
    activity = store.activity(tmp_path, "poll-1")
    assert len(activity) == 200
    assert activity[0].detail == "Check 2; password=[REDACTED]"
    assert "hidden" not in (store.path_for(tmp_path, "poll-1") / "activity.json").read_text()


def test_bounded_activity_accepts_unicode_summaries(tmp_path: Path) -> None:
    store = DeliveryRunStore()
    now = datetime(2026, 10, 7, tzinfo=UTC)
    for _ in range(200):
        store.record_activity(tmp_path, "poll-1", DeliveryActivity(now, "discover", "確認" * 250))
    assert len(store.activity(tmp_path, "poll-1")) == 200


def test_command_details_round_trip_and_legacy_receipts(tmp_path: Path) -> None:
    store = DeliveryRunStore()
    now = datetime(2026, 10, 7, tzinfo=UTC)
    store.record_activity(
        tmp_path,
        "poll-1",
        DeliveryActivity(
            now,
            "verification",
            "command execution: completed (exit 2)",
            command="npm test --token 'private credential'",
            operation_id="cmd-1",
            exit_code=2,
        ),
    )
    command = store.activity(tmp_path, "poll-1")[0]
    assert command.command == "npm test --token [REDACTED]"
    assert command.operation_id == "cmd-1"
    assert command.exit_code == 2
    receipt = store.path_for(tmp_path, "poll-1") / "activity.json"
    receipt.write_text(json.dumps([{"at": now.isoformat(), "phase": "discover", "detail": "old"}]))
    assert store.activity(tmp_path, "poll-1")[0].command is None
    receipt.write_text(
        json.dumps(
            [
                {
                    "at": now.isoformat(),
                    "phase": "discover",
                    "detail": "bad",
                    "exit_code": True,
                }
            ]
        )
    )
    with pytest.raises(PreflightError):
        store.activity(tmp_path, "poll-1")


def test_command_history_stays_within_receipt_byte_limit(tmp_path: Path) -> None:
    store = DeliveryRunStore()
    now = datetime(2026, 10, 7, tzinfo=UTC)
    for _ in range(200):
        store.record_activity(
            tmp_path,
            "poll-1",
            DeliveryActivity(
                now,
                "驗" * 80,
                "驗" * 500,
                command="\x01" * 2000,
                operation_id="驗" * 128,
            ),
        )
    assert 0 < len(store.activity(tmp_path, "poll-1")) < 200
    assert (store.path_for(tmp_path, "poll-1") / "activity.json").stat().st_size <= 1024 * 1024


def test_dashboard_live_history_then_recovery_is_workspace_scoped(tmp_path: Path) -> None:
    state = tmp_path / "state"
    workspace = tmp_path / "workspace"
    registry = WorkspaceRegistry(state)
    settings = WorkspaceSettingsStore(state)
    initializer = WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"),
        registry=registry,
        settings_store=settings,
    )
    initializer.initialize(InitRequest(workspace, name="Delivery test"))
    workspace_id = registry.list()[0].workspace_id
    dashboard = DashboardService(state_root=state, registry=registry, settings_store=settings)
    client = cast(httpx.Client, TestClient(create_app(dashboard)))
    store = dashboard.delivery_service.run_store
    now = datetime(2026, 10, 7, tzinfo=UTC)
    poll = DeliveryPoll("poll-1", workspace_id, DeliveryPollState.RUNNING, now)
    run = DeliveryRun.claim(
        "story-1",
        "MBPAS-1",
        "Version bump",
        now=now,
        workspace_id=workspace_id,
        poll_id=poll.run_id,
    )
    store.save_poll(workspace, poll)
    store.save(workspace, run)
    store.record_activity(
        workspace,
        poll.run_id,
        DeliveryActivity(
            now,
            "discover",
            "Checking Stories.",
            command="git status",
            operation_id="cmd-1",
            exit_code=0,
        ),
    )
    foreign = replace(run, run_id="foreign", workspace_id=uuid4())
    store.save(workspace, foreign)
    with delivery_lock(state, workspace_id):
        response = client.get(f"/api/workspaces/{workspace_id}/deliveries")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert [item["run_id"] for item in response.json()["runs"]] == [run.run_id]
        assert response.json()["polls"][0]["state"] == "running"
        events = client.get(f"/api/workspaces/{workspace_id}/deliveries/poll-1/activity")
        assert events.json()[0]["detail"] == "Checking Stories."
        assert events.json()[0]["command"] == "git status"
        assert events.json()[0]["operation_id"] == "cmd-1"
        assert events.json()[0]["exit_code"] == 0
    recovered = client.get(f"/api/workspaces/{workspace_id}/deliveries").json()
    assert recovered["polls"][0]["state"] == "failed"
    assert recovered["runs"][0]["state"] == "failed"
    assert recovered["runs"][0]["duration_seconds"] is None
    assert recovered["polls"][0]["finished_at"] is None
    assert not (store.path_for(workspace, run.run_id) / "notifications.json").exists()
    assert store.load(workspace, foreign.run_id) == foreign
    assert client.get(f"/api/workspaces/{uuid4()}/deliveries").status_code == 404
    assert (
        client.get(f"/api/workspaces/{workspace_id}/deliveries/foreign/activity").status_code == 409
    )
    assert (
        client.get(f"/api/workspaces/{workspace_id}/deliveries/not-found/activity").status_code
        == 409
    )


def test_legacy_delivery_receipts_remain_readable(tmp_path: Path) -> None:
    store = DeliveryRunStore()
    run = DeliveryRun.claim("legacy", "MBPAS-1", "Legacy")
    store.save(tmp_path, run)
    path = store.path_for(tmp_path, run.run_id) / "run.json"
    payload = json.loads(path.read_text())
    del payload["poll_id"], payload["detail"]
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert store.load(tmp_path, run.run_id) == run


@pytest.fixture
def history_context(tmp_path: Path) -> tuple[httpx.Client, DashboardService, Path, UUID]:
    state = tmp_path / "state"
    workspace = tmp_path / "workspace"
    registry = WorkspaceRegistry(state)
    settings = WorkspaceSettingsStore(state)
    initializer = WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"),
        registry=registry,
        settings_store=settings,
    )
    initializer.initialize(InitRequest(workspace, name="History test"))
    workspace_id = registry.list()[0].workspace_id
    dashboard = DashboardService(state_root=state, registry=registry, settings_store=settings)
    return cast(httpx.Client, TestClient(create_app(dashboard))), dashboard, workspace, workspace_id


@pytest.mark.parametrize(
    "state", [DeliveryState.COMPLETED, DeliveryState.BLOCKED, DeliveryState.FAILED]
)
def test_delete_history_is_durable_and_keeps_all_operational_receipts(
    history_context: tuple[httpx.Client, DashboardService, Path, UUID], state: DeliveryState
) -> None:
    client, dashboard, workspace, workspace_id = history_context
    store = dashboard.delivery_service.run_store
    run = replace(
        DeliveryRun.claim("recorded", "MBPAS-1", "Saved", workspace_id=workspace_id), state=state
    )
    store.save(workspace, run)
    store.record_activity(
        workspace, run.run_id, DeliveryActivity(run.started_at, "handoff", "Done")
    )
    directory = store.path_for(workspace, run.run_id)
    before = {path.name: path.read_bytes() for path in directory.iterdir()}
    endpoint = f"/api/workspaces/{workspace_id}/deliveries/{run.run_id}"
    for _ in range(2):
        assert client.delete(endpoint).status_code == 204
    assert client.get(f"/api/workspaces/{workspace_id}/deliveries").json()["runs"] == []
    assert DeliveryRunStore().history_deleted(workspace, run.run_id)
    assert store.list(workspace) == (run,)
    assert store.load(workspace, run.run_id) == run
    assert all((directory / name).read_bytes() == content for name, content in before.items())
    assert (directory / "history-deleted.json").stat().st_mode & 0o777 == 0o600
    assert client.get(f"{endpoint}/activity").json()[0]["detail"] == "Done"


def test_delete_history_rejects_active_work_foreign_ownership_and_invalid_targets(
    history_context: tuple[httpx.Client, DashboardService, Path, UUID],
) -> None:
    client, dashboard, workspace, workspace_id = history_context
    store = dashboard.delivery_service.run_store
    run = DeliveryRun.claim("recorded", "MBPAS-1", "Saved", workspace_id=workspace_id)
    store.save(workspace, run)
    endpoint = f"/api/workspaces/{workspace_id}/deliveries/{run.run_id}"
    assert client.delete(endpoint).status_code == 409
    assert not store.history_deleted(workspace, run.run_id)
    finished = replace(run, state=DeliveryState.COMPLETED)
    store.save(workspace, finished)
    with delivery_lock(dashboard.registry.layout.root, workspace_id):
        assert client.delete(endpoint).status_code == 409
    poll = DeliveryPoll("parent", workspace_id, DeliveryPollState.RUNNING, run.started_at)
    store.save_poll(workspace, poll)
    store.save(workspace, replace(finished, poll_id=poll.run_id))
    assert client.delete(endpoint).status_code == 409
    store.save(workspace, replace(finished, workspace_id=uuid4()))
    assert client.delete(endpoint).status_code == 409
    assert client.delete(endpoint.replace(str(workspace_id), str(uuid4()))).status_code == 404
    assert client.delete(endpoint.replace("recorded", "missing")).status_code == 409
    with pytest.raises(PreflightError):
        store.delete_history(workspace, "../outside")
    assert not store.history_deleted(workspace, run.run_id)


def test_delete_history_rejects_symlinks_and_preserves_row_on_write_failure(
    history_context: tuple[httpx.Client, DashboardService, Path, UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, dashboard, workspace, workspace_id = history_context
    store = dashboard.delivery_service.run_store
    run = replace(
        DeliveryRun.claim("recorded", "MBPAS-1", "Saved", workspace_id=workspace_id),
        state=DeliveryState.COMPLETED,
    )
    store.save(workspace, run)
    directory = store.path_for(workspace, run.run_id)
    marker = directory / "history-deleted.json"
    marker.symlink_to(directory / "run.json")
    with pytest.raises(PreflightError, match="symbolic"):
        store.delete_history(workspace, run.run_id)
    marker.unlink()

    def fail_replace(source: object, destination: object) -> None:
        del source, destination
        raise OSError("test disk failure")

    monkeypatch.setattr("lumon.delivery.store.os.replace", fail_replace)
    endpoint = f"/api/workspaces/{workspace_id}/deliveries/{run.run_id}"
    assert client.delete(endpoint).status_code == 409
    assert not store.history_deleted(workspace, run.run_id)
    assert (
        client.get(f"/api/workspaces/{workspace_id}/deliveries").json()["runs"][0]["run_id"]
        == run.run_id
    )
    assert store.load(workspace, run.run_id) == run
