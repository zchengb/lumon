"""Tests for Feishu message normalization and admission policy."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

import lumon.agents.mark.feishu as feishu_module
from lumon.agents.mark.config import MarkAgentConfig
from lumon.agents.mark.feishu import MarkFeishuChannel, normalize_message
from lumon.agents.mark.model import InboundMessage


def _raw(chat_type: str, text: str, sender_type: str = "user") -> dict[str, object]:
    return {
        "id": "om_1",
        "chat_id": "oc_1",
        "chat_type": chat_type,
        "body_text": text,
        "sender_id": "ou_1",
        "sender_type": sender_type,
        "conversation": {"chat_id": "oc_1", "chat_type": chat_type, "thread_id": "thread-1"},
    }


def test_private_message_is_admitted() -> None:
    message = normalize_message(_raw("p2p", "hello"))

    assert message is not None
    assert message.admitted
    assert message.conversation_key == "oc_1:thread-1"


def test_group_message_requires_mark_mention() -> None:
    ignored = normalize_message(_raw("group", "hello everyone"))
    admitted = normalize_message(_raw("group", "@Mark inspect the README"))

    assert ignored is not None and not ignored.admitted
    assert admitted is not None and admitted.admitted and admitted.mentioned_mark


def test_bot_messages_are_ignored() -> None:
    message = normalize_message(_raw("p2p", "hello", sender_type="bot"))

    assert message is not None and not message.admitted


class _FakePolicy:
    def __init__(self, **kwargs: object) -> None:
        self.values = kwargs


class _FakeInbound:
    def __init__(self, **kwargs: object) -> None:
        self.values = kwargs


class _FakeSdkChannel:
    instance: _FakeSdkChannel | None = None

    def __init__(self, **kwargs: object) -> None:
        self.values = kwargs
        self.handlers: dict[str, Any] = {}
        _FakeSdkChannel.instance = self

    def on(self, event: str, handler: Any) -> None:
        self.handlers[event] = handler

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None


def test_channel_explicitly_configures_message_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_import(_name: str) -> SimpleNamespace:
        return SimpleNamespace(
            FeishuChannel=_FakeSdkChannel,
            PolicyConfig=_FakePolicy,
            InboundConfig=_FakeInbound,
        )

    monkeypatch.setattr(
        feishu_module.importlib,
        "import_module",
        fake_import,
    )
    channel = MarkFeishuChannel(
        MarkAgentConfig(feishu_app_id="cli_test", feishu_app_secret="secret-value")
    )

    async def run() -> None:
        async def handler(_message: InboundMessage) -> None:
            return None

        await channel.connect(handler)
        await channel.disconnect()

    asyncio.run(run())

    sdk_channel = _FakeSdkChannel.instance
    assert sdk_channel is not None
    policy = sdk_channel.values["policy"]
    inbound = sdk_channel.values["inbound"]
    assert isinstance(policy, _FakePolicy)
    assert isinstance(inbound, _FakeInbound)
    assert policy.values == {
        "dm_policy": "open",
        "group_policy": "open",
        "require_mention": True,
    }
    assert inbound.values == {"drop_self_sent": True}
