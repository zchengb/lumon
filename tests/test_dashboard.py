"""HTTP contract tests for the local Dashboard."""

from __future__ import annotations

import socket
from collections.abc import Awaitable, Callable
from dataclasses import replace
from pathlib import Path
from urllib.request import Request
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from lumon.agents.agent.config import AgentConfig, AgentConfigStore
from lumon.agents.agent.model import AgentRunResult, InboundMessage, Message
from lumon.agents.agent.session_store import AgentSessionStore
from lumon.dashboard.routes import create_app
from lumon.dashboard.server import DashboardServer, create_dashboard_app, select_port
from lumon.dashboard.service import DashboardService
from lumon.errors import AgentRuntimeError, PreflightError
from lumon.scan.model import ScanRun, ScanState
from lumon.scan.store import ScanRunStore
from lumon.skills.installer import SkillInstaller
from lumon.tools.codex_models import CodexModel
from lumon.tools.codex_status import CodexCliUpdateChecker
from lumon.tools.feishu_directory import FeishuDirectory, FeishuDisplayNames
from lumon.tools.feishu_webhook import FeishuWebhookSender
from lumon.version import __version__
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.model import InitRequest
from lumon.workspace.registry import WorkspaceRegistry
from lumon.workspace.settings import (
    AutoDeliverySettings,
    AutoScanSettings,
    FlowScheduleSettings,
    WorkspaceSettingsStore,
)


class _NoopDeliveryScheduler:
    def apply(
        self,
        workspace: Path,
        workspace_id: UUID,
        settings: AutoDeliverySettings,
    ) -> None:
        del workspace, workspace_id, settings


class _NoopScanScheduler:
    def apply(
        self,
        workspace: Path,
        workspace_id: UUID,
        settings: AutoScanSettings,
    ) -> None:
        del workspace, workspace_id, settings


class _RecordingFlowScheduler:
    def __init__(self) -> None:
        self.calls: list[FlowScheduleSettings] = []

    def apply(
        self,
        workspace: Path,
        workspace_id: UUID,
        schedule: FlowScheduleSettings,
    ) -> None:
        del workspace, workspace_id
        self.calls.append(schedule)


class _RecordingDeliveryScheduler:
    def __init__(self) -> None:
        self.calls: list[AutoDeliverySettings] = []
        self.fail = False

    def apply(
        self,
        workspace: Path,
        workspace_id: UUID,
        settings: AutoDeliverySettings,
    ) -> None:
        del workspace, workspace_id
        self.calls.append(settings)
        if self.fail:
            raise PreflightError("scheduler test failure")


class _RecordingScanScheduler:
    def __init__(self) -> None:
        self.calls: list[AutoScanSettings] = []
        self.fail = False

    def apply(
        self,
        workspace: Path,
        workspace_id: UUID,
        settings: AutoScanSettings,
    ) -> None:
        del workspace, workspace_id
        self.calls.append(settings)
        if self.fail:
            raise PreflightError("scheduler test failure")


def _flow_content(
    flow_id: str = "dashboard-flow",
    brief: str = "Handle a dashboard request.",
    *,
    enabled: bool = True,
) -> str:
    enabled_value = "true" if enabled else "false"
    return (
        "---\n"
        f'id = "{flow_id}"\n'
        'name = "Dashboard flow"\n'
        f"enabled = {enabled_value}\n"
        f'brief = "{brief}"\n'
        "---\n\n"
        "# Dashboard flow\n\n"
        "Follow the dashboard flow.\n"
    )


def _capability_content(
    capability_id: str = "dashboard-capability",
    *,
    enabled: bool = True,
    brief: str = "Handle a dashboard capability.",
) -> str:
    enabled_value = "true" if enabled else "false"
    return (
        "---\n"
        f'id = "{capability_id}"\n'
        'name = "Dashboard capability"\n'
        f"enabled = {enabled_value}\n"
        f'brief = "{brief}"\n'
        "---\n\n"
        "# Dashboard capability\n\n"
        "Follow the dashboard capability.\n"
    )


class _Response:
    status = 200

    def read(self, amount: int = -1) -> bytes:
        del amount
        return b'{"code": 0}'

    def close(self) -> None:
        pass


def _opener(request: Request, timeout: float) -> _Response:
    del request, timeout
    return _Response()


def _service(
    tmp_path: Path,
    folder_picker: Callable[[], Path | None] | None = None,
    flow_scheduler: _RecordingFlowScheduler | None = None,
    model_loader: Callable[[], Awaitable[tuple[CodexModel, ...]]] | None = None,
    codex_update_checker: CodexCliUpdateChecker | None = None,
) -> DashboardService:
    state_root = tmp_path / "user-state"
    registry = WorkspaceRegistry(state_root)
    settings = WorkspaceSettingsStore(state_root)
    initializer = WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"),
        registry=registry,
        settings_store=settings,
    )
    return DashboardService(
        registry=registry,
        settings_store=settings,
        initializer=initializer,
        webhook_sender=FeishuWebhookSender(opener=_opener),
        folder_picker=folder_picker,
        delivery_scheduler=_NoopDeliveryScheduler(),
        scan_scheduler=_NoopScanScheduler(),
        flow_scheduler=flow_scheduler or _RecordingFlowScheduler(),
        model_loader=model_loader,
        codex_update_checker=codex_update_checker,
    )


def _client(service: DashboardService) -> httpx.Client:
    return TestClient(create_app(service))


def _static_client(service: DashboardService, static_dir: Path) -> httpx.Client:
    return TestClient(create_dashboard_app(service, static_dir=static_dir))


def test_empty_registry_exposes_onboarding_state(tmp_path: Path) -> None:
    client = _client(_service(tmp_path))

    assert client.get("/api/health").json()["ok"] is True
    assert client.get("/api/bootstrap").json() == {
        "version": __version__,
        "workspace_count": 0,
        "has_workspaces": False,
    }
    assert client.get("/api/workspaces").json() == []


