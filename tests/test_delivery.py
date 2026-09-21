"""Contract tests for the Auto Delivery lifecycle and Feishu cards."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from urllib.request import Request
from uuid import uuid4

import pytest

from lumon.delivery.model import DeliveryEvent, DeliveryResult, DeliveryRun, DeliveryState
from lumon.delivery.notifications import build_delivery_card
from lumon.delivery.service import DeliveryService
from lumon.errors import PreflightError
from lumon.tools.feishu_webhook import FeishuWebhookError, FeishuWebhookSender
from lumon.workspace.settings import (
    AutoDeliverySettings,
    FeishuWebhookSettings,
    WorkspaceSettings,
    WorkspaceSettingsStore,
)


class _Response:
    def __init__(self, status: int = 200, body: bytes = b'{"code": 0}') -> None:
        self.status = status
        self.body = body

    def read(self, amount: int = -1) -> bytes:
        del amount
        return self.body

    def close(self) -> None:
        pass


def _run() -> DeliveryRun:
    return DeliveryRun.claim(
        "run-1",
        "MBPAS-1495",
        "Generate test cases",
        now=datetime(2026, 9, 19, 8, 0, tzinfo=UTC),
        workspace_id=uuid4(),
        jira_url="https://inspire.atlassian.net/browse/MBPAS-1495",
    )


@pytest.mark.parametrize(
    ("event", "title", "template"),
    (
        (DeliveryEvent.STARTED, "Lumon · Delivery Started", "blue"),
        (DeliveryEvent.DEV_DONE, "Lumon · Delivery Completed", "green"),
        (DeliveryEvent.FAILED, "Lumon · Delivery Needs Attention", "red"),
        (DeliveryEvent.BLOCKED, "Lumon · Delivery Blocked", "orange"),
    ),
)
def test_delivery_card_contract(event: DeliveryEvent, title: str, template: str) -> None:
    run = _run()
    if event is DeliveryEvent.DEV_DONE:
        run = run.with_result(
            DeliveryResult(DeliveryState.COMPLETED, "publish", "published"),
            now=datetime(2026, 9, 19, 8, 1, 7, tzinfo=UTC),
            pull_request_url="https://example.test/pr/1",
        )
    elif event is DeliveryEvent.BLOCKED:
        run = run.with_result(
            DeliveryResult(DeliveryState.BLOCKED, "verification", "Missing test runner"),
            now=datetime(2026, 9, 19, 8, 1, tzinfo=UTC),
        )
    elif event is DeliveryEvent.FAILED:
        run = run.with_result(
            DeliveryResult(DeliveryState.FAILED, "agent", "Agent exited unexpectedly"),
            now=datetime(2026, 9, 19, 8, 1, tzinfo=UTC),
        )

    card = build_delivery_card(event, run)
    payload = cast(dict[str, object], card["card"])
    header = cast(dict[str, object], payload["header"])
    assert header == {
        "title": {"tag": "plain_text", "content": title},
        "subtitle": {"tag": "plain_text", "content": "MBPAS-1495 · Generate test cases"},
        "template": template,
    }
    assert payload["schema"] == "2.0"
    assert ("deploy" + "ment") not in json.dumps(card).lower()
    assert ("l" + "umen") not in json.dumps(card).lower()


def test_delivery_service_sends_once_and_records_receipt(tmp_path: Path) -> None:
    workspace_id = uuid4()
    settings = WorkspaceSettingsStore(tmp_path / "state")
    settings.save(
        WorkspaceSettings(
            workspace_id,
            FeishuWebhookSettings(
                enabled=True,
                url="https://open.feishu.cn/open-apis/bot/v2/hook/test-token",
            ),
            AutoDeliverySettings(enabled=True),
        )
    )
    requests: list[Request] = []

    def opener(request: Request, timeout: float) -> _Response:
        del timeout
        requests.append(request)
        return _Response()

    service = DeliveryService(
        settings_store=settings,
        webhook_sender=FeishuWebhookSender(opener=opener),
        now=lambda: datetime(2026, 9, 19, 8, 0, 1, tzinfo=UTC),
    )
    run = _run()
    first = service.start(tmp_path / "workspace", workspace_id, run)
    second = service.notify(tmp_path / "workspace", workspace_id, run, DeliveryEvent.STARTED)

    assert first.sent is True
    assert second.skipped is True
    assert len(requests) == 1
    body = cast(bytes, requests[0].data)
    assert body is not None
    assert "test-token" not in body.decode()
    assert (tmp_path / "workspace" / "lumon" / "runs" / "run-1" / "notifications.json").is_file()


def test_delivery_start_requires_workspace_permission(tmp_path: Path) -> None:
    workspace_id = uuid4()
    settings = WorkspaceSettingsStore(tmp_path / "state")
    settings.save(WorkspaceSettings(workspace_id))
    service = DeliveryService(settings_store=settings)

    with pytest.raises(PreflightError, match="Auto Delivery is disabled"):
        service.start(tmp_path / "workspace", workspace_id, _run())


def test_webhook_failure_does_not_change_delivery_state(tmp_path: Path) -> None:
    workspace_id = uuid4()
    settings = WorkspaceSettingsStore(tmp_path / "state")
    settings.save(
        WorkspaceSettings(
            workspace_id,
            FeishuWebhookSettings(
                enabled=True,
                url="https://open.feishu.cn/open-apis/bot/v2/hook/test-token",
            ),
            AutoDeliverySettings(enabled=True),
        )
    )

    def opener(request: Request, timeout: float) -> _Response:
        del request, timeout
        raise TimeoutError

    service = DeliveryService(
        settings_store=settings,
        webhook_sender=FeishuWebhookSender(opener=opener),
    )
    run = _run()
    service.run_store.save(tmp_path / "workspace", run)
    notification = service.notify(tmp_path / "workspace", workspace_id, run, DeliveryEvent.STARTED)

    assert notification.sent is False
    assert notification.skipped is False
    assert service.run_store.load(tmp_path / "workspace", run.run_id) == run
    assert not (tmp_path / "workspace" / "lumon" / "runs" / "run-1" / "notifications.json").exists()


def test_card_sender_rejects_http_errors_without_exposing_url() -> None:
    def opener(request: Request, timeout: float) -> _Response:
        del request, timeout
        return _Response(status=500)

    sender = FeishuWebhookSender(opener=opener)
    with pytest.raises(FeishuWebhookError, match="HTTP status 500"):
        sender.send_card(
            "https://open.feishu.cn/open-apis/bot/v2/hook/secret-token",
            {"msg_type": "interactive"},
        )


def test_delivery_text_is_redacted_before_card_and_receipt() -> None:
    run = DeliveryRun(
        run_id="run-redacted",
        story_key="MBPAS-1",
        story_title="Investigate password: super-secret",
        state=DeliveryState.BLOCKED,
        phase="verification",
        started_at=datetime(2026, 9, 19, 8, 0, tzinfo=UTC),
        reason="api_token: do-not-share",
    )

    card = json.dumps(build_delivery_card(DeliveryEvent.BLOCKED, run))

    assert "super-secret" not in card
    assert "do-not-share" not in card
    assert "[REDACTED]" in card


def test_delivery_card_drops_credential_bearing_links() -> None:
    run = DeliveryRun(
        run_id="run-link",
        story_key="MBPAS-1",
        story_title="Safe title",
        state=DeliveryState.COMPLETED,
        phase="publish",
        started_at=datetime(2026, 9, 19, 8, 0, tzinfo=UTC),
        jira_url="https://user:password@example.test/browse/MBPAS-1",
    )

    card = json.dumps(build_delivery_card(DeliveryEvent.DEV_DONE, run))

    assert "password" not in card
    assert "card_link" not in card
