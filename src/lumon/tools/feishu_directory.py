"""Best-effort display names using the Agent's existing Feishu app identity."""

from __future__ import annotations

import asyncio
import importlib
import logging
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from lumon.agents.agent.config import AgentConfig
from lumon.tools.safety import sanitize_output

_logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FeishuDisplayNames:
    chat_names: Mapping[str, str] = field(default_factory=dict[str, str])
    user_names: Mapping[str, str] = field(default_factory=dict[str, str])


DirectoryLookup = Callable[[str, str, tuple[str, ...], tuple[str, ...]], FeishuDisplayNames]


class FeishuDirectory:
    """Cache bounded page-level lookups for five minutes; never persist names."""

    def __init__(
        self,
        *,
        lookup: DirectoryLookup | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        lookup_names = lookup or _lookup_feishu_names

        def cached(
            app_id: str,
            app_secret: str,
            chats: tuple[str, ...],
            users: tuple[str, ...],
            window: int,
        ) -> FeishuDisplayNames:
            del window
            return lookup_names(app_id, app_secret, chats, users)

        self._cached = lru_cache(maxsize=128)(cached)
        self._clock = clock

    def resolve(
        self, config: AgentConfig, chat_ids: tuple[str, ...], user_ids: tuple[str, ...]
    ) -> FeishuDisplayNames:
        chats = tuple(sorted({identifier for identifier in chat_ids if identifier}))[:50]
        users = tuple(sorted({identifier for identifier in user_ids if identifier}))[:50]
        if not chats and not users:
            return FeishuDisplayNames()
        return self._cached(
            config.feishu_app_id,
            config.feishu_app_secret,
            chats,
            users,
            int(self._clock() // 300),
        )


def _lookup_feishu_names(
    app_id: str, app_secret: str, chats: tuple[str, ...], users: tuple[str, ...]
) -> FeishuDisplayNames:
    # The SDK owns authentication and token refresh. Obtain the token once,
    # before concurrent async calls: its automatic token acquisition is synchronous.
    try:
        sdk: Any = importlib.import_module("lark_channel.client")
        enums: Any = importlib.import_module("lark_channel.core.enum")
        tokens: Any = importlib.import_module("lark_channel.core.token")
        options: Any = importlib.import_module("lark_channel.core.model")
        client: Any = (
            sdk.Client.builder()
            .app_id(app_id)
            .app_secret(app_secret)
            .timeout(2)
            .enable_set_token(True)
            .log_level(enums.LogLevel.ERROR)
            .build()
        )
        token: Any = tokens.TokenManager.get_self_tenant_token(client.config)
        option: Any = options.RequestOption.builder().tenant_access_token(token).build()
        return asyncio.run(_fetch_names(client, option, chats, users))
    except Exception:
        # Final SDK boundary: error bodies can contain credentials or personal
        # data. Log only the operation, not the exception or upstream response.
        _logger.warning("Feishu display-name lookup unavailable; retaining IDs.")
        return FeishuDisplayNames()


async def _fetch_names(
    client: Any, option: Any, chats: tuple[str, ...], users: tuple[str, ...]
) -> FeishuDisplayNames:
    chat_model: Any = importlib.import_module("lark_channel.api.im.v1.model.get_chat_request")
    user_model: Any = importlib.import_module(
        "lark_channel.api.contact.v3.model.batch_user_request"
    )
    chat_names: dict[str, str] = {}
    user_names: dict[str, str] = {}
    semaphore = asyncio.Semaphore(4)

    async def read_chat(chat_id: str) -> None:
        try:
            async with semaphore:
                request: Any = chat_model.GetChatRequest.builder().chat_id(chat_id).build()
                response: Any = await client.im.v1.chat.aget(request, option)
            if response.code == 0:
                name = _display_name(getattr(response.data, "name", None))
                if name:
                    chat_names[chat_id] = name
            else:
                _logger.warning("Feishu chat-name lookup rejected; retaining ID.")
        except Exception:
            _logger.warning("Feishu chat-name lookup unavailable; retaining ID.")

    async def read_users() -> None:
        if not users:
            return
        try:
            request: Any = (
                user_model.BatchUserRequest.builder()
                .user_ids(list(users))
                .user_id_type("open_id")
                .build()
            )
            response: Any = await client.contact.v3.user.abatch(request, option)
            if response.code != 0:
                _logger.warning("Feishu user-name lookup rejected; retaining IDs.")
                return
            for user in getattr(response.data, "items", None) or ():
                user_id: object = getattr(user, "open_id", None)
                name = _display_name(getattr(user, "name", None))
                if isinstance(user_id, str) and user_id in users and name:
                    user_names[user_id] = name
        except Exception:
            _logger.warning("Feishu user-name lookup unavailable; retaining IDs.")

    try:
        async with asyncio.timeout(5):
            await asyncio.gather(read_users(), *(read_chat(chat_id) for chat_id in chats))
    except TimeoutError:
        _logger.warning("Feishu display-name lookup timed out; retaining unresolved IDs.")
    return FeishuDisplayNames(chat_names, user_names)


def _display_name(raw: object) -> str:
    if not isinstance(raw, str):
        return ""
    return " ".join(sanitize_output(raw).split())[:120]
