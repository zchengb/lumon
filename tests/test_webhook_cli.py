"""Contract tests for sending Agent messages via the Workspace Webhook."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from lumon.cli.app import app
from lumon.errors import PreflightError
from lumon.skills.installer import SkillInstaller
from lumon.tools.feishu_webhook import WebhookSendResult
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.model import InitRequest
from lumon.workspace.registry import WorkspaceRegistry
from lumon.workspace.settings import (
    FeishuWebhookSettings,
    WorkspaceSettings,
    WorkspaceSettingsStore,
)


class _RecordingSender:
    def __init__(self, result: WebhookSendResult | None = None) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.result = result or WebhookSendResult(True, "Feishu Webhook message sent.")

    def send_message(self, url: str, payload: dict[str, object]) -> WebhookSendResult:
        self.calls.append((url, payload))
        return self.result


def _workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, enabled: bool = True) -> Path:
    state_root = tmp_path / "state"
    monkeypatch.setenv("LUMON_HOME", str(state_root))
    registry = WorkspaceRegistry(state_root)
    settings_store = WorkspaceSettingsStore(state_root)
    target = tmp_path / "workspace"
    WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"),
        registry=registry,
        settings_store=settings_store,
    ).initialize(InitRequest(target, name="Test Workspace"))
    registration = registry.list()[0]
    settings_store.save(
        WorkspaceSettings(
            registration.workspace_id,
            feishu_webhook=FeishuWebhookSettings(
                enabled=enabled,
                url="https://open.feishu.cn/open-apis/bot/v2/hook/test-token",
            ),
        )
    )
    return target


def test_webhook_cli_sends_only_through_the_saved_workspace_endpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path, monkeypatch)
    payload = {"msg_type": "interactive", "card": {"schema": "2.0"}}
    payload_path = workspace / "lumon" / "tmp" / "auto-guard.json"
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    sender = _RecordingSender()
    monkeypatch.setattr("lumon.cli.commands.webhook.FeishuWebhookSender", lambda: sender)

    result = CliRunner().invoke(
        app,
        [
            "webhook",
            "send",
            "--workspace",
            str(workspace),
            "--payload-file",
            str(payload_path.relative_to(workspace)),
        ],
    )

    output = result.stdout + result.stderr
    assert result.exit_code == 0, output
    assert "Webhook message sent" in output
    assert "test-token" not in output
    assert sender.calls == [("https://open.feishu.cn/open-apis/bot/v2/hook/test-token", payload)]


def test_webhook_cli_rejects_disabled_endpoint_and_outside_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path, monkeypatch, enabled=False)
    inside_payload = workspace / "lumon" / "tmp" / "inside.json"
    inside_payload.write_text('{"msg_type":"text"}', encoding="utf-8")
    outside_payload = tmp_path / "payload.json"
    outside_payload.write_text('{"msg_type":"text"}', encoding="utf-8")
    sender = _RecordingSender()
    monkeypatch.setattr("lumon.cli.commands.webhook.FeishuWebhookSender", lambda: sender)
    runner = CliRunner()

    disabled = runner.invoke(
        app,
        [
            "webhook",
            "send",
            "--workspace",
            str(workspace),
            "--payload-file",
            str(inside_payload.relative_to(workspace)),
        ],
    )
    assert disabled.exit_code != 0
    assert "disabled" in disabled.stdout + disabled.stderr
    assert "test-token" not in disabled.stdout + disabled.stderr

    settings_store = WorkspaceSettingsStore()
    registration = WorkspaceRegistry().list()[0]
    settings_store.save(
        WorkspaceSettings(
            registration.workspace_id,
            feishu_webhook=FeishuWebhookSettings(
                enabled=True,
                url="https://open.feishu.cn/open-apis/bot/v2/hook/test-token",
            ),
        )
    )
    escaped = runner.invoke(
        app,
        ["webhook", "send", "--workspace", str(workspace), "--payload-file", str(outside_payload)],
    )
    assert escaped.exit_code != 0
    assert "inside the Workspace" in escaped.stdout + escaped.stderr
    assert sender.calls == []


def test_webhook_cli_reports_send_failure_without_claiming_delivery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path, monkeypatch)
    payload_path = workspace / "lumon" / "tmp" / "report.json"
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text('{"msg_type":"text"}', encoding="utf-8")
    failure = PreflightError("Webhook rejected the message")

    class _FailingSender:
        def send_message(self, url: str, payload: dict[str, object]) -> WebhookSendResult:
            del url, payload
            raise failure

    monkeypatch.setattr("lumon.cli.commands.webhook.FeishuWebhookSender", _FailingSender)
    result = CliRunner().invoke(
        app,
        [
            "webhook",
            "send",
            "--workspace",
            str(workspace),
            "--payload-file",
            str(payload_path.relative_to(workspace)),
        ],
    )

    assert result.exit_code != 0
    assert "rejected" in result.stdout + result.stderr
    assert "message sent" not in result.stdout + result.stderr


def test_webhook_cli_rejects_invalid_payload_before_sending(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path, monkeypatch)
    payload_path = workspace / "lumon" / "tmp" / "invalid.json"
    payload_path.write_text("{}", encoding="utf-8")
    sender = _RecordingSender()
    monkeypatch.setattr("lumon.cli.commands.webhook.FeishuWebhookSender", lambda: sender)

    result = CliRunner().invoke(
        app,
        [
            "webhook",
            "send",
            "--workspace",
            str(workspace),
            "--payload-file",
            str(payload_path.relative_to(workspace)),
        ],
    )

    assert result.exit_code != 0
    assert "msg_type" in result.stdout + result.stderr
    assert sender.calls == []


def test_webhook_cli_refuses_an_unconfigured_webhook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path, monkeypatch)
    payload_path = workspace / "lumon" / "tmp" / "report.json"
    payload_path.write_text('{"msg_type":"text"}', encoding="utf-8")
    registration = WorkspaceRegistry().list()[0]
    WorkspaceSettingsStore().save(
        WorkspaceSettings(
            registration.workspace_id,
            feishu_webhook=FeishuWebhookSettings(enabled=True),
        )
    )
    sender = _RecordingSender()
    monkeypatch.setattr("lumon.cli.commands.webhook.FeishuWebhookSender", lambda: sender)

    result = CliRunner().invoke(
        app,
        [
            "webhook",
            "send",
            "--workspace",
            str(workspace),
            "--payload-file",
            str(payload_path.relative_to(workspace)),
        ],
    )

    assert result.exit_code != 0
    assert "not configured" in result.stdout + result.stderr
    assert sender.calls == []
