"""Manual execution uses saved workflows and the scheduled-run exclusion lock."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from lumon.agents.agent.config import AgentConfig, AgentConfigStore
from lumon.agents.agent.model import AgentResult
from lumon.agents.agent.runner import CodexAgentRunner
from lumon.dashboard.routes import create_app
from lumon.dashboard.service import DashboardService
from lumon.errors import AgentRuntimeError, PreflightError
from lumon.flows.catalog import FlowCatalog
from lumon.flows.scheduler import flow_lock
from lumon.flows.service import FlowService
from lumon.skills.installer import SkillInstaller
from lumon.tools.codex import CodexTool
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.model import InitRequest
from lumon.workspace.registry import WorkspaceRegistry
from lumon.workspace.settings import WorkspaceSettingsStore


def _client(dashboard: DashboardService) -> httpx.Client:
    return TestClient(create_app(dashboard))


class _Runner(CodexAgentRunner):
    def __init__(self) -> None:
        super().__init__(tool=CodexTool(binary="/unused/codex"))
        self.calls: list[tuple[Path, str]] = []
        self.result = AgentResult(status="succeeded", final_text="private workflow output")
        self.waiting: asyncio.Event | None = None

    async def run(self, workspace: Path, prompt: str, **_: object) -> AgentResult:
        self.calls.append((workspace, prompt))
        if self.waiting is not None:
            await self.waiting.wait()
        return self.result


@pytest.fixture
def execution(tmp_path: Path) -> tuple[FlowService, UUID, Path, _Runner]:
    registry = WorkspaceRegistry(tmp_path / "state")
    settings = WorkspaceSettingsStore(tmp_path / "state")
    workspace = tmp_path / "workspace"
    WorkspaceInitializer(
        registry=registry,
        settings_store=settings,
        skill_installer=SkillInstaller(tmp_path / "skills"),
    ).initialize(InitRequest(workspace, name="Manual workflow test"))
    workspace_id = registry.list()[0].workspace_id
    FlowCatalog(workspace).create(
        '---\nid = "manual-check"\nname = "Manual check"\nenabled = true\n'
        'brief = "Run only this saved check."\n---\n\n# Saved workflow instructions\n'
    )
    config_store = AgentConfigStore(tmp_path / "state")
    config_store.save(
        AgentConfig(enabled=True, feishu_app_id="test", feishu_app_secret="test-secret")
    )
    runner = _Runner()
    return FlowService(registry, config_store, runner), workspace_id, workspace, runner


def test_manual_run_uses_saved_workflow_without_changing_disabled_schedule(
    execution: tuple[FlowService, UUID, Path, _Runner],
) -> None:
    service, workspace_id, workspace, runner = execution
    settings = WorkspaceSettingsStore(service.registry.layout.root)
    before = settings.load(workspace_id)
    result = asyncio.run(service.run(workspace_id, "manual-check"))
    assert result.status == "succeeded"
    assert len(runner.calls) == 1
    assert runner.calls[0][0] == workspace
    assert "manual-check" in runner.calls[0][1]
    assert "# Saved workflow instructions" in runner.calls[0][1]
    assert settings.load(workspace_id) == before
    assert before.flow_schedules == ()


@pytest.mark.parametrize("unavailable", ["disabled", "invalid", "missing", "agent_disabled"])
def test_unavailable_workflows_do_not_start_agent(
    execution: tuple[FlowService, UUID, Path, _Runner], unavailable: str
) -> None:
    service, workspace_id, workspace, runner = execution
    catalog = FlowCatalog(workspace)
    if unavailable == "disabled":
        catalog.save(
            catalog.read("manual-check").content.replace("enabled = true", "enabled = false")
        )
    elif unavailable == "invalid":
        (workspace / "lumon/flows/manual-check.md").write_text("invalid", encoding="utf-8")
    elif unavailable == "missing":
        catalog.delete("manual-check")
    else:
        store = service.agent_config_store
        store.save(replace(store.load(), enabled=False))
    with pytest.raises(PreflightError):
        asyncio.run(service.run(workspace_id, "manual-check"))
    assert runner.calls == []


def test_manual_run_shares_the_scheduled_run_lock(
    execution: tuple[FlowService, UUID, Path, _Runner],
) -> None:
    service, workspace_id, _workspace, runner = execution
    with flow_lock(service.registry.layout.root, workspace_id, "manual-check"):
        with pytest.raises(PreflightError, match="already has a run"):
            asyncio.run(service.run(workspace_id, "manual-check"))
    assert runner.calls == []
    assert asyncio.run(service.run(workspace_id, "manual-check")).status == "succeeded"


def test_failure_and_cancellation_release_the_workflow_lock(
    execution: tuple[FlowService, UUID, Path, _Runner],
) -> None:
    service, workspace_id, _workspace, runner = execution
    runner.result = AgentResult(status="failed")
    with pytest.raises(AgentRuntimeError, match="Workflow did not complete"):
        asyncio.run(service.run(workspace_id, "manual-check"))

    async def cancel() -> None:
        runner.waiting = asyncio.Event()
        task = asyncio.create_task(service.run(workspace_id, "manual-check"))
        await asyncio.sleep(0)
        assert len(runner.calls) == 2
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(cancel())
    runner.waiting = None
    runner.result = AgentResult(status="succeeded", final_text="done")
    assert asyncio.run(service.run(workspace_id, "manual-check")).status == "succeeded"


def test_manual_execution_http_contract_and_errors(
    execution: tuple[FlowService, UUID, Path, _Runner],
) -> None:
    service, workspace_id, _workspace, runner = execution
    dashboard = DashboardService(
        registry=service.registry,
        settings_store=WorkspaceSettingsStore(service.registry.layout.root),
        agent_config_store=service.agent_config_store,
        flow_service=service,
    )
    client = _client(dashboard)
    url = f"/api/workspaces/{workspace_id}/flows/manual-check/run"
    assert client.get(url).status_code == 405
    assert runner.calls == []
    response = client.post(url)
    assert response.status_code == 200
    assert response.json() == {"status": "completed", "flow_id": "manual-check"}
    assert "private workflow output" not in response.text
    with flow_lock(service.registry.layout.root, workspace_id, "manual-check"):
        assert client.post(url).status_code == 409
    assert len(runner.calls) == 1
    runner.result = AgentResult(status="timed_out")
    assert client.post(url).status_code == 400
    assert client.post(f"/api/workspaces/{uuid4()}/flows/manual-check/run").status_code == 404
    assert client.post(f"/api/workspaces/{workspace_id}/flows/missing/run").status_code == 409
