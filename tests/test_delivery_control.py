"""Continuation preserves work and stops the owning execution, not just its badge."""

from __future__ import annotations

import asyncio
import json
import subprocess
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from lumon.agents.agent.config import AgentConfig, AgentConfigStore
from lumon.agents.agent.model import AgentErrorCode, AgentEvent, AgentResult
from lumon.agents.agent.runner import AgentEventCallback, AgentRunner, ProgressCallback
from lumon.dashboard.routes import create_app
from lumon.dashboard.service import DashboardService
from lumon.delivery.control import prepare_resume, request_stop, save_checkpoint, worktree_snapshot
from lumon.delivery.execution import DeliveryTasks, resume_delivery, run_poll
from lumon.delivery.model import (
    DeliveryEvent,
    DeliveryPoll,
    DeliveryPollState,
    DeliveryRun,
    DeliveryState,
)
from lumon.delivery.scheduler import delivery_lock
from lumon.delivery.service import DeliveryNotification, DeliveryService
from lumon.errors import PreflightError
from lumon.skills.installer import SkillInstaller
from lumon.tools.jira_delivery import JiraDeliveryCandidate, JiraDeliveryTrigger
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.model import InitRequest
from lumon.workspace.registry import WorkspaceRegistry
from lumon.workspace.settings import AutoDeliverySettings, WorkspaceSettings, WorkspaceSettingsStore


@pytest.fixture
def lab(tmp_path: Path) -> tuple[Path, Path, UUID, DeliveryService]:
    state, workspace = tmp_path / "state", tmp_path / "workspace"
    registry, settings = WorkspaceRegistry(state), WorkspaceSettingsStore(state)
    WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"),
        registry=registry,
        settings_store=settings,
    ).initialize(InitRequest(workspace, name="Control test"))
    workspace_id = registry.list()[0].workspace_id
    settings.save(
        WorkspaceSettings(
            workspace_id,
            auto_delivery=AutoDeliverySettings(
                enabled=True, jira_site="test.atlassian.net", trigger_jql="project = TEST"
            ),
        )
    )
    AgentConfigStore(state).save(
        AgentConfig(enabled=True, feishu_app_id="fake", feishu_app_secret="fake")
    )
    return state, workspace, workspace_id, DeliveryService(settings_store=settings)


def blocked(workspace: Path, workspace_id: UUID, service: DeliveryService) -> DeliveryRun:
    run = DeliveryRun.claim("delivery-TEST-1", "TEST-1", "Test", workspace_id=workspace_id)
    service.start(workspace, workspace_id, run)
    return service.block(workspace, workspace_id, run, "Need access", phase="verification")[0]


@pytest.fixture
def lifecycle_notifications(monkeypatch: pytest.MonkeyPatch) -> list[tuple[DeliveryEvent, int]]:
    events: list[tuple[DeliveryEvent, int]] = []
    original = DeliveryService.notify

    def observe(
        self: DeliveryService,
        workspace: Path,
        workspace_id: UUID,
        run: DeliveryRun,
        event: DeliveryEvent | str,
    ) -> DeliveryNotification:
        events.append((DeliveryEvent(event), run.attempt))
        return original(self, workspace, workspace_id, run, event)

    monkeypatch.setattr(DeliveryService, "notify", observe)
    return events


def test_resume_preserves_attempt_checkpoint_and_rejects_stale_actions(
    lab: tuple[Path, Path, UUID, DeliveryService],
) -> None:
    _state, workspace, workspace_id, service = lab
    run = blocked(workspace, workspace_id, service)
    run = save_checkpoint(
        service.run_store,
        workspace,
        run.run_id,
        detail="Tests passed; no push.",
        comment_id="50509",
    )
    service.run_store.archive_attempt(workspace, run)
    service.run_store.archive_attempt(workspace, run)
    poll = DeliveryPoll(
        "resume-poll",
        workspace_id,
        DeliveryPollState.RUNNING,
        run.started_at + timedelta(minutes=5),
    )
    service.run_store.save_poll(workspace, poll)
    resumed = prepare_resume(
        service.run_store,
        workspace,
        workspace_id,
        run.run_id,
        attempt=1,
        poll=poll,
        reentry_id="337133",
    )
    assert resumed.attempt == 2 and resumed.run_id == run.run_id
    assert resumed.jira_reentry_id == "337133"
    assert resumed.checkpoint == run.checkpoint and resumed.result_comment_id == "50509"
    assert resumed.started_at == run.started_at and resumed.attempt_started_at == poll.started_at
    newer = replace(run, run_id="newer", started_at=run.started_at + timedelta(seconds=1))
    service.run_store.save(workspace, newer)
    assert service.run_store.list(workspace)[0].run_id == run.run_id
    assert service.run_store.load(workspace, run.run_id) == resumed
    archive = service.run_store.path_for(workspace, run.run_id) / "attempt-1.json"
    assert json.loads(archive.read_text())["state"] == "blocked"
    with pytest.raises(PreflightError, match="attempt changed"):
        request_stop(service.run_store, workspace, workspace_id, run.run_id, attempt=1)
    with pytest.raises(PreflightError, match="different archived"):
        service.run_store.archive_attempt(workspace, run)
    assert not (archive.stat().st_mode & 0o077)


