"""Tests for Feishu message normalization and admission policy."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

import lumon.agents.mark.feishu as feishu_module
from lumon.agents.mark.config import MarkAgentConfig
from lumon.agents.mark.feishu import (
    MarkFeishuChannel,
    normalize_message,
    normalize_recalled_message,
)
from lumon.agents.mark.model import InboundMessage, RecalledMessage


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
    assert message.conversation_key == "oc_1"


def test_group_thread_is_the_session_boundary() -> None:
    first = normalize_message(_raw("group", "@Mark first"))
    second = normalize_message(
        {
            **_raw("group", "@Mark second"),
            "id": "om_2",
            "conversation": {
                "chat_id": "oc_1",
                "chat_type": "group",
                "thread_id": "thread-1",
            },
        }
    )
    other_thread = normalize_message(
        {
            **_raw("group", "@Mark other"),
            "id": "om_3",
            "conversation": {
                "chat_id": "oc_1",
                "chat_type": "group",
                "thread_id": "thread-2",
            },
        }
    )

    assert first is not None and second is not None and other_thread is not None
    assert first.conversation_key == second.conversation_key
    assert first.conversation_key != other_thread.conversation_key


def test_group_message_requires_mark_mention() -> None:
    ignored = normalize_message(_raw("group", "hello everyone"))
    admitted = normalize_message(_raw("group", "@Mark inspect the README"))

    assert ignored is not None and not ignored.admitted
    assert admitted is not None and admitted.admitted and admitted.mentioned_mark


def test_bot_messages_are_ignored() -> None:
    message = normalize_message(_raw("p2p", "hello", sender_type="bot"))

    assert message is not None and not message.admitted


def test_recalled_message_is_normalized_from_raw_event() -> None:
    message = normalize_recalled_message(
        {
            "header": {"event_id": "recall-event"},
            "event": {"message_id": "om-1", "chat_id": "oc-1"},
        }
    )

    assert message == RecalledMessage(
        event_id="recall-event",
        message_id="om-1",
        chat_id="oc-1",
    )


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
        self.raw_handlers: dict[str, Any] = {}
        _FakeSdkChannel.instance = self

    def on(self, event: str, handler: Any) -> None:
        self.handlers[event] = handler

    def on_raw_event(self, event: str, handler: Any) -> None:
        self.raw_handlers[event] = handler

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None


def test_channel_explicitly_configures_message_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        feishu_module,
        "_sdk_module",
        SimpleNamespace(
            FeishuChannel=_FakeSdkChannel,
            PolicyConfig=_FakePolicy,
            InboundConfig=_FakeInbound,
        ),
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


def test_channel_registers_recalled_event(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        feishu_module,
        "_sdk_module",
        SimpleNamespace(
            FeishuChannel=_FakeSdkChannel,
            PolicyConfig=_FakePolicy,
            InboundConfig=_FakeInbound,
        ),
    )
    channel = MarkFeishuChannel(
        MarkAgentConfig(feishu_app_id="cli_test", feishu_app_secret="secret-value")
    )
    recalled: list[RecalledMessage] = []

    async def run() -> None:
        async def handler(_message: InboundMessage) -> None:
            return None

        async def on_recalled(message: RecalledMessage) -> None:
            recalled.append(message)

        await channel.connect(handler, on_recalled)
        sdk_channel = _FakeSdkChannel.instance
        assert sdk_channel is not None
        await sdk_channel.raw_handlers["im.message.recalled_v1"](
            {
                "header": {"event_id": "recall-event"},
                "event": {"message_id": "om-1", "chat_id": "oc-1"},
            }
        )
        await channel.disconnect()

    asyncio.run(run())

    assert recalled == [RecalledMessage(event_id="recall-event", message_id="om-1", chat_id="oc-1")]
