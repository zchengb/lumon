"""HTTP contract tests for the local Dashboard."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from urllib.request import Request
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient

from lumon.dashboard.routes import create_app
from lumon.dashboard.server import DashboardServer, create_dashboard_app, select_port
from lumon.dashboard.service import DashboardService
from lumon.skills.installer import SkillInstaller
from lumon.tools.feishu_webhook import FeishuWebhookSender
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.model import InitRequest
from lumon.workspace.registry import WorkspaceRegistry
from lumon.workspace.settings import WorkspaceSettingsStore


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
    )


def _client(service: DashboardService) -> httpx.Client:
    return TestClient(create_app(service))


def _static_client(service: DashboardService, static_dir: Path) -> httpx.Client:
    return TestClient(create_dashboard_app(service, static_dir=static_dir))


def test_empty_registry_exposes_onboarding_state(tmp_path: Path) -> None:
    client = _client(_service(tmp_path))

    assert client.get("/api/health").json()["ok"] is True
    assert client.get("/api/bootstrap").json() == {
        "version": "1.0.6",
        "workspace_count": 0,
        "has_workspaces": False,
    }
    assert client.get("/api/workspaces").json() == []


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
    assert url not in saved.text

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
