"""Delivery history, safe live progress, and interrupted-poll recovery."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import uuid4

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
        workspace, poll.run_id, DeliveryActivity(now, "discover", "Checking Stories.")
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
