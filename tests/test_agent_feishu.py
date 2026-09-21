"""Tests for Feishu message normalization and admission policy."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import lumon.agents.agent.feishu as feishu_module
from lumon.agents.agent.config import AgentConfig
from lumon.agents.agent.feishu import (
    AgentFeishuChannel,
    normalize_message,
    normalize_recalled_message,
)
from lumon.agents.agent.model import InboundImage, InboundMessage, RecalledMessage


def _raw(
    chat_type: str,
    text: str,
    sender_type: str = "user",
    mentioned_bot: bool = False,
    thread_id: str | None = "thread-1",
) -> dict[str, object]:
    return {
        "id": "om_1",
        "chat_id": "oc_1",
        "chat_type": chat_type,
        "body_text": text,
        "sender_id": "ou_1",
        "sender_type": sender_type,
        "mentioned_bot": mentioned_bot,
        "conversation": {"chat_id": "oc_1", "chat_type": chat_type, "thread_id": thread_id},
    }


def test_private_message_is_admitted() -> None:
    message = normalize_message(_raw("p2p", "hello"))

    assert message is not None
    assert message.admitted
    assert message.conversation_key == "oc_1"


def test_image_resources_are_normalized_without_persisting_opaque_keys() -> None:
    message = normalize_message(
        {
            **_raw("p2p", "Review this ![image](img-1)"),
            "resources": [
                {"type": "image", "file_key": "img-1", "file_name": "screen.png"},
                {"type": "image", "file_key": "img-1"},
                {"type": "file", "file_key": "file-1"},
            ],
        }
    )

    assert message is not None
    assert message.text == "Review this [image attachment]"
    assert message.images == (InboundImage(file_key="img-1", file_name="screen.png"),)


def test_reply_without_new_text_is_admitted_for_quoted_context() -> None:
    message = normalize_message(
        {
            **_raw("p2p", ""),
            "reply": {"message_id": "om-parent"},
        }
    )

    assert message is not None
    assert message.text == ""


def test_group_thread_is_the_session_boundary() -> None:
    first = normalize_message(_raw("group", "@Agent first", mentioned_bot=True))
    second = normalize_message(
        {
            **_raw("group", "@Agent second", mentioned_bot=True),
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
            **_raw("group", "@Agent other", mentioned_bot=True),
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


def test_group_message_requires_bot_mention() -> None:
    ignored = normalize_message(_raw("group", "hello everyone"))
    admitted = normalize_message(_raw("group", "inspect the README", mentioned_bot=True))

    assert ignored is not None and not ignored.admitted
    assert admitted is not None and admitted.admitted and admitted.mentioned_agent


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
        self.sent: list[tuple[str, object, object]] = []
        self.quoted_messages: dict[str, object] = {}
        self.downloaded_message_ids: list[str] = []
        self.downloaded_file_names: list[str | None] = []
        _FakeSdkChannel.instance = self

    def on(self, event: str, handler: Any) -> None:
        self.handlers[event] = handler

    def on_raw_event(self, event: str, handler: Any) -> None:
        self.raw_handlers[event] = handler

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    async def send(self, chat_id: str, body: object, options: object) -> SimpleNamespace:
        self.sent.append((chat_id, body, options))
        return SimpleNamespace(success=True)

    async def fetch_inbound_message(self, message_id: str) -> object | None:
        return self.quoted_messages.get(message_id)

    async def download_resource_to_file(
        self,
        file_key: str,
        *,
        resource_type: str,
        message_id: str,
        dest_dir: Path,
        file_name: str | None,
    ) -> Path:
        assert resource_type == "image"
        self.downloaded_message_ids.append(message_id)
        self.downloaded_file_names.append(file_name)
        path = dest_dir / f"{file_key}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"image")
        return path


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
    channel = AgentFeishuChannel(
        AgentConfig(feishu_app_id="cli_test", feishu_app_secret="secret-value")
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
    assert inbound.values == {
        "drop_self_sent": True,
        "expand_merge_forward": True,
        "fetch_interactive_card": True,
        "include_raw": True,
    }


def test_interactive_email_card_keeps_v1_body_and_quoted_history() -> None:
    message = normalize_message(
        {
            **_raw("p2p", "[interactive]"),
            "content": SimpleNamespace(
                card={
                    "config": {"wide_screen_mode": True},
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": "ALARM: database CPU exceeded threshold",
                            },
                        },
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": (
                                    "Sender: AWS Notifications <no-reply@example.com>\n"
                                    "Time: 2026-09-20 20:36\n\n"
                                    "> Previous alert context\n"
                                    "> Threshold was crossed again"
                                ),
                            },
                        },
                    ],
                },
            ),
        }
    )

    assert message is not None
    assert "ALARM: database CPU exceeded threshold" in message.text
    assert "Sender: AWS Notifications" in message.text
    assert "> Previous alert context" in message.text
    assert "[interactive]" not in message.text


def test_group_reply_creates_a_thread_for_a_top_level_message(
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
    channel = AgentFeishuChannel(
        AgentConfig(feishu_app_id="cli_test", feishu_app_secret="secret-value")
    )
    message = normalize_message(_raw("group", "@Agent hello", mentioned_bot=True, thread_id=None))
    assert message is not None
    assert message.thread_id is None

    async def run() -> None:
        async def handler(_message: InboundMessage) -> None:
            return None

        await channel.connect(handler)
        await channel.reply(message, "answer")
        await channel.disconnect()

    asyncio.run(run())

    sdk_channel = _FakeSdkChannel.instance
    assert sdk_channel is not None
    assert sdk_channel.sent == [
        (
            "oc_1",
            {"markdown": "answer"},
            {"reply_to": "om_1", "reply_in_thread": True},
        )
    ]


def test_private_reply_is_sent_without_a_reply_target(
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
    channel = AgentFeishuChannel(
        AgentConfig(feishu_app_id="cli_test", feishu_app_secret="secret-value")
    )
    message = normalize_message(_raw("p2p", "hello"))
    assert message is not None

    async def run() -> None:
        async def handler(_message: InboundMessage) -> None:
            return None

        await channel.connect(handler)
        await channel.reply(message, "answer")
        await channel.disconnect()

    asyncio.run(run())

    sdk_channel = _FakeSdkChannel.instance
    assert sdk_channel is not None
    assert sdk_channel.sent == [("oc_1", {"markdown": "answer"}, {})]


def test_channel_downloads_an_inbound_image_to_the_requested_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
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
    channel = AgentFeishuChannel(
        AgentConfig(feishu_app_id="cli_test", feishu_app_secret="secret-value")
    )
    message = InboundMessage(
        event_id="om-1",
        message_id="om-1",
        chat_id="oc-1",
        chat_type="p2p",
        text="[image attachment]",
        sender_id="ou-1",
        sender_type="user",
    )

    async def run() -> Path:
        async def handler(_message: InboundMessage) -> None:
            return None

        await channel.connect(handler)
        path = await channel.download_image(
            message,
            InboundImage(file_key="img-1", file_name="screen.png"),
            tmp_path,
        )
        await channel.disconnect()
        return path

    path = asyncio.run(run())

    assert path == (tmp_path / "img-1.png").resolve()
    assert path.read_bytes() == b"image"
    sdk_channel = _FakeSdkChannel.instance
    assert sdk_channel is not None
    assert sdk_channel.downloaded_message_ids == ["om-1"]
    assert sdk_channel.downloaded_file_names == ["screen.png"]


def test_channel_enriches_a_reply_with_quoted_text_and_images(
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
    channel = AgentFeishuChannel(
        AgentConfig(feishu_app_id="cli_test", feishu_app_secret="secret-value")
    )
    received: list[InboundMessage] = []
    raw = {
        **_raw("p2p", "请评估这个问题"),
        "reply": {"message_id": "om-parent"},
    }

    async def run() -> None:
        async def handler(message: InboundMessage) -> None:
            received.append(message)

        await channel.connect(handler)
        sdk_channel = _FakeSdkChannel.instance
        assert sdk_channel is not None
        sdk_channel.quoted_messages["om-parent"] = SimpleNamespace(
            body_text="原始问题 ![image](img-parent)",
            resources=[
                SimpleNamespace(
                    type="image",
                    file_key="img-parent",
                    file_name="original.png",
                )
            ],
        )
        message_handler = sdk_channel.handlers["message"]
        await message_handler(raw)
        await channel.disconnect()

    asyncio.run(run())

    assert received == [
        InboundMessage(
            event_id="om_1",
            message_id="om_1",
            chat_id="oc_1",
            chat_type="p2p",
            text=(
                "<feishu-quoted-message>\n"
                "原始问题 [image attachment]\n"
                "</feishu-quoted-message>\n\n"
                "请评估这个问题"
            ),
            sender_id="ou_1",
            sender_type="user",
            thread_id="thread-1",
            images=(
                InboundImage(
                    file_key="img-parent",
                    file_name="original.png",
                    source_message_id="om-parent",
                ),
            ),
        )
    ]


def test_channel_enriches_first_group_thread_reply_from_raw_parent(
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
    channel = AgentFeishuChannel(
        AgentConfig(feishu_app_id="cli_test", feishu_app_secret="secret-value")
    )
    received: list[InboundMessage] = []
    raw = {
        **_raw("group", "@Agent 評估一下這個問題", mentioned_bot=True, thread_id=None),
        "raw": {"parent_id": "om-parent", "root_id": "om-parent"},
    }

    async def run() -> None:
        async def handler(message: InboundMessage) -> None:
            received.append(message)

        await channel.connect(handler)
        sdk_channel = _FakeSdkChannel.instance
        assert sdk_channel is not None
        sdk_channel.quoted_messages["om-parent"] = SimpleNamespace(
            body_text="原始問題",
            resources=(),
        )
        await sdk_channel.handlers["message"](raw)
        await channel.disconnect()

    asyncio.run(run())

    assert received == [
        InboundMessage(
            event_id="om_1",
            message_id="om_1",
            chat_id="oc_1",
            chat_type="group",
            text=(
                "<feishu-quoted-message>\n"
                "原始問題\n"
                "</feishu-quoted-message>\n\n"
                "@Agent 評估一下這個問題"
            ),
            sender_id="ou_1",
            sender_type="user",
            mentioned_agent=True,
            thread_id=None,
            root_id="om-parent",
        )
    ]


def test_quoted_image_download_uses_parent_message_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
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
    channel = AgentFeishuChannel(
        AgentConfig(feishu_app_id="cli_test", feishu_app_secret="secret-value")
    )
    message = InboundMessage(
        event_id="om-1",
        message_id="om-1",
        chat_id="oc-1",
        chat_type="p2p",
        text="quoted",
        sender_id="ou-1",
        sender_type="user",
        images=(
            InboundImage(
                file_key="img-parent",
                file_name="original.png",
                source_message_id="om-parent",
            ),
        ),
    )

    async def run() -> Path:
        async def handler(_message: InboundMessage) -> None:
            return None

        await channel.connect(handler)
        path = await channel.download_image(message, message.images[0], tmp_path)
        await channel.disconnect()
        return path

    path = asyncio.run(run())

    assert path.read_bytes() == b"image"
    sdk_channel = _FakeSdkChannel.instance
    assert sdk_channel is not None
    assert sdk_channel.downloaded_message_ids == ["om-parent"]
    assert sdk_channel.downloaded_file_names == ["original.png"]


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
    channel = AgentFeishuChannel(
        AgentConfig(feishu_app_id="cli_test", feishu_app_secret="secret-value")
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
