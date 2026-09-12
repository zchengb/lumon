"""Feishu WebSocket channel adapter for Mark's normalized message interface."""

from __future__ import annotations

import importlib
import re
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, cast

from lumon.agents.mark.config import MarkAgentConfig
from lumon.agents.mark.model import InboundMessage
from lumon.errors import AgentRuntimeError

MessageHandler = Callable[[InboundMessage], Awaitable[None]]


class MarkFeishuChannel:
    """Keep the third-party Channel SDK behind one concrete integration module."""

    def __init__(self, config: MarkAgentConfig) -> None:
        self.config = config
        self._channel: Any = None
        self._handler: MessageHandler | None = None

    async def connect(self, on_message: MessageHandler) -> None:
        """Connect the SDK's WebSocket transport and keep it running."""

        try:
            module = importlib.import_module("lark_channel")
            channel_type: Any = module.FeishuChannel
        except ImportError as exc:
            raise AgentRuntimeError(
                "The lark-channel-sdk dependency is unavailable; reinstall Lumon."
            ) from exc

        self._handler = on_message
        try:
            sdk = cast(Any, module)
            policy_type = sdk.PolicyConfig
            inbound_type = sdk.InboundConfig
            self._channel = channel_type(
                app_id=self.config.feishu_app_id,
                app_secret=self.config.feishu_app_secret,
                policy=policy_type(
                    dm_policy="open",
                    group_policy="open",
                    require_mention=True,
                ),
                inbound=inbound_type(drop_self_sent=True),
            )
            self._channel.on("message", self._on_sdk_message)
            self._channel.on("error", self._on_sdk_error)
            await self._channel.connect()
        except Exception as exc:
            raise AgentRuntimeError("Feishu WebSocket connection failed.") from exc

    async def disconnect(self) -> None:
        """Close the SDK connection when the owning service stops."""

        channel = self._channel
        self._channel = None
        if channel is None:
            return
        try:
            await channel.disconnect()
        except Exception as exc:
            raise AgentRuntimeError("Feishu WebSocket disconnect failed.") from exc

    async def reply(self, message: InboundMessage, text: str) -> None:
        """Reply in the source chat and thread without exposing SDK details."""

        if self._channel is None:
            raise AgentRuntimeError("Feishu channel is not connected.")
        options: dict[str, object] = {"reply_to": message.message_id}
        if message.thread_id or message.root_id:
            options["reply_in_thread"] = True
        try:
            result = await self._channel.send(
                message.chat_id,
                {"markdown": text},
                options,
            )
        except Exception as exc:
            raise AgentRuntimeError("Feishu message send failed.") from exc
        if getattr(result, "success", True) is False:
            raise AgentRuntimeError("Feishu message send failed.")

    async def _on_sdk_message(self, raw_message: Any) -> None:
        if self._handler is None:
            return
        message = normalize_message(raw_message)
        if message is not None:
            await self._handler(message)

    async def _on_sdk_error(self, _error: Any) -> None:
        """Consume SDK error callbacks without echoing potentially sensitive details."""

        return None


def normalize_message(raw: object) -> InboundMessage | None:
    """Convert an SDK message into the small message contract Mark consumes."""

    message_id = _text(_value(raw, "id", _value(raw, "message_id", "")))
    conversation = _value(raw, "conversation", {})
    sender = _value(raw, "sender", {})
    chat_id = _text(_value(raw, "chat_id", _value(conversation, "chat_id", "")))
    chat_type = _text(_value(raw, "chat_type", _value(conversation, "chat_type", "unknown")))
    text = _text(
        _value(
            raw,
            "body_text",
            _value(raw, "content_text", _value(raw, "safe_content_text", "")),
        )
    ).strip()
    sender_id = _text(_value(raw, "sender_id", _value(sender, "open_id", "")))
    sender_type = _text(_value(raw, "sender_type", _value(sender, "sender_type", "unknown")))
    if not sender_type:
        sender_type = "unknown"
    if not message_id or not chat_id or not text:
        return None

    mentioned_bot = bool(
        _value(raw, "mentioned_bot", False)
        or re.search(r"(?i)(?:^|\s)@mark(?:\s|$)", text) is not None
    )
    sender_is_bot = bool(_value(raw, "sender_is_bot", _value(sender, "is_bot", False)))
    if sender_is_bot and sender_type == "unknown":
        sender_type = "bot"
    thread_id = _optional_text(_value(conversation, "thread_id", _value(raw, "thread_id", None)))
    root_id = _optional_text(_value(raw, "root_id", None))
    return InboundMessage(
        event_id=message_id,
        message_id=message_id,
        chat_id=chat_id,
        chat_type=chat_type,
        text=text,
        sender_id=sender_id,
        sender_type=sender_type,
        mentioned_mark=mentioned_bot,
        thread_id=thread_id,
        root_id=root_id,
    )


def _value(value: object, name: str, default: object) -> object:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value).get(name, default)
    return getattr(value, name, default)


def _text(value: object) -> str:
    return value if isinstance(value, str) else str(value) if value is not None else ""


def _optional_text(value: object) -> str | None:
    text = _text(value).strip()
    return text or None
