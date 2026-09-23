"""Contract tests for per-Workspace Dashboard settings."""

from __future__ import annotations

import stat
from pathlib import Path
from uuid import uuid4

import pytest

from lumon.errors import InvalidInputError, PreflightError
from lumon.workspace.settings import (
    AutoDeliverySettings,
    FeishuWebhookSettings,
    FlowScheduleSettings,
    WorkspaceSettings,
    WorkspaceSettingsStore,
    masked_webhook_url,
)


def test_settings_round_trip_is_typed_and_owner_only(tmp_path: Path) -> None:
    store = WorkspaceSettingsStore(tmp_path / "lumon")
    workspace_id = uuid4()
    expected = WorkspaceSettings(
        workspace_id,
        FeishuWebhookSettings(
            enabled=True,
            url="https://open.feishu.cn/open-apis/bot/v2/hook/private-token",
        ),
        AutoDeliverySettings(enabled=True),
    )

    store.save(expected)

    assert store.load(workspace_id) == expected
    assert stat.S_IMODE(store.path_for(workspace_id).stat().st_mode) == 0o600
    assert (
        masked_webhook_url(expected.feishu_webhook.url)
        == "https://open.feishu.cn/open-apis/bot/v2/hook/priv*****oken"
    )


def test_auto_delivery_settings_round_trip_trigger_hooks_and_schedule(tmp_path: Path) -> None:
    store = WorkspaceSettingsStore(tmp_path / "lumon")
    workspace_id = uuid4()
    expected = WorkspaceSettings(
        workspace_id,
        auto_delivery=AutoDeliverySettings(
            enabled=True,
            trigger_hooks=("jira.delivery_ready", "mail.delivery_ready"),
            schedule_expression="0 9 * * 1-5",
        ),
    )

    store.save(expected)

    assert store.load(workspace_id).auto_delivery == expected.auto_delivery


def test_flow_schedules_round_trip_and_old_profiles_default_to_unscheduled(
    tmp_path: Path,
) -> None:
    store = WorkspaceSettingsStore(tmp_path / "lumon")
    workspace_id = uuid4()
    store.save(WorkspaceSettings(workspace_id))

    assert store.load(workspace_id).flow_schedules == ()

    expected = WorkspaceSettings(
        workspace_id,
        flow_schedules=(
            FlowScheduleSettings("auto-guard", enabled=True, schedule_expression="0 8 * * 1-5"),
        ),
    )
    store.save(expected)

    assert store.load(workspace_id) == expected


@pytest.mark.parametrize(
    "schedules",
    [
        (FlowScheduleSettings("../unsafe"),),
        (FlowScheduleSettings("auto-guard"), FlowScheduleSettings("auto-guard")),
        (FlowScheduleSettings("auto-guard", schedule_expression="not cron"),),
    ],
)
def test_flow_schedules_reject_invalid_ids_duplicates_and_cron(
    tmp_path: Path,
    schedules: tuple[FlowScheduleSettings, ...],
) -> None:
    store = WorkspaceSettingsStore(tmp_path / "lumon")

    with pytest.raises(InvalidInputError):
        store.save(WorkspaceSettings(uuid4(), flow_schedules=schedules))


def test_settings_reject_profile_for_another_workspace(tmp_path: Path) -> None:
    store = WorkspaceSettingsStore(tmp_path / "lumon")
    first = uuid4()
    second = uuid4()
    store.save(WorkspaceSettings(first))
    path = store.path_for(first)
    path.write_text(
        path.read_text(encoding="utf-8").replace(str(first), str(second)),
        encoding="utf-8",
    )

    with pytest.raises(PreflightError, match="does not match"):
        store.load(first)


def test_settings_reject_credentials_and_mask_webhook_token(tmp_path: Path) -> None:
    store = WorkspaceSettingsStore(tmp_path / "lumon")
    workspace_id = uuid4()
    with pytest.raises(InvalidInputError, match="must not contain credentials"):
        store.save(
            WorkspaceSettings(
                workspace_id,
                FeishuWebhookSettings(
                    url="https://user:secret@open.feishu.cn/open-apis/bot/v2/hook/token"
                ),
            )
        )

    assert (
        masked_webhook_url("https://user:secret@open.feishu.cn/open-apis/bot/v2/hook/token")
        == "https://open.feishu.cn/open-apis/bot/v2/hook/t***n"
    )
