"""Feishu WebSocket channel adapter for Mark's normalized message interface."""

from __future__ import annotations

import importlib
import re
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, cast

from lumon.agents.mark.config import MarkAgentConfig
from lumon.agents.mark.model import InboundMessage, RecalledMessage
from lumon.errors import AgentRuntimeError

MessageHandler = Callable[[InboundMessage], Awaitable[None]]
RecallHandler = Callable[[RecalledMessage], Awaitable[None]]
_RECALL_EVENT_TYPE = "im.message.recalled_v1"

# Load the SDK before ``asyncio.run`` creates Mark's runtime loop. The SDK's
# WebSocket client captures a module-level loop during import and later runs
# its synchronous starter on that loop; importing it inside Mark's loop causes
# the SDK to call ``run_until_complete`` on an already-running loop.
try:
    _sdk_module: Any | None = importlib.import_module("lark_channel")
    _sdk_import_error: ImportError | None = None
except ImportError as exc:
    _sdk_module = None
    _sdk_import_error = exc


class MarkFeishuChannel:
    """Keep the third-party Channel SDK behind one concrete integration module."""

    def __init__(self, config: MarkAgentConfig) -> None:
        self.config = config
        self._channel: Any = None
        self._handler: MessageHandler | None = None
        self._recall_handler: RecallHandler | None = None

    async def connect(
        self,
        on_message: MessageHandler,
        on_recalled: RecallHandler | None = None,
    ) -> None:
        """Connect the SDK's WebSocket transport and keep it running."""

        module = _sdk_module
        if module is None:
            raise AgentRuntimeError(
                "The lark-channel-sdk dependency is unavailable; reinstall Lumon."
            ) from _sdk_import_error
        channel_type: Any = module.FeishuChannel

        self._handler = on_message
        self._recall_handler = on_recalled
        try:
            policy_type = module.PolicyConfig
            inbound_type = module.InboundConfig
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
            if on_recalled is not None:
                raw_event_subscriber = getattr(self._channel, "on_raw_event", None)
                if not callable(raw_event_subscriber):
                    raise AgentRuntimeError(
                        "The lark-channel-sdk dependency cannot receive recall events."
                    )
                raw_event_subscriber(_RECALL_EVENT_TYPE, self._on_sdk_recalled)
            await self._channel.connect()
        except Exception as exc:
            raise AgentRuntimeError("Feishu WebSocket connection failed.") from exc

    async def disconnect(self) -> None:
        """Close the SDK connection when the owning service stops."""

        channel = self._channel
        self._channel = None
        self._recall_handler = None
        if channel is None:
            return
        try:
            await channel.disconnect()
        except Exception as exc:
            raise AgentRuntimeError("Feishu WebSocket disconnect failed.") from exc

    async def add_typing(self, message_id: str) -> str | None:
        """Add the SDK's ``Typing`` reaction to an inbound message."""

        if self._channel is None:
            raise AgentRuntimeError("Feishu channel is not connected.")
        add_typing = getattr(self._channel, "add_typing_reaction", None)
        if not callable(add_typing):
            raise AgentRuntimeError("Feishu typing reactions are unavailable.")
        try:
            add_typing_call = cast(Callable[[str], Awaitable[object]], add_typing)
            reaction_id: object = await add_typing_call(message_id)
        except Exception as exc:
            raise AgentRuntimeError("Feishu typing reaction could not be added.") from exc
        return reaction_id if isinstance(reaction_id, str) and reaction_id else None

    async def remove_typing(self, message_id: str, reaction_id: str) -> None:
        """Remove a Typing reaction previously created by :meth:`add_typing`."""

        if self._channel is None:
            return
        remove_typing = getattr(self._channel, "remove_typing_reaction", None)
        if not callable(remove_typing):
            return
        try:
            remove_typing_call = cast(
                Callable[[str, str], Awaitable[object]],
                remove_typing,
            )
            await remove_typing_call(message_id, reaction_id)
        except Exception as exc:
            raise AgentRuntimeError("Feishu typing reaction could not be removed.") from exc

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

    async def _on_sdk_recalled(self, raw_message: Any) -> None:
        if self._recall_handler is None:
            return
        message = normalize_recalled_message(raw_message)
        if message is not None:
            await self._recall_handler(message)

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
    root_id = _optional_text(
        _value(
            raw,
            "root_id",
            _value(
                conversation,
                "root_id",
                _value(conversation, "root_message_id", None),
            ),
        )
    )
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


def normalize_recalled_message(raw: object) -> RecalledMessage | None:
    """Convert a raw Feishu recall event into the cancellation contract."""

    event = _value(raw, "event", raw)
    header = _value(raw, "header", {})
    message_id = _text(_value(event, "message_id", _value(raw, "message_id", ""))).strip()
    chat_id = _optional_text(_value(event, "chat_id", _value(raw, "chat_id", None)))
    event_id = _text(_value(header, "event_id", "")).strip()
    if not event_id:
        recall_time = _text(_value(event, "recall_time", "")).strip()
        event_id = f"recall:{message_id}:{recall_time}" if message_id else ""
    if not message_id or not event_id:
        return None
    return RecalledMessage(event_id=event_id, message_id=message_id, chat_id=chat_id)


def _value(value: object, name: str, default: object) -> object:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value).get(name, default)
    return getattr(value, name, default)


def _text(value: object) -> str:
    return value if isinstance(value, str) else str(value) if value is not None else ""


def _optional_text(value: object) -> str | None:
    text = _text(value).strip()
    return text or None