@pytest.mark.parametrize("chat_type", ["p2p", "group"])
def test_chat_history_http_contract_is_read_only_and_workspace_scoped(
    tmp_path: Path, chat_type: str
) -> None:
    service = _service(tmp_path)
    _, registration = service.initialize_workspace(tmp_path / "workspace", None, ())
    workspace_id = registration.workspace_id
    client = _client(service)
    base = f"/api/workspaces/{workspace_id}/conversations"
    assert client.get(base).json() == {"items": [], "total": 0}
    assert not (service.registry.layout.root / "agent.sqlite3").exists()
    store = AgentSessionStore(service.registry.layout.root)
    message = InboundMessage(
        event_id="event-one",
        message_id="message-one",
        chat_id="chat-one",
        chat_type=chat_type,
        text="password=secret-test-value",
        sender_id="user-one",
        sender_type="user",
    )
    session = store.get_or_create_session(message)
    assert store.claim_event(message.event_id, message)
    store.record_message(
        Message(
            conversation_key=message.conversation_key,
            direction="inbound",
            text=message.text,
            created_at="2026-09-30T04:00:00Z",
            message_id=message.message_id,
            session_id=session.session_id,
        )
    )
    store.attach_workspace(message.event_id, workspace_id)
    store.record_result(
        AgentRunResult(
            run_id="failed-run",
            event_id=message.event_id,
            conversation_key=message.conversation_key,
            status="failed",
            started_at="2026-09-30T04:00:00Z",
            ended_at="2026-09-30T04:01:00Z",
            workspace_id=workspace_id,
            session_id=session.session_id,
            error_code="agent_failed",
            prompt_text="PRIVATE RAW PROMPT",
            failure_diagnostic="PRIVATE DIAGNOSTIC",
        )
    )
    snapshot = store.path.read_bytes()

    kind = "direct" if chat_type == "p2p" else "group"
    listed = client.get(base, params={"kind": kind, "search": "user-one"})
    assert listed.status_code == 200
    assert listed.headers["cache-control"] == "no-store"
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["status"] == "failed"
    assert listed.json()["items"][0]["duration_seconds"] == 60
    assert listed.json()["items"][0]["output_preview"] == ""
    assert listed.json()["items"][0]["chat_name"] is None
    assert listed.json()["items"][0]["sender_name"] is None

    lookups: list[tuple[tuple[str, ...], tuple[str, ...]]] = []

    def resolve_names(
        app_id: str, secret: str, chats: tuple[str, ...], users: tuple[str, ...]
    ) -> FeishuDisplayNames:
        assert app_id == "cli_test" and secret == "test-secret"
        lookups.append((chats, users))
        return FeishuDisplayNames(
            chat_names={"chat-one": "MBPass Engineering"} if chats else {},
            user_names={"user-one": "Alice Li"},
        )

    service.feishu_directory = FeishuDirectory(lookup=resolve_names)
    service.agent_config_store.save(
        AgentConfig(feishu_app_id="cli_test", feishu_app_secret="test-secret")
    )
    named = client.get(base)
    assert named.status_code == 200
    assert named.json()["items"][0]["sender_name"] == "Alice Li"
    assert named.json()["items"][0]["chat_name"] == (
        "MBPass Engineering" if chat_type == "group" else None
    )
    expected_lookup = (("chat-one",) if chat_type == "group" else (), ("user-one",))
    assert lookups == [expected_lookup]
    assert "test-secret" not in named.text
    detail = client.get(f"{base}/failed-run")
    assert detail.status_code == 200
    assert detail.headers["cache-control"] == "no-store"
    assert detail.json() == {
        "run_id": "failed-run",
        "input_text": "password=[REDACTED]",
        "output_text": "",
    }
    assert "PRIVATE" not in detail.text and "secret-test-value" not in detail.text
    assert lookups == [expected_lookup]
    assert client.get(f"{base}/{session.session_id}").status_code == 404
    assert "secret-test-value" not in listed.text
    assert "PRIVATE" not in listed.text
    assert "prompt_text" not in listed.text
    assert "failure_diagnostic" not in listed.text
    assert client.get(f"{base}/{uuid4()}").status_code == 404
    assert client.get(f"/api/workspaces/{uuid4()}/conversations").status_code == 404
    assert client.get(f"/api/workspaces/{uuid4()}/conversations/failed-run").status_code == 404
    assert lookups == [expected_lookup]
    for parameters in (
        {"limit": 0},
        {"limit": 51},
        {"offset": -1},
        {"offset": 10**30},
        {"kind": "invalid"},
        {"search": "x" * 201},
    ):
        assert client.get(base, params=parameters).status_code == 422
    assert client.post(base, json={}).status_code == 405
    assert store.path.read_bytes() == snapshot


def test_agent_settings_are_available_with_safe_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    client = _client(_service(tmp_path))

    response = client.get("/api/agent/settings")

    assert response.status_code == 200
    assert response.json() == {
        "enabled": False,
        "default_workspace_id": None,
        "agent_provider": "codex",
        "agent_model": "gpt-5.6-luna",
        "agent_reasoning_effort": "max",
        "feishu_app_id": "",
        "feishu_app_configured": False,
        "feishu_app_secret_masked": None,
        "observability": {
            "enabled": False,
            "provider": "langfuse",
            "base_url": "https://cloud.langfuse.com",
            "sample_rate": 1.0,
            "public_key_configured": False,
            "secret_key_configured": False,
            "public_key_masked": None,
            "secret_key_masked": None,
        },
    }


def test_agent_settings_masks_environment_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-environment-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-environment-test")

    response = _client(_service(tmp_path)).get("/api/agent/settings")

    assert response.status_code == 200
    assert response.json()["observability"]["public_key_masked"] == "pk-l**************test"
    assert response.json()["observability"]["secret_key_masked"] == "sk-l**************test"
    assert "pk-lf-environment-test" not in response.text
    assert "sk-lf-environment-test" not in response.text


def test_agent_model_catalog_is_read_only_and_not_cached(tmp_path: Path) -> None:
    async def models() -> tuple[CodexModel, ...]:
        return (CodexModel("future-model", "Future model", "Description", "none", ("none", "max")),)

    service = _service(tmp_path, model_loader=models)
    service.agent_config_store.save(
        AgentConfig(feishu_app_id="cli_test", feishu_app_secret="secret-value")
    )
    config_snapshot = service.agent_config_store.path.read_bytes()
    client = _client(service)
    response = client.get("/api/agent/models")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == [
        {
            "model": "future-model",
            "display_name": "Future model",
            "description": "Description",
            "default_reasoning_effort": "none",
            "supported_reasoning_efforts": ["none", "max"],
        }
    ]
    assert "secret-value" not in response.text
    assert service.agent_config_store.path.read_bytes() == config_snapshot
    assert service.registry.list() == ()
    assert client.post("/api/agent/models", json={}).status_code == 405


