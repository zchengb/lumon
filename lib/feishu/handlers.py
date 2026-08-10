from __future__ import annotations

import json
from typing import Any

from feishu.client_registry import FeishuClientConfig
from agents.bridge import handle_agent_message
from agents.runtime.loop_intent import classify_loop_intent


def extract_text(event: dict[str, Any]) -> str:
    body = event.get("event") if isinstance(event.get("event"), dict) else event
    message = body.get("message") if isinstance(body, dict) else {}
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, dict):
        return str(content.get("text") or "").strip()
    if isinstance(content, str):
        raw = content.strip()
        if not raw:
            return ""
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        if isinstance(parsed, dict):
            return str(parsed.get("text") or "").strip()
        return raw
    return ""


def extract_message_meta(event: dict[str, Any]) -> dict[str, str]:
    body = event.get("event") if isinstance(event.get("event"), dict) else event
    message = body.get("message") if isinstance(body, dict) else {}
    sender = body.get("sender") if isinstance(body, dict) else {}
    header = event.get("header") if isinstance(event.get("header"), dict) else {}
    if not isinstance(message, dict):
        message = {}
    if not isinstance(sender, dict):
        sender = {}
    sender_id = sender.get("sender_id") if isinstance(sender.get("sender_id"), dict) else {}
    # thread_id is Feishu topic id (omt_*). Never fall back to root_id (om_* message id).
    meta = {
        "message_id": str(message.get("message_id") or "").strip(),
        "chat_id": str(message.get("chat_id") or "").strip(),
        "thread_id": str(message.get("thread_id") or "").strip(),
        "parent_id": str(message.get("parent_id") or "").strip(),
        "root_id": str(message.get("root_id") or "").strip(),
        "chat_type": str(message.get("chat_type") or "").strip(),
        "user_id": str(sender_id.get("open_id") or sender_id.get("user_id") or "").strip(),
        "union_id": str(sender_id.get("union_id") or "").strip(),
        "sender_type": str(sender.get("sender_type") or "").strip().lower(),
        "app_id": str(header.get("app_id") or "").strip(),
        "user_name": "",
    }
    mentions = message.get("mentions") if isinstance(message.get("mentions"), list) else []
    for item in mentions:
        if not isinstance(item, dict):
            continue
        mention_id = item.get("id") if isinstance(item.get("id"), dict) else {}
        open_id = str(mention_id.get("open_id") or "").strip()
        name = str(item.get("name") or "").strip()
        if open_id and name and open_id == meta["user_id"]:
            meta["user_name"] = name
            break
    return meta


def remember_message_identities(
    event: dict[str, Any],
    meta: dict[str, str],
    *,
    agent_id: str = "",
) -> None:
    try:
        from feishu.identity import is_feishu_open_chat_id, remember_chat_identity, remember_user_identity
        from risk.store import GlobalAgentStore
    except Exception:
        return
    store = GlobalAgentStore()
    try:
        user_id = str(meta.get("user_id") or "").strip()
        if user_id:
            remember_user_identity(
                store=store,
                open_id=user_id,
                display_name=str(meta.get("user_name") or "").strip(),
                union_id=str(meta.get("union_id") or "").strip(),
                agent_id=agent_id,
            )
        chat_id = str(meta.get("chat_id") or "").strip()
        chat_type = str(meta.get("chat_type") or "").strip().lower()
        if chat_id and is_feishu_open_chat_id(chat_id) and chat_type not in {"p2p", "private", "dm"}:
            remember_chat_identity(store=store, chat_id=chat_id, agent_id=agent_id)
        body = event.get("event") if isinstance(event.get("event"), dict) else event
        message = body.get("message") if isinstance(body, dict) else {}
        mentions = message.get("mentions") if isinstance(message, dict) and isinstance(message.get("mentions"), list) else []
        for item in mentions:
            if not isinstance(item, dict):
                continue
            mention_id = item.get("id") if isinstance(item.get("id"), dict) else {}
            open_id = str(mention_id.get("open_id") or "").strip()
            name = str(item.get("name") or "").strip()
            union_id = str(mention_id.get("union_id") or "").strip()
            if open_id:
                remember_user_identity(
                    store=store,
                    open_id=open_id,
                    display_name=name,
                    union_id=union_id,
                    agent_id=agent_id,
                )
    except Exception:
        pass
    finally:
        store.close()

def _mention_targets_agent(mentions: object, agent_id: str) -> bool:
    needle = str(agent_id or "").strip().lower()
    if not needle or not isinstance(mentions, list):
        return False
    for item in mentions:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip().lower()
        if name == needle or needle in name.split():
            return True
    return False


def _content_targets_agent(content: str, agent_id: str) -> bool:
    text = str(content or "")
    needle = str(agent_id or "").strip().lower()
    if not needle or "@" not in text:
        return False
    return f"@{needle}" in text.lower()


def should_handle(event: dict[str, Any], client: FeishuClientConfig) -> bool:
    body = event.get("event") if isinstance(event.get("event"), dict) else event
    message = body.get("message") if isinstance(body, dict) else {}
    if not isinstance(message, dict):
        return False
    sender = body.get("sender") if isinstance(body, dict) else {}
    sender_type = str(sender.get("sender_type") or "").strip().lower() if isinstance(sender, dict) else ""
    if sender_type in {"bot", "app"}:
        return False
    agent_id = str(client.agent_id or "").strip().lower()
    chat_type = str(message.get("chat_type") or "").strip().lower()
    mentions = message.get("mentions")
    if chat_type in {"p2p", "private"}:
        return True
    if isinstance(mentions, list) and len(mentions) > 0:
        return _mention_targets_agent(mentions, agent_id)
    content = extract_text(event)
    if _content_targets_agent(content, agent_id):
        return True
    parent_id = str(message.get("parent_id") or "").strip()
    root_id = str(message.get("root_id") or "").strip()
    thread_id = str(message.get("thread_id") or "").strip()
    if parent_id or root_id or thread_id:
        try:
            from agents.runtime.reply_anchor import is_agent_thread_context

            if is_agent_thread_context(
                agent_id=agent_id,
                parent_id=parent_id,
                root_id=root_id,
                thread_id=thread_id,
            ):
                return True
        except Exception:
            pass
    # Mark is the default Loop front door in a group: clear requirement or
    # technical-plan language should not require a ceremony-only @Mark.
    if agent_id == "mark":
        return classify_loop_intent(content).should_route_in_group
    return False


def handle_message_event(event: dict[str, Any], client: FeishuClientConfig) -> None:
    import logging

    log = logging.getLogger("lumen.feishu.channel")
    if not should_handle(event, client):
        body = event.get("event") if isinstance(event.get("event"), dict) else {}
        message = body.get("message") if isinstance(body, dict) else {}
        log.info(
            "ignore message chat_type=%s mentions=%s parent_id=%s thread_id=%s",
            (message.get("chat_type") if isinstance(message, dict) else None),
            (message.get("mentions") if isinstance(message, dict) else None),
            (message.get("parent_id") if isinstance(message, dict) else None),
            (message.get("thread_id") if isinstance(message, dict) else None),
        )
        return
    text = extract_text(event)
    meta = extract_message_meta(event)
    if not meta.get("app_id"):
        meta["app_id"] = client.app_id
    remember_message_identities(event, meta, agent_id=client.agent_id)
    log.info(
        "handle text=%r meta=%s",
        text[:120],
        {
            k: meta.get(k)
            for k in ("message_id", "chat_id", "chat_type", "parent_id", "root_id", "thread_id")
        },
    )
    handle_agent_message(
        agent_id=client.agent_id,
        text=text,
        meta=meta,
    )
