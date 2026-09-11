"""Contract tests for per-Workspace Dashboard settings."""

from __future__ import annotations

import stat
from pathlib import Path
from uuid import uuid4

import pytest

from lumon.errors import InvalidInputError, PreflightError
from lumon.workspace.settings import (
    FeishuWebhookSettings,
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
    )

    store.save(expected)

    assert store.load(workspace_id) == expected
    assert stat.S_IMODE(store.path_for(workspace_id).stat().st_mode) == 0o600
    assert (
        masked_webhook_url(expected.feishu_webhook.url)
        == "https://open.feishu.cn/open-apis/bot/v2/hook/priv*****oken"
    )


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