@pytest.mark.parametrize("state", [DeliveryState.COMPLETED, DeliveryState.RUNNING])
def test_cannot_resume_completed_or_active(
    lab: tuple[Path, Path, UUID, DeliveryService], state: DeliveryState
) -> None:
    root, workspace, workspace_id, service = lab
    run = replace(blocked(workspace, workspace_id, service), state=state)
    service.run_store.save(workspace, run)
    with pytest.raises(PreflightError, match="Only a failed"):
        asyncio.run(
            resume_delivery(workspace, workspace_id, run.run_id, attempt=1, state_root=root)
        )
    assert service.run_store.load(workspace, run.run_id) == run


def test_snapshot_detects_tracked_and_untracked_changes_without_storing_contents(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "lumon/worktrees/TEST-1/app"
    repository.mkdir(parents=True)
    for arguments in (
        ("init",),
        ("config", "user.name", "Test"),
        ("config", "user.email", "test@example.invalid"),
    ):
        subprocess.run(["git", "-C", str(repository), *arguments], check=True, capture_output=True)
    (repository / "screen.txt").write_text("baseline")
    subprocess.run(["git", "-C", str(repository), "add", "screen.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "commit", "-m", "baseline"], check=True, capture_output=True
    )
    baseline = worktree_snapshot(tmp_path, "TEST-1")
    (repository / "screen.txt").write_text("private business content")
    changed = worktree_snapshot(tmp_path, "TEST-1")
    assert baseline != changed and "private business content" not in changed
    (repository / "new.txt").write_text("new change")
    assert worktree_snapshot(tmp_path, "TEST-1") != changed


def test_snapshot_does_not_follow_worktrees_outside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "lumon").mkdir(parents=True)
    outside = tmp_path / "outside"
    (outside / "TEST-1/app").mkdir(parents=True)
    (workspace / "lumon/worktrees").symlink_to(outside, target_is_directory=True)
    with pytest.raises(PreflightError, match="outside"):
        worktree_snapshot(workspace, "TEST-1")


def test_result_comment_id_cannot_be_replaced_by_another_comment(
    lab: tuple[Path, Path, UUID, DeliveryService],
) -> None:
    _state, workspace, workspace_id, service = lab
    run = blocked(workspace, workspace_id, service)
    save_checkpoint(service.run_store, workspace, run.run_id, comment_id="50509")
    with pytest.raises(PreflightError, match="existing Delivery result comment"):
        save_checkpoint(service.run_store, workspace, run.run_id, comment_id="50510")
    assert service.run_store.load(workspace, run.run_id).result_comment_id == "50509"


def test_dashboard_task_resumes_session_and_acknowledges_stop_only_after_cancellation(
    lab: tuple[Path, Path, UUID, DeliveryService],
) -> None:
    state, workspace, workspace_id, service = lab
    run = replace(blocked(workspace, workspace_id, service), agent_session_id=str(uuid4()))
    service.run_store.save(workspace, run)
    observed: list[str] = []

    class WaitingRunner:
        async def run(
            self,
            root: Path,
            prompt: str,
            *,
            agent_session_id: str | None = None,
            on_progress: ProgressCallback | None = None,
            on_event: AgentEventCallback | None = None,
        ) -> AgentResult:
            assert agent_session_id == run.agent_session_id
            assert "do NOT call start" in prompt and "ONE final Jira result comment" in prompt
            assert "do NOT blindly create" in prompt or "blindly create" in prompt
            observed.append("started")
            try:
                await asyncio.Event().wait()
            finally:
                observed.append("cancelled")
            return AgentResult(status="succeeded", final_text="unreachable")

    async def exercise() -> None:
        tasks = DeliveryTasks(
            state, runner_factory=lambda _config: cast(AgentRunner, WaitingRunner())
        )
        await tasks.launch(workspace, workspace_id, run.run_id, attempt=1)
        with pytest.raises(
            PreflightError,
            match="already running|already active|busy|another|lock",
        ):
            with delivery_lock(state, workspace_id):
                pass
        for _ in range(100):
            if observed:
                break
            await asyncio.sleep(0.01)
        request_stop(service.run_store, workspace, workspace_id, run.run_id, attempt=2)
        assert service.run_store.load(workspace, run.run_id).state == DeliveryState.RUNNING
        for _ in range(100):
            if service.run_store.load(workspace, run.run_id).state == DeliveryState.STOPPED:
                break
            await asyncio.sleep(0.01)
        assert observed == ["started", "cancelled"]
        stopped = service.run_store.load(workspace, run.run_id)
        assert stopped.state == DeliveryState.STOPPED and stopped.attempt == 2
        assert stopped.poll_id is not None
        assert (
            service.run_store.load_poll(workspace, stopped.poll_id).state
            == DeliveryPollState.STOPPED
        )
        await tasks.close()

    asyncio.run(exercise())


def test_resume_success_and_duplicate_effect_instructions(
    lab: tuple[Path, Path, UUID, DeliveryService],
    lifecycle_notifications: list[tuple[DeliveryEvent, int]],
) -> None:
    state, workspace, workspace_id, service = lab
    run = blocked(workspace, workspace_id, service)
    session = str(uuid4())

    class CompletingRunner:
        async def run(
            self,
            root: Path,
            prompt: str,
            *,
            on_progress: ProgressCallback | None = None,
            on_event: AgentEventCallback | None = None,
        ) -> AgentResult:
            assert "Reconcile remote commits" in prompt
            assert on_event is not None
            await on_event(AgentEvent(kind="session", agent_session_id=session))
            current = service.run_store.load(root, run.run_id)
            service.complete(
                root, workspace_id, current, "Published earlier; handoff complete.", phase="handoff"
            )
            return AgentResult(status="succeeded", final_text="Completed", agent_session_id=session)

    asyncio.run(
        resume_delivery(
            workspace,
            workspace_id,
            run.run_id,
            attempt=1,
            state_root=state,
            runner_factory=lambda _config: cast(AgentRunner, CompletingRunner()),
        )
    )  # type: ignore[arg-type]
    finished = service.run_store.load(workspace, run.run_id)
    assert finished.state == DeliveryState.COMPLETED and finished.agent_session_id == session
    assert finished.poll_id is not None
    assert (
        service.run_store.load_poll(workspace, finished.poll_id).state
        == DeliveryPollState.COMPLETED
    )
    assert lifecycle_notifications == [
        (DeliveryEvent.STARTED, 1),
        (DeliveryEvent.BLOCKED, 1),
        (DeliveryEvent.STARTED, 2),
        (DeliveryEvent.DEV_DONE, 2),
    ]


def test_missing_session_falls_back_to_checkpoint_not_fresh_delivery(
    lab: tuple[Path, Path, UUID, DeliveryService],
    lifecycle_notifications: list[tuple[DeliveryEvent, int]],
) -> None:
    state, workspace, workspace_id, service = lab
    run = replace(
        blocked(workspace, workspace_id, service),
        agent_session_id=str(uuid4()),
        checkpoint="Published already; only Jira result media remain.",
    )
    service.run_store.save(workspace, run)
    sessions: list[str | None] = []

    class SessionRunner:
        async def run(
            self,
            root: Path,
            prompt: str,
            *,
            agent_session_id: str | None = None,
            on_progress: ProgressCallback | None = None,
            on_event: AgentEventCallback | None = None,
        ) -> AgentResult:
            sessions.append(agent_session_id)
            if agent_session_id:
                return AgentResult(status="failed", error_code=AgentErrorCode.SESSION_UNAVAILABLE)
            assert (
                run.checkpoint is not None
                and run.checkpoint in prompt
                and "do NOT call start" in prompt
            )
            current = service.run_store.load(root, run.run_id)
            service.complete(
                root, workspace_id, current, "Missing handoff finished.", phase="handoff"
            )
            return AgentResult(status="succeeded", final_text="Done")

    asyncio.run(
        resume_delivery(
            workspace,
            workspace_id,
            run.run_id,
            attempt=1,
            state_root=state,
            runner_factory=lambda _config: cast(AgentRunner, SessionRunner()),
        )
    )
    assert sessions == [run.agent_session_id, None]
    assert service.run_store.load(workspace, run.run_id).attempt == 2
    assert lifecycle_notifications.count((DeliveryEvent.STARTED, 2)) == 1


def test_session_before_claim_survives_progress_and_stop_blocks_late_completion(
    lab: tuple[Path, Path, UUID, DeliveryService],
) -> None:
    _state, workspace, workspace_id, service = lab
    session = str(uuid4())
    poll = DeliveryPoll("managed", workspace_id, DeliveryPollState.RUNNING, datetime.now(UTC))
    store = service.run_store
    store.save_poll(workspace, poll)
    store.set_control(workspace, poll.run_id, stopping=False)
    store.save_session(workspace, poll.run_id, session)
    run = DeliveryRun.claim(
        "delivery-TEST-2", "TEST-2", "Test", workspace_id=workspace_id, poll_id=poll.run_id
    )
    service.start(workspace, workspace_id, run)
    progressed = service.progress(workspace, run, phase="verification", detail="Checked")
    assert progressed.agent_session_id == session
    request_stop(store, workspace, workspace_id, run.run_id, attempt=1)
    with pytest.raises(PreflightError, match="stop was requested"):
        service.complete(workspace, workspace_id, progressed, "Too late", phase="handoff")
    assert store.load(workspace, run.run_id).state == DeliveryState.RUNNING


def test_poll_does_not_resume_without_post_terminal_jira_reentry(
    lab: tuple[Path, Path, UUID, DeliveryService], monkeypatch: pytest.MonkeyPatch
) -> None:
    state, workspace, workspace_id, service = lab
    run = blocked(workspace, workspace_id, service)

    async def no_candidate(
        self: JiraDeliveryTrigger,
        jira_site: str,
        trigger_jql: str,
        *,
        excluded_keys: frozenset[str],
    ) -> None:
        assert run.story_key in excluded_keys
        return None

    async def no_reentry(
        self: JiraDeliveryTrigger,
        jira_site: str,
        trigger_jql: str,
        key: str,
        *,
        finished_at: datetime,
        consumed_event_id: str | None = None,
    ) -> None:
        assert key == run.story_key and finished_at == run.finished_at
        return None

    monkeypatch.setattr(JiraDeliveryTrigger, "find_candidate", no_candidate)
    monkeypatch.setattr(JiraDeliveryTrigger, "reentered", no_reentry)
    result = asyncio.run(
        run_poll(
            workspace,
            workspace_id,
            service.settings_store.load(workspace_id).auto_delivery,
            state_root=state,
        )
    )
    assert result.final_text == "AUTO_DELIVERY_IDLE"
    assert service.run_store.load(workspace, run.run_id).attempt == 1


def test_http_resume_stop_scope_and_stale_attempt_guards(
    lab: tuple[Path, Path, UUID, DeliveryService],
) -> None:
    state, workspace, workspace_id, service = lab
    run = blocked(workspace, workspace_id, service)
    dashboard = DashboardService(state_root=state)

    class WaitingRunner:
        async def run(
            self,
            root: Path,
            prompt: str,
            *,
            on_progress: ProgressCallback | None = None,
            on_event: AgentEventCallback | None = None,
        ) -> AgentResult:
            await asyncio.Event().wait()
            return AgentResult(status="succeeded", final_text="never")

    def factory(_config: AgentConfig) -> AgentRunner:
        return cast(AgentRunner, WaitingRunner())

    dashboard.delivery_tasks.runner_factory = factory
    prefix = f"/api/workspaces/{workspace_id}/deliveries/{run.run_id}"
    with TestClient(create_app(dashboard)) as raw_client:
        client = cast(httpx.Client, raw_client)
        assert client.post(prefix + "/resume", json={"attempt": 0}).status_code == 422
        assert client.post(prefix + "/resume", json={"attempt": 1}).status_code == 202
        assert client.post(prefix + "/resume", json={"attempt": 1}).status_code == 409
        assert client.post(prefix + "/stop", json={"attempt": 1}).status_code == 409
        history = client.get(f"/api/workspaces/{workspace_id}/deliveries").json()
        assert history["runs"][0]["attempt"] == 2 and history["runs"][0]["stopping"] is False
        assert client.post(prefix + "/stop", json={"attempt": 2}).status_code == 202
        foreign = client.post(
            f"/api/workspaces/{uuid4()}/deliveries/{run.run_id}/stop", json={"attempt": 2}
        )
        assert foreign.status_code == 404
    # Lifespan shutdown also awaits owned tasks; the badge cannot remain Running.
    assert service.run_store.load(workspace, run.run_id).state == DeliveryState.STOPPED


def test_jira_reentry_resumes_once_and_completed_receipt_stays_excluded(
    lab: tuple[Path, Path, UUID, DeliveryService],
    monkeypatch: pytest.MonkeyPatch,
    lifecycle_notifications: list[tuple[DeliveryEvent, int]],
) -> None:
    state, workspace, workspace_id, service = lab
    run = blocked(workspace, workspace_id, service)
    matches: list[str] = []

    async def no_fresh(
        self: JiraDeliveryTrigger,
        jira_site: str,
        trigger_jql: str,
        *,
        excluded_keys: frozenset[str],
    ) -> None:
        assert run.story_key in excluded_keys
        return None

    async def reentry(
        self: JiraDeliveryTrigger,
        jira_site: str,
        trigger_jql: str,
        key: str,
        *,
        finished_at: datetime,
        consumed_event_id: str | None = None,
    ) -> JiraDeliveryCandidate:
        matches.append(key)
        return JiraDeliveryCandidate(
            key, "Updated requirement", f"https://{jira_site}/browse/{key}"
        )

    class CompletingRunner:
        async def run(
            self,
            root: Path,
            prompt: str,
            *,
            on_progress: ProgressCallback | None = None,
            on_event: AgentEventCallback | None = None,
        ) -> AgentResult:
            current = service.run_store.load(root, run.run_id)
            assert current.attempt == 2 and "Explicit continuation" in prompt
            service.complete(root, workspace_id, current, "Done", phase="handoff")
            return AgentResult(status="succeeded", final_text="Done")

    monkeypatch.setattr(JiraDeliveryTrigger, "find_candidate", no_fresh)
    monkeypatch.setattr(JiraDeliveryTrigger, "reentered", reentry)
    settings = service.settings_store.load(workspace_id).auto_delivery

    def factory(_config: AgentConfig) -> AgentRunner:
        return cast(AgentRunner, CompletingRunner())

    asyncio.run(
        run_poll(workspace, workspace_id, settings, state_root=state, runner_factory=factory)
    )
    assert service.run_store.load(workspace, run.run_id).state == DeliveryState.COMPLETED
    result = asyncio.run(
        run_poll(workspace, workspace_id, settings, state_root=state, runner_factory=factory)
    )
    assert result.final_text == "AUTO_DELIVERY_IDLE" and matches == [run.story_key]
    assert lifecycle_notifications == [
        (DeliveryEvent.STARTED, 1),
        (DeliveryEvent.BLOCKED, 1),
        (DeliveryEvent.STARTED, 2),
        (DeliveryEvent.DEV_DONE, 2),
    ]


def test_detection_has_one_total_time_budget_before_starting_agent(
    lab: tuple[Path, Path, UUID, DeliveryService], monkeypatch: pytest.MonkeyPatch
) -> None:
    state, workspace, workspace_id, service = lab

    async def stalled(
        self: JiraDeliveryTrigger,
        jira_site: str,
        trigger_jql: str,
        *,
        excluded_keys: frozenset[str],
    ) -> None:
        await asyncio.Event().wait()

    monkeypatch.setattr(JiraDeliveryTrigger, "find_candidate", stalled)
    monkeypatch.setattr("lumon.delivery.execution._DETECTION_TIMEOUT_SECONDS", 0.02)
    with pytest.raises(PreflightError, match="time budget"):
        asyncio.run(
            run_poll(
                workspace,
                workspace_id,
                service.settings_store.load(workspace_id).auto_delivery,
                state_root=state,
            )
        )
    assert service.run_store.list(workspace) == ()
    assert service.run_store.list_polls(workspace)[0].state == DeliveryPollState.FAILED