def test_codex_update_notice_is_read_only_and_manual_refresh_bypasses_cache(tmp_path: Path) -> None:
    latest_calls: list[str] = []

    def latest() -> str:
        latest_calls.append("latest")
        return "0.160.0"

    checker = CodexCliUpdateChecker(
        binary="/test/codex", version_reader=lambda _: "0.156.1", latest_reader=latest
    )
    service = _service(tmp_path, codex_update_checker=checker)
    service.agent_config_store.save(
        AgentConfig(feishu_app_id="cli_test", feishu_app_secret="secret-value")
    )
    config_snapshot = service.agent_config_store.path.read_bytes()
    client = _client(service)
    response = client.get("/api/agent/codex-status")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "status": "update_available",
        "binary_path": "/test/codex",
        "installed_version": "0.156.1",
        "latest_version": "0.160.0",
    }
    assert "secret-value" not in response.text
    assert client.get("/api/agent/codex-status").status_code == 200
    assert len(latest_calls) == 1
    assert client.get("/api/agent/codex-status?refresh=true").status_code == 200
    assert len(latest_calls) == 2
    assert client.post("/api/agent/codex-status", json={}).status_code == 405
    assert service.agent_config_store.path.read_bytes() == config_snapshot
    assert service.registry.list() == ()


def test_codex_update_failure_does_not_block_models_or_settings(tmp_path: Path) -> None:
    def latest() -> str:
        raise TimeoutError("secret-value")

    async def models() -> tuple[CodexModel, ...]:
        return ()

    checker = CodexCliUpdateChecker(
        binary="/test/codex", version_reader=lambda _: "0.156.1", latest_reader=latest
    )
    client = _client(_service(tmp_path, codex_update_checker=checker, model_loader=models))
    response = client.get("/api/agent/codex-status")
    assert response.status_code == 200
    assert response.json()["status"] == "check_failed"
    assert response.json()["latest_version"] is None
    assert "secret-value" not in response.text
    assert client.get("/api/agent/models").json() == []
    assert client.get("/api/agent/settings").json()["agent_model"] == "gpt-5.6-luna"


def test_agent_model_discovery_failure_does_not_break_settings(tmp_path: Path) -> None:
    async def unavailable() -> tuple[CodexModel, ...]:
        raise AgentRuntimeError("Codex model discovery timed out. Try refreshing again.")

    service = _service(tmp_path, model_loader=unavailable)
    client = _client(service)
    response = client.get("/api/agent/models")
    assert response.status_code == 400
    assert "timed out" in response.json()["error"]["message"]
    assert client.get("/api/agent/settings").json()["agent_model"] == "gpt-5.6-luna"
    assert not service.agent_config_store.path.exists()


@pytest.mark.parametrize("effort", ["none", "adaptive", "unsafe token"])
def test_agent_settings_supports_provider_efforts_but_rejects_invalid_tokens(
    tmp_path: Path, effort: str
) -> None:
    service = _service(tmp_path)
    client = _client(service)
    response = client.put(
        "/api/agent/settings",
        json={
            "enabled": False,
            "default_workspace_id": None,
            "agent_model": "future-model",
            "agent_reasoning_effort": effort,
            "feishu_app_id": "cli_test",
            "feishu_app_secret": "secret-value",
            "observability": {
                "enabled": False,
                "base_url": "https://cloud.langfuse.com",
                "sample_rate": 1,
            },
        },
    )
    if effort == "unsafe token":
        assert response.status_code == 422
        assert not service.agent_config_store.path.exists()
    else:
        assert response.status_code == 200
        assert service.agent_config_store.load().agent_reasoning_effort == effort
        assert "secret-value" not in response.text


