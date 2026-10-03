"""Display-name lookups are bounded, cached, read-only and best-effort."""

from __future__ import annotations

import asyncio
import importlib
import json
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

from lumon.agents.agent.config import AgentConfig
from lumon.tools.feishu_directory import FeishuDirectory, FeishuDisplayNames


def test_directory_cache_is_bounded_deduplicated_and_scoped_to_app_credentials() -> None:
    calls: list[tuple[str, str, tuple[str, ...], tuple[str, ...]]] = []
    clock = [0.0]

    def lookup(
        app_id: str, app_secret: str, chats: tuple[str, ...], users: tuple[str, ...]
    ) -> FeishuDisplayNames:
        calls.append((app_id, app_secret, chats, users))
        return FeishuDisplayNames({"group": "MBPass"}, {"user": "Alice"})

    directory = FeishuDirectory(lookup=lookup, clock=lambda: clock[0])
    config = AgentConfig(feishu_app_id="app-one", feishu_app_secret="secret-one")
    assert directory.resolve(config, (), ()) == FeishuDisplayNames()
    assert not calls
    first = directory.resolve(config, ("group", "group", ""), ("user",))
    assert directory.resolve(config, ("group",), ("user",)) is first
    assert calls == [("app-one", "secret-one", ("group",), ("user",))]
    clock[0] = 301
    directory.resolve(config, ("group",), ("user",))
    directory.resolve(replace(config, feishu_app_secret="rotated"), ("group",), ("user",))
    directory.resolve(replace(config, feishu_app_id="app-two"), ("group",), ("user",))
    assert len(calls) == 4
    directory.resolve(config, tuple(str(index) for index in range(100)), ())
    assert len(calls[-1][2]) == 50


@pytest.mark.parametrize(
    "failure", ["none", "permission", "timeout", "deadline", "invalid", "auth"]
)
def test_sdk_lookup_returns_partial_names_without_leaking_upstream_errors(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, failure: str
) -> None:
    tokens: Any = importlib.import_module("lark_channel.core.token")
    http: Any = importlib.import_module("lark_channel.core.http")
    calls: list[tuple[str, object]] = []
    if failure == "deadline":
        timeout = asyncio.timeout

        def short_timeout(_delay: float | None) -> asyncio.Timeout:
            return timeout(0.01)

        monkeypatch.setattr(asyncio, "timeout", short_timeout)

    def token(_config: object) -> str:
        if failure == "auth":
            raise RuntimeError("token=PRIVATE_APP_CREDENTIAL")
        return "test-token"

    async def execute(_config: Any, request: Any, _option: Any) -> SimpleNamespace:
        assert _option.tenant_access_token == "test-token"
        payload: dict[str, object]
        if request.uri == "/open-apis/contact/v3/users/batch":
            calls.append(("users", request.user_ids))
            assert request.user_id_type == "open_id"
            payload = {
                "code": 0,
                "data": {
                    "items": [
                        {"open_id": "user-one", "name": " Alice\nLi "},
                        {"open_id": "not-requested", "name": "Private outsider"},
                    ]
                },
            }
        else:
            assert request.uri == "/open-apis/im/v1/chats/:chat_id"
            calls.append(("chat", request.chat_id))
            if request.chat_id == "group-b" and failure == "timeout":
                raise TimeoutError("token=PRIVATE_UPSTREAM_ERROR")
            if request.chat_id == "group-b" and failure == "deadline":
                await asyncio.sleep(60)
            if request.chat_id == "group-b" and failure == "permission":
                payload = {"code": 99991672, "msg": "token=PRIVATE_UPSTREAM_ERROR"}
            else:
                payload = {"code": 0, "data": {"name": "MBPass token=PRIVATE_NAME_VALUE"}}
        content = (
            b"invalid JSON token=PRIVATE_UPSTREAM_ERROR"
            if failure == "invalid"
            else json.dumps(payload).encode()
        )
        return SimpleNamespace(status_code=200, content=content, headers={})

    monkeypatch.setattr(tokens.TokenManager, "get_self_tenant_token", token)
    monkeypatch.setattr(http.Transport, "aexecute", execute)
    config = AgentConfig(feishu_app_id="test-app", feishu_app_secret="PRIVATE_APP_CREDENTIAL")
    names = FeishuDirectory().resolve(config, ("group-a", "group-b"), ("user-one",))
    if failure in {"auth", "invalid"}:
        assert names == FeishuDisplayNames()
    else:
        assert names.user_names == {"user-one": "Alice Li"}
        assert names.chat_names["group-a"] == "MBPass token=[REDACTED]"
        assert ("group-b" in names.chat_names) is (failure == "none")
    assert "PRIVATE" not in caplog.text
    assert "PRIVATE" not in repr(names)
    assert len([call for call in calls if call[0] == "users"]) <= 1