def test_agent_settings_update_persists_secrets_and_returns_only_masks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    service = _service(tmp_path)
    client = _client(service)
    workspace_id = client.post(
        "/api/workspaces/initialize",
        json={"path": str(tmp_path / "workspace"), "repositories": []},
    ).json()["workspace_id"]

    response = client.put(
        "/api/agent/settings",
        json={
            "enabled": True,
            "default_workspace_id": None,
            "agent_model": "gpt-5.6-luna",
            "agent_reasoning_effort": "max",
            "feishu_app_id": "cli_test",
            "feishu_app_secret": "feishu-secret-value",
            "observability": {
                "enabled": True,
                "base_url": "https://us.cloud.langfuse.com",
                "sample_rate": 0.25,
                "public_key": "pk-lf-dashboard-test",
                "secret_key": "sk-lf-dashboard-test",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["default_workspace_id"] == workspace_id
    assert response.json()["observability"] == {
        "enabled": True,
        "provider": "langfuse",
        "base_url": "https://us.cloud.langfuse.com",
        "sample_rate": 0.25,
        "public_key_configured": True,
        "secret_key_configured": True,
        "public_key_masked": "pk-l************test",
        "secret_key_masked": "sk-l************test",
    }
    assert response.json()["feishu_app_secret_masked"] == "feis***********alue"
    assert "feishu-secret-value" not in response.text
    assert "pk-lf-dashboard-test" not in response.text
    assert "sk-lf-dashboard-test" not in response.text

    config = AgentConfigStore(service.agent_config_store.layout.root).load()
    assert config.feishu_app_secret == "feishu-secret-value"
    assert config.observability.public_key == "pk-lf-dashboard-test"
    assert config.observability.secret_key == "sk-lf-dashboard-test"
    assert config.observability.sample_rate == 0.25

    preserved = client.put(
        "/api/agent/settings",
        json={
            "enabled": True,
            "default_workspace_id": workspace_id,
            "agent_model": "gpt-5.6-sol",
            "agent_reasoning_effort": "high",
            "feishu_app_id": "cli_test-updated",
            "observability": {
                "enabled": True,
                "base_url": "https://us.cloud.langfuse.com",
                "sample_rate": 0.5,
            },
        },
    )

    assert preserved.status_code == 200
    updated_config = AgentConfigStore(service.agent_config_store.layout.root).load()
    assert updated_config.feishu_app_secret == "feishu-secret-value"
    assert updated_config.observability.public_key == "pk-lf-dashboard-test"
    assert updated_config.observability.secret_key == "sk-lf-dashboard-test"
    assert updated_config.agent_model == "gpt-5.6-sol"
    assert updated_config.agent_reasoning_effort == "high"


def test_agent_settings_rejects_an_unregistered_default_workspace(tmp_path: Path) -> None:
    client = _client(_service(tmp_path))

    response = client.put(
        "/api/agent/settings",
        json={
            "enabled": False,
            "default_workspace_id": "12345678-1234-5678-1234-567812345678",
            "agent_model": "gpt-5.6-luna",
            "agent_reasoning_effort": "max",
            "feishu_app_id": "cli_test",
            "feishu_app_secret": "secret-value",
            "observability": {
                "enabled": False,
                "base_url": "https://cloud.langfuse.com",
                "sample_rate": 1.0,
            },
        },
    )

    assert response.status_code == 404
    assert "not registered" in response.json()["error"]["message"]


def test_dashboard_initialization_selects_the_sole_workspace_for_agent(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    service.agent_config_store.save(
        AgentConfig(
            enabled=True,
            feishu_app_id="cli_test",
            feishu_app_secret="secret-value",
        )
    )

    _, registration = service.initialize_workspace(tmp_path / "workspace", None, ())

    assert service.agent_config_store.load().default_workspace_id == registration.workspace_id


def test_workspace_folder_picker_returns_selected_path(tmp_path: Path) -> None:
    selected = tmp_path / "selected-workspace"
    selected.mkdir()
    client = _client(_service(tmp_path, folder_picker=lambda: selected))

    response = client.post("/api/workspaces/select-folder")

    assert response.status_code == 200
    assert response.json() == {"path": str(selected), "cancelled": False}


def test_workspace_folder_picker_reports_cancellation(tmp_path: Path) -> None:
    client = _client(_service(tmp_path, folder_picker=lambda: None))

    response = client.post("/api/workspaces/select-folder")

    assert response.status_code == 200
    assert response.json() == {"path": None, "cancelled": True}


def test_initialize_and_read_workspace_overview(tmp_path: Path) -> None:
    service = _service(tmp_path)
    client = _client(service)

    response = client.post(
        "/api/workspaces/initialize",
        json={"path": str(tmp_path / "created-workspace"), "repositories": []},
    )

    assert response.status_code == 201
    workspace_id = response.json()["workspace_id"]
    overview = client.get(f"/api/workspaces/{workspace_id}/overview")
    assert overview.status_code == 200
    assert overview.json()["name"] == "created-workspace"
    assert overview.json()["repositories"] == []
    assert overview.json()["workflow_schedules"] == []


def test_overview_lists_only_saved_workflow_schedules_without_changing_jobs(
    tmp_path: Path,
) -> None:
    scheduler = _RecordingFlowScheduler()
    service = _service(tmp_path, flow_scheduler=scheduler)
    client = _client(service)
    workspace_id = client.post(
        "/api/workspaces/initialize",
        json={"path": str(tmp_path / "scheduled-workspace"), "repositories": []},
    ).json()["workspace_id"]
    flows_url = f"/api/workspaces/{workspace_id}/flows"
    for flow_id in ("auto-guard", "disabled-schedule", "disabled-workflow", "unscheduled"):
        assert client.post(flows_url, json={"content": _flow_content(flow_id)}).status_code == 201
    for flow_id, enabled in (("auto-guard", True), ("disabled-schedule", False)):
        assert (
            client.put(
                f"{flows_url}/{flow_id}/schedule",
                json={"enabled": enabled, "schedule_expression": "0 10 * * 1-5"},
            ).status_code
            == 200
        )
    assert (
        client.put(
            f"{flows_url}/disabled-workflow",
            json={"content": _flow_content("disabled-workflow", enabled=False)},
        ).status_code
        == 200
    )
    settings = service.settings_store.load(UUID(workspace_id))
    # A workflow can also be disabled by editing its Markdown outside the Dashboard.
    service.settings_store.save(
        replace(
            settings,
            flow_schedules=(
                *settings.flow_schedules,
                FlowScheduleSettings("disabled-workflow", True),
            ),
        )
    )
    profile_snapshot = service.settings_store.raw_snapshot(UUID(workspace_id))
    scheduler_calls = scheduler.calls.copy()

    response = client.get(f"/api/workspaces/{workspace_id}/overview")

    assert response.status_code == 200
    assert response.json()["workflow_schedules"] == [
        {
            "flow_id": "auto-guard",
            "name": "Dashboard flow",
            "enabled": True,
            "schedule_expression": "0 10 * * 1-5",
        },
        {
            "flow_id": "disabled-schedule",
            "name": "Dashboard flow",
            "enabled": False,
            "schedule_expression": "0 10 * * 1-5",
        },
        {
            "flow_id": "disabled-workflow",
            "name": "Dashboard flow",
            "enabled": False,
            "schedule_expression": "0 8 * * *",
        },
    ]
    assert service.settings_store.raw_snapshot(UUID(workspace_id)) == profile_snapshot
    assert scheduler.calls == scheduler_calls
    assert client.delete(f"{flows_url}/auto-guard").status_code == 204
    remaining = client.get(f"/api/workspaces/{workspace_id}/overview").json()["workflow_schedules"]
    assert [item["flow_id"] for item in remaining] == ["disabled-schedule", "disabled-workflow"]


def test_overview_workflow_schedules_are_workspace_scoped_and_skip_invalid_files(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    client = _client(service)
    workspace_ids: list[str] = []
    for name in ("one", "two"):
        target = tmp_path / name
        workspace_id = client.post(
            "/api/workspaces/initialize",
            json={"path": str(target), "repositories": []},
        ).json()["workspace_id"]
        workspace_ids.append(workspace_id)
        content = _flow_content("shared-id").replace("Dashboard flow", name)
        client.post(f"/api/workspaces/{workspace_id}/flows", json={"content": content})
        (target / "lumon" / "flows" / "broken.md").write_text("broken", encoding="utf-8")
        settings = service.settings_store.load(UUID(workspace_id))
        service.settings_store.save(
            replace(
                settings,
                flow_schedules=(
                    FlowScheduleSettings("shared-id", name == "one", "0 10 * * 1-5"),
                    FlowScheduleSettings("broken", True),
                    FlowScheduleSettings("deleted", True),
                ),
            )
        )

    for name, workspace_id in zip(("one", "two"), workspace_ids, strict=True):
        response = client.get(f"/api/workspaces/{workspace_id}/overview")
        assert response.status_code == 200
        assert response.json()["workflow_schedules"] == [
            {
                "flow_id": "shared-id",
                "name": name,
                "enabled": name == "one",
                "schedule_expression": "0 10 * * 1-5",
            }
        ]


def test_dashboard_flow_crud_edits_the_workspace_files_and_reports_validation(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    client = _client(service)
    target = tmp_path / "flow-workspace"
    workspace_id = client.post(
        "/api/workspaces/initialize",
        json={"path": str(target), "repositories": []},
    ).json()["workspace_id"]

    listed = client.get(f"/api/workspaces/{workspace_id}/flows")
    assert listed.status_code == 200
    assert listed.json() == []

    created = client.post(
        f"/api/workspaces/{workspace_id}/flows",
        json={"content": _flow_content()},
    )
    assert created.status_code == 201
    assert created.json()["flow_id"] == "dashboard-flow"
    assert (target / "lumon" / "flows" / "dashboard-flow.md").read_text(
        encoding="utf-8"
    ) == _flow_content()

    updated_content = _flow_content(brief="Updated from the Dashboard.")
    updated = client.put(
        f"/api/workspaces/{workspace_id}/flows/dashboard-flow",
        json={"content": updated_content},
    )
    assert updated.status_code == 200
    assert updated.json()["brief"] == "Updated from the Dashboard."
    assert (target / "lumon" / "flows" / "dashboard-flow.md").read_text(
        encoding="utf-8"
    ) == updated_content

    (target / "lumon" / "flows" / "broken.md").write_text("broken", encoding="utf-8")
    invalid = client.get(f"/api/workspaces/{workspace_id}/flows").json()
    broken = next(item for item in invalid if item["path"] == "lumon/flows/broken.md")
    assert broken["valid"] is False
    assert "frontmatter" in broken["error"]
    broken_document = client.get(f"/api/workspaces/{workspace_id}/flows/broken")
    assert broken_document.status_code == 200
    assert broken_document.json()["valid"] is False
    assert broken_document.json()["content"] == "broken"

    deleted = client.delete(f"/api/workspaces/{workspace_id}/flows/dashboard-flow")
    assert deleted.status_code == 204
    assert not (target / "lumon" / "flows" / "dashboard-flow.md").exists()
    assert client.delete(f"/api/workspaces/{workspace_id}/flows/broken").status_code == 204
    assert not (target / "lumon" / "flows" / "broken.md").exists()

    changed_id = client.put(
        f"/api/workspaces/{workspace_id}/flows/dashboard-flow",
        json={"content": _flow_content("other-id")},
    )
    assert changed_id.status_code == 200
    assert changed_id.json()["flow_id"] == "other-id"
    assert not (target / "lumon" / "flows" / "dashboard-flow.md").exists()
    assert (target / "lumon" / "flows" / "other-id.md").exists()


def test_flow_schedule_is_saved_applied_disabled_with_flow_and_removed_on_delete(
    tmp_path: Path,
) -> None:
    scheduler = _RecordingFlowScheduler()
    service = _service(tmp_path, flow_scheduler=scheduler)
    client = _client(service)
    target = tmp_path / "scheduled-flow-workspace"
    workspace_id = client.post(
        "/api/workspaces/initialize",
        json={"path": str(target), "repositories": []},
    ).json()["workspace_id"]
    flow_path = f"/api/workspaces/{workspace_id}/flows"
    created = client.post(flow_path, json={"content": _flow_content()})
    assert created.status_code == 201
    assert created.json()["schedule_enabled"] is False

    scheduled = client.put(
        f"{flow_path}/dashboard-flow/schedule",
        json={"enabled": True, "schedule_expression": "0 8 * * 1-5"},
    )
    assert scheduled.status_code == 200
    assert scheduled.json()["schedule_enabled"] is True
    assert scheduled.json()["schedule_expression"] == "0 8 * * 1-5"
    assert scheduler.calls[-1].enabled is True
    service.update_settings(
        UUID(workspace_id),
        enabled=False,
        url_provided=False,
        url=None,
    )
    assert service.settings_store.load(UUID(workspace_id)).flow_schedules[0].enabled is True

    disabled_flow = client.put(
        f"{flow_path}/dashboard-flow",
        json={"content": _flow_content(enabled=False)},
    )
    assert disabled_flow.status_code == 200
    assert disabled_flow.json()["schedule_enabled"] is False
    assert scheduler.calls[-1].enabled is False
    assert service.settings_store.load(UUID(workspace_id)).flow_schedules[0].enabled is False

    assert client.delete(f"{flow_path}/dashboard-flow").status_code == 204
    assert service.settings_store.load(UUID(workspace_id)).flow_schedules == ()
    assert scheduler.calls[-1].enabled is False


def test_flow_schedule_rejects_enabled_disabled_flow_and_invalid_cron(tmp_path: Path) -> None:
    service = _service(tmp_path)
    client = _client(service)
    target = tmp_path / "invalid-scheduled-flow-workspace"
    workspace_id = client.post(
        "/api/workspaces/initialize",
        json={"path": str(target), "repositories": []},
    ).json()["workspace_id"]
    flow_path = f"/api/workspaces/{workspace_id}/flows"
    client.post(flow_path, json={"content": _flow_content(enabled=False)})

    disabled = client.put(
        f"{flow_path}/dashboard-flow/schedule",
        json={"enabled": True, "schedule_expression": "0 8 * * *"},
    )
    assert disabled.status_code == 422
    assert "Enable the Flow" in disabled.json()["error"]["message"]

    invalid_cron = client.put(
        f"{flow_path}/dashboard-flow/schedule",
        json={"enabled": False, "schedule_expression": "nope"},
    )
    assert invalid_cron.status_code == 422
    assert service.settings_store.load(UUID(workspace_id)).flow_schedules == ()


def test_dashboard_capability_crud_edits_the_workspace_files_and_supports_disable(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    client = _client(service)
    target = tmp_path / "capability-workspace"
    workspace_id = client.post(
        "/api/workspaces/initialize",
        json={"path": str(target), "repositories": []},
    ).json()["workspace_id"]

    listed = client.get(f"/api/workspaces/{workspace_id}/capabilities")
    assert listed.status_code == 200
    assert listed.json() == []

    created = client.post(
        f"/api/workspaces/{workspace_id}/capabilities",
        json={"content": _capability_content()},
    )
    assert created.status_code == 201
    assert created.json()["capability_id"] == "dashboard-capability"
    assert (target / "lumon" / "capabilities" / "dashboard-capability.md").read_text(
        encoding="utf-8"
    ) == _capability_content()

    disabled_content = _capability_content(enabled=False, brief="Disabled capability.")
    updated = client.put(
        f"/api/workspaces/{workspace_id}/capabilities/dashboard-capability",
        json={"content": disabled_content},
    )
    assert updated.status_code == 200
    assert updated.json()["enabled"] is False
    assert updated.json()["brief"] == "Disabled capability."

    renamed_content = _capability_content("other-capability").replace(
        'name = "Dashboard capability"',
        'name = "Jenkins CLI"',
    )
    changed_id = client.put(
        f"/api/workspaces/{workspace_id}/capabilities/dashboard-capability",
        json={"content": renamed_content},
    )
    assert changed_id.status_code == 200
    assert changed_id.json()["capability_id"] == "other-capability"
    assert changed_id.json()["name"] == "Jenkins CLI"
    assert not (target / "lumon" / "capabilities" / "dashboard-capability.md").exists()
    assert (target / "lumon" / "capabilities" / "other-capability.md").exists()

    deleted = client.delete(f"/api/workspaces/{workspace_id}/capabilities/other-capability")
    assert deleted.status_code == 204
    assert not (target / "lumon" / "capabilities" / "other-capability.md").exists()


def test_settings_update_masks_webhook_and_test_does_not_persist_draft(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    client = _client(service)
    client.post(
        "/api/workspaces/initialize",
        json={"path": str(tmp_path / "workspace"), "repositories": []},
    )
    workspace_id = client.get("/api/workspaces").json()[0]["workspace_id"]
    url = "https://open.feishu.cn/open-apis/bot/v2/hook/private-token"

    saved = client.put(
        f"/api/workspaces/{workspace_id}/settings",
        json={"feishu_webhook": {"enabled": True, "url": url}},
    )
    assert saved.status_code == 200
    assert saved.json()["feishu_webhook"] == {
        "enabled": True,
        "configured": True,
        "masked_url": "https://open.feishu.cn/open-apis/bot/v2/hook/priv*****oken",
    }
    assert saved.json()["auto_delivery"] == {
        "enabled": False,
        "trigger_hooks": ["jira.delivery_ready"],
        "schedule_expression": "*/5 * * * *",
    }
    assert url not in saved.text

    enabled = client.put(
        f"/api/workspaces/{workspace_id}/settings",
        json={
            "feishu_webhook": {"enabled": True},
            "auto_delivery": {
                "enabled": True,
                "trigger_hooks": ["jira.delivery_ready", "mail.delivery_ready"],
                "schedule_expression": "0 9 * * 1-5",
            },
        },
    )
    assert enabled.status_code == 200
    assert enabled.json()["auto_delivery"] == {
        "enabled": True,
        "trigger_hooks": ["jira.delivery_ready", "mail.delivery_ready"],
        "schedule_expression": "0 9 * * 1-5",
    }

    tested = client.post(
        f"/api/workspaces/{workspace_id}/settings/feishu/test",
        json={"url": url},
    )
    assert tested.status_code == 200
    assert tested.json()["success"] is True
    assert url not in tested.text

    unchanged = client.get(f"/api/workspaces/{workspace_id}/settings")
    assert url not in unchanged.text

    preserved = client.put(
        f"/api/workspaces/{workspace_id}/settings",
        json={"feishu_webhook": {"enabled": False}},
    )
    assert preserved.json()["feishu_webhook"]["configured"] is True
    assert preserved.json()["auto_delivery"]["enabled"] is True
    assert preserved.json()["auto_delivery"]["trigger_hooks"] == [
        "jira.delivery_ready",
        "mail.delivery_ready",
    ]

    cleared = client.put(
        f"/api/workspaces/{workspace_id}/settings",
        json={"feishu_webhook": {"enabled": False, "url": ""}},
    )
    assert cleared.json()["feishu_webhook"]["configured"] is False


def test_workspace_settings_are_isolated_between_workspaces(tmp_path: Path) -> None:
    client = _client(_service(tmp_path))
    first = client.post(
        "/api/workspaces/initialize",
        json={"path": str(tmp_path / "first"), "repositories": []},
    ).json()["workspace_id"]
    second = client.post(
        "/api/workspaces/initialize",
        json={"path": str(tmp_path / "second"), "repositories": []},
    ).json()["workspace_id"]

    client.put(
        f"/api/workspaces/{first}/settings",
        json={
            "feishu_webhook": {
                "enabled": True,
                "url": "https://open.feishu.cn/open-apis/bot/v2/hook/first-token",
            }
        },
    )

    assert (
        client.get(f"/api/workspaces/{first}/settings").json()["feishu_webhook"]["configured"]
        is True
    )
    assert (
        client.get(f"/api/workspaces/{second}/settings").json()["feishu_webhook"]["configured"]
        is False
    )


@pytest.mark.parametrize("automation", ["auto_delivery", "auto_scan"])
def test_settings_updates_do_not_reload_unchanged_automation_schedules(
    tmp_path: Path,
    automation: str,
) -> None:
    delivery_scheduler = _RecordingDeliveryScheduler()
    scan_scheduler = _RecordingScanScheduler()
    service = _service(tmp_path)
    service.delivery_scheduler = delivery_scheduler
    service.scan_scheduler = scan_scheduler
    client = _client(service)
    workspace_id = client.post(
        "/api/workspaces/initialize",
        json={"path": str(tmp_path / "workspace"), "repositories": []},
    ).json()["workspace_id"]
    endpoint = f"/api/workspaces/{workspace_id}/settings"
    required_settings: dict[str, object] = {"lookback_days": 7} if automation == "auto_scan" else {}
    saved = client.put(
        endpoint,
        json={
            "feishu_webhook": {"enabled": False},
            automation: {
                "enabled": True,
                "schedule_expression": "0 12 * * 1-5",
                **required_settings,
            },
        },
    )
    assert saved.status_code == 200
    expected_calls = (1, 0) if automation == "auto_delivery" else (0, 1)
    assert (len(delivery_scheduler.calls), len(scan_scheduler.calls)) == expected_calls

    webhook_updates = [
        {"enabled": True, "url": "https://open.feishu.cn/open-apis/bot/v2/hook/test-token"},
        {"enabled": False},
        {"enabled": False, "url": ""},
    ]
    for webhook in webhook_updates:
        updated = client.put(endpoint, json={"feishu_webhook": webhook})
        assert updated.status_code == 200
        assert updated.json()[automation] == saved.json()[automation]
        assert (len(delivery_scheduler.calls), len(scan_scheduler.calls)) == expected_calls

    execution_settings: dict[str, object] = {"trigger_hooks": ["mail.delivery_ready"]}
    if automation == "auto_scan":
        execution_settings = {
            "lookback_days": 14,
            "trigger_hooks": [
                "Create verified Jira Bugs.\n\nReuse duplicates; include scan evidence."
            ],
            "workflow_description": "Review confirmed bugs only.",
        }
    updated = client.put(
        endpoint,
        json={
            "feishu_webhook": {"enabled": False},
            automation: {
                "enabled": True,
                "schedule_expression": "0 12 * * 1-5",
                **execution_settings,
            },
        },
    )
    assert updated.status_code == 200
    for setting, expected in execution_settings.items():
        assert updated.json()[automation][setting] == expected
    assert (len(delivery_scheduler.calls), len(scan_scheduler.calls)) == expected_calls


@pytest.mark.parametrize("automation", ["auto_delivery", "auto_scan"])
def test_automation_scheduler_is_updated_and_settings_roll_back_on_failure(
    tmp_path: Path,
    automation: str,
) -> None:
    delivery_scheduler = _RecordingDeliveryScheduler()
    scan_scheduler = _RecordingScanScheduler()
    scheduler = delivery_scheduler if automation == "auto_delivery" else scan_scheduler
    other_scheduler = scan_scheduler if automation == "auto_delivery" else delivery_scheduler
    service = _service(tmp_path)
    service.delivery_scheduler = delivery_scheduler
    service.scan_scheduler = scan_scheduler
    client = _client(service)
    workspace_id = client.post(
        "/api/workspaces/initialize",
        json={"path": str(tmp_path / "workspace"), "repositories": []},
    ).json()["workspace_id"]
    required_settings: dict[str, object] = {"lookback_days": 7} if automation == "auto_scan" else {}

    saved = client.put(
        f"/api/workspaces/{workspace_id}/settings",
        json={
            "feishu_webhook": {"enabled": False},
            automation: {
                "enabled": True,
                "trigger_hooks": ["jira.delivery_ready"],
                "schedule_expression": "*/10 * * * *",
                **required_settings,
            },
        },
    )
    assert saved.status_code == 200
    assert scheduler.calls[-1].schedule_expression == "*/10 * * * *"
    assert len(scheduler.calls) == 1
    assert not other_scheduler.calls

    rescheduled = client.put(
        f"/api/workspaces/{workspace_id}/settings",
        json={
            "feishu_webhook": {"enabled": False},
            automation: {
                "enabled": True,
                "schedule_expression": "*/15 * * * *",
                **required_settings,
            },
        },
    )
    assert rescheduled.status_code == 200
    assert scheduler.calls[-1].schedule_expression == "*/15 * * * *"
    assert len(scheduler.calls) == 2
    assert not other_scheduler.calls

    snapshot = service.settings_store.raw_snapshot(UUID(workspace_id))

    scheduler.fail = True
    failed = client.put(
        f"/api/workspaces/{workspace_id}/settings",
        json={
            "feishu_webhook": {"enabled": False},
            automation: {
                "enabled": False,
                "trigger_hooks": ["jira.delivery_ready"],
                "schedule_expression": "*/30 * * * *",
                **required_settings,
            },
        },
    )
    assert failed.status_code == 409
    assert len(scheduler.calls) == 3
    assert not other_scheduler.calls
    assert service.settings_store.raw_snapshot(UUID(workspace_id)) == snapshot

    scheduler.fail = False
    disabled = client.put(
        f"/api/workspaces/{workspace_id}/settings",
        json={
            "feishu_webhook": {"enabled": False},
            automation: {"enabled": False, **required_settings},
        },
    )
    assert disabled.status_code == 200
    assert scheduler.calls[-1].enabled is False
    assert len(scheduler.calls) == 4
    assert not other_scheduler.calls


def test_auto_scan_settings_and_history_are_available_from_dashboard(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    client = _client(service)
    workspace_id = client.post(
        "/api/workspaces/initialize",
        json={"path": str(tmp_path / "workspace"), "repositories": []},
    ).json()["workspace_id"]

    defaults = client.get(f"/api/workspaces/{workspace_id}/settings")
    assert defaults.status_code == 200
    assert defaults.json()["auto_scan"] == {
        "enabled": False,
        "lookback_days": 7,
        "trigger_hooks": [],
        "schedule_expression": "0 12 * * 1-5",
        "workflow_description": (
            "Review recent repository changes for confirmed production-impacting bugs. "
            "Keep the review evidence-based and report-only."
        ),
    }

    saved = client.put(
        f"/api/workspaces/{workspace_id}/settings",
        json={
            "feishu_webhook": {"enabled": False},
            "auto_scan": {
                "enabled": True,
                "lookback_days": 14,
                "trigger_hooks": ["twg.create_bug"],
                "schedule_expression": "0 9 * * 1-5",
                "workflow_description": "Create a bug through the Workspace completion hook.",
            },
        },
    )
    assert saved.status_code == 200
    assert saved.json()["auto_scan"] == {
        "enabled": True,
        "lookback_days": 14,
        "trigger_hooks": ["twg.create_bug"],
        "schedule_expression": "0 9 * * 1-5",
        "workflow_description": "Create a bug through the Workspace completion hook.",
    }
    assert client.get(f"/api/workspaces/{workspace_id}/scans").json() == []


def test_completion_prompt_saves_only_to_selected_workspace(tmp_path: Path) -> None:
    service = _service(tmp_path)
    client = _client(service)
    workspace_ids = [
        client.post(
            "/api/workspaces/initialize",
            json={
                "path": str(tmp_path / name),
                "repositories": [],
            },
        ).json()["workspace_id"]
        for name in ("first", "second")
    ]
    endpoint = f"/api/workspaces/{workspace_ids[0]}/settings"
    prompt = 'Create verified Jira Bugs.\n\nInclude "code evidence" and reuse duplicates.'

    saved = client.put(
        endpoint,
        json={
            "feishu_webhook": {"enabled": False},
            "auto_scan": {"enabled": False, "lookback_days": 7, "trigger_hooks": [prompt]},
        },
    )

    assert saved.status_code == 200
    assert client.get(endpoint).json()["auto_scan"]["trigger_hooks"] == [prompt]
    assert (
        client.get(f"/api/workspaces/{workspace_ids[1]}/settings").json()["auto_scan"][
            "trigger_hooks"
        ]
        == []
    )
    assert AutoScanSettings().trigger_hooks == ()

    rejected = client.put(
        endpoint,
        json={
            "feishu_webhook": {"enabled": False},
            "auto_scan": {"enabled": False, "lookback_days": 7, "trigger_hooks": ["x" * 8001]},
        },
    )
    assert rejected.status_code == 422
    assert client.get(endpoint).json()["auto_scan"]["trigger_hooks"] == [prompt]


@pytest.mark.parametrize(
    ("kind", "media_type", "disposition", "content"),
    [
        ("html", "text/html", "inline", b"<h1>Scan report</h1>"),
        ("pdf", "application/pdf", "attachment", b"%PDF-1.4 test report"),
    ],
)
def test_scan_reports_display_html_inline_and_download_pdf(
    tmp_path: Path, kind: str, media_type: str, disposition: str, content: bytes
) -> None:
    client = _client(_service(tmp_path))
    workspace = tmp_path / "workspace"
    workspace_id = client.post(
        "/api/workspaces/initialize",
        json={"path": str(workspace), "repositories": []},
    ).json()["workspace_id"]
    run = ScanRun.start("scan-report", 7)
    run = replace(
        run,
        state=ScanState.COMPLETED,
        phase="completed",
        finished_at=run.started_at,
        html_path="report.html",
        pdf_path="report.pdf",
    )
    store = ScanRunStore()
    store.save(workspace, run)
    filename = f"report.{kind}"
    (store.path_for(workspace, run.run_id) / filename).write_bytes(content)

    response = client.get(f"/api/workspaces/{workspace_id}/scans/{run.run_id}/artifacts/{kind}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(media_type)
    assert response.headers["content-disposition"] == f'{disposition}; filename="{filename}"'
    assert response.content == content


def test_scan_history_reconciles_abandoned_runs_without_inventing_elapsed_time(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    client = _client(service)
    workspace = tmp_path / "workspace"
    workspace_id = client.post(
        "/api/workspaces/initialize",
        json={"path": str(workspace), "repositories": []},
    ).json()["workspace_id"]
    store = ScanRunStore()
    run = ScanRun.start("interrupted-scan", 7)
    store.save(workspace, run)

    response = client.get(f"/api/workspaces/{workspace_id}/scans")

    assert response.status_code == 200
    receipt = response.json()[0]
    assert receipt["state"] == "failed"
    assert receipt["phase"] == "review"
    assert receipt["findings"] == []
    assert receipt["finished_at"] is None
    assert receipt["duration_seconds"] is None
    assert "interrupted" in receipt["failures"][0]
    assert receipt["hook_results"] == []
    assert store.load(workspace, run.run_id).state is ScanState.FAILED
    assert client.get(f"/api/workspaces/{workspace_id}/scans").json() == response.json()


def test_register_existing_workspace_returns_registry_item(tmp_path: Path) -> None:
    service = _service(tmp_path)
    target = tmp_path / "workspace"
    service.initializer.initialize(InitRequest(target))
    client = _client(service)

    response = client.post("/api/workspaces/register", json={"path": str(target)})

    assert response.status_code == 201
    assert response.json()["health"] == "ready"


def test_bundled_frontend_is_served_after_build(tmp_path: Path) -> None:
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<h1>Lumon test</h1>", encoding="utf-8")
    client = _static_client(_service(tmp_path), static_dir)

    response = client.get("/")

    assert response.status_code == 200
    assert "Lumon test" in response.text


def test_dashboard_server_is_loopback_only_and_supports_injected_runner() -> None:
    captured: dict[str, object] = {}

    def runner(application: object, **options: object) -> None:
        captured["application"] = application
        captured.update(options)

    server = DashboardServer(
        browser_opener=lambda _: True,
        runner=runner,
    )
    server.run(port=0, open_browser=False)

    assert captured["host"] == "127.0.0.1"
    assert isinstance(captured["port"], int)
    assert int(captured["port"]) > 0


def test_dashboard_server_uses_fixed_default_port(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ports: list[int] = []
    captured: dict[str, object] = {}

    def select(requested: int) -> int:
        ports.append(requested)
        return requested

    def runner(application: object, **options: object) -> None:
        del application
        captured.update(options)

    monkeypatch.setenv("LUMON_HOME", str(tmp_path / "state"))
    monkeypatch.setattr("lumon.dashboard.server.select_port", select)
    DashboardServer(runner=runner).run(open_browser=False)

    assert ports == [15778]
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 15778


def test_dashboard_server_selects_requested_workspace_in_browser_url() -> None:
    captured: dict[str, str] = {}

    def browser_opener(url: str) -> bool:
        captured["url"] = url
        return True

    def runner(application: object, **options: object) -> None:
        del application, options

    server = DashboardServer(
        browser_opener=browser_opener,
        runner=runner,
        initial_workspace_id=UUID("12345678-1234-5678-1234-567812345678"),
    )
    server.run(port=0, open_browser=True)

    assert captured["url"].endswith(
        "/?workspace=12345678-1234-5678-1234-567812345678&view=overview"
    )


def test_select_port_rejects_invalid_port() -> None:
    from lumon.errors import PreflightError

    with pytest.raises(PreflightError, match="between 0 and 65535"):
        select_port(-1)


def test_select_port_does_not_switch_when_requested_port_is_occupied() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        occupied_port = listener.getsockname()[1]
        with pytest.raises(PreflightError, match=f"port is unavailable: {occupied_port}"):
            select_port(occupied_port)
