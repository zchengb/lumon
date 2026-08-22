from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agents.conversation.config import thread_native_config
from agents.conversation.relay import record_inbound_message
from agents.conversation.thread_store import ThreadTranscriptStore
from agents.project_resolver import load_chat_project_map, resolve_project
from feishu.client_registry import FeishuClientConfig
from feishu.agent_mentions import (
    agent_ids_from_structured_mentions,
    has_any_agent_or_user_mention,
    parse_agent_mentions,
)
from feishu.messenger import FeishuMessenger
from agents.bridge import handle_agent_message
from agents.runtime.loop_intent import classify_loop_intent
from agents.runtime.reply_anchor import extract_content_text, extract_feishu_attachment_refs, extract_feishu_image_keys


def _message_content(message: dict[str, Any]) -> Any:
    content = message.get("content")
    if content is not None:
        return content
    body = message.get("body")
    return body.get("content") if isinstance(body, dict) else None


def _message_from_response(response: object) -> dict[str, Any]:
    if not isinstance(response, dict):
        return {}
    data = response.get("data") if isinstance(response.get("data"), dict) else response
    items = data.get("items") if isinstance(data, dict) else None
    message = items[0] if isinstance(items, list) and items and isinstance(items[0], dict) else None
    if message is None and isinstance(data, dict) and isinstance(data.get("message"), dict):
        message = data["message"]
    if message is None and isinstance(data, dict) and data.get("msg_type"):
        message = data
    if not message:
        return {}
    normalized = dict(message)
    if normalized.get("content") is None:
        body = normalized.get("body")
        if isinstance(body, dict) and body.get("content") is not None:
            normalized["content"] = body["content"]
    return normalized


def _hydrate_missing_text(
    text: str,
    meta: dict[str, str],
    client: FeishuClientConfig,
) -> tuple[str, dict[str, str]]:
    """Recover content omitted by Feishu's image/post websocket payload."""
    current = str(text or "").strip()
    if current and current not in {"[Image attachment]", "[Message attachment]"}:
        return current, meta
    message_id = str(meta.get("message_id") or "").strip()
    if not message_id:
        return current, meta
    fetched = FeishuMessenger(client.agent_id).safe_get_message(message_id)
    message = _message_from_response(fetched)
    if not message:
        return current, meta
    fetched_event = {"event": {"message": message}}
    fetched_text = extract_text(fetched_event)
    fetched_meta = extract_message_meta(fetched_event)
    merged_meta = dict(meta)
    for key, value in fetched_meta.items():
        if value and not merged_meta.get(key):
            merged_meta[key] = value
    if fetched_text and fetched_text not in {"[Image attachment]", "[Message attachment]"}:
        return fetched_text, merged_meta
    return current, merged_meta


def extract_text(event: dict[str, Any]) -> str:
    body = event.get("event") if isinstance(event.get("event"), dict) else event
    message = body.get("message") if isinstance(body, dict) else {}
    if not isinstance(message, dict):
        return ""
    msg_type = str(message.get("msg_type") or "text")
    chunks: list[str] = []
    content_text = extract_content_text(msg_type, _message_content(message))
    if content_text:
        chunks.append(content_text)
    for field in ("text", "caption", "description"):
        value = message.get(field)
        if not isinstance(value, (str, dict)):
            continue
        field_text = extract_content_text("text", value)
        if field_text and field_text not in chunks:
            chunks.append(field_text)
    return "\n".join(chunks).strip()


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
    msg_type = str(message.get("msg_type") or "text")
    content = _message_content(message)
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
        "chat_name": str(
            message.get("chat_name")
            or message.get("chat_title")
            or message.get("conversation_name")
            or ""
        ).strip(),
    }
    image_keys = extract_feishu_image_keys(msg_type, content)
    if image_keys:
        meta["image_keys"] = json.dumps(image_keys, ensure_ascii=False)
    attachment_refs = extract_feishu_attachment_refs(msg_type, content)
    if attachment_refs:
        meta["attachment_refs"] = json.dumps(attachment_refs, ensure_ascii=False)
    mentions = message.get("mentions") if isinstance(message.get("mentions"), list) else []
    participant_ids: list[str] = []
    if meta["user_id"]:
        participant_ids.append(meta["user_id"])
    mentioned_agent_ids: list[str] = []
    for item in mentions:
        if not isinstance(item, dict):
            continue
        mention_id = item.get("id") if isinstance(item.get("id"), dict) else {}
        open_id = str(mention_id.get("open_id") or "").strip()
        name = str(item.get("name") or "").strip()
        if open_id and name and open_id == meta["user_id"]:
            meta["user_name"] = name
        if open_id and open_id not in participant_ids:
            participant_ids.append(open_id)
    if mentions:
        try:
            mentioned_agent_ids = list(dict.fromkeys(agent_ids_from_structured_mentions(mentions)))
        except Exception:
            mentioned_agent_ids = []
    if participant_ids:
        meta["participants"] = json.dumps(participant_ids, ensure_ascii=False)
    if mentioned_agent_ids:
        meta["available_agents"] = json.dumps(mentioned_agent_ids, ensure_ascii=False)
    return meta


def remember_message_identities(
    event: dict[str, Any],
    meta: dict[str, str],
    *,
    agent_id: str = "",
) -> None:
    try:
        from feishu.identity import (
            is_feishu_agent_display_name,
            is_feishu_open_chat_id,
            remember_chat_identity,
            remember_user_identity,
        )
        from risk.store import GlobalAgentStore
    except Exception:
        return
    store = GlobalAgentStore()
    try:
        user_id = str(meta.get("user_id") or "").strip()
        if user_id:
            store.record_feishu_user_context(
                user_id=user_id,
                chat_id=str(meta.get("chat_id") or ""),
                chat_type=str(meta.get("chat_type") or ""),
            )
            remember_user_identity(
                store=store,
                open_id=user_id,
                display_name=str(meta.get("user_name") or "").strip(),
                union_id=str(meta.get("union_id") or "").strip(),
                agent_id=agent_id,
            )
        chat_id = str(meta.get("chat_id") or "").strip()
        chat_type = str(meta.get("chat_type") or "").strip().lower()
        if chat_id:
            # Keep chat type independent from feishu_identity. The latter is
            # only a display-name cache and historically contained DMs, which
            # made them look like groups in the Dashboard.
            store.record_feishu_chat_context(chat_id=chat_id, chat_type=chat_type)
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
            mentioned_type = str(item.get("mentioned_type") or item.get("mention_type") or "").strip().lower()
            if mentioned_type in {"bot", "app"} or is_feishu_agent_display_name(name):
                continue
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


def _structured_content_mentions(message: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract Feishu rich-text @ targets when the top-level list is absent."""
    raw = _message_content(message)
    if isinstance(raw, (dict, list)):
        parsed: Any = raw
    else:
        try:
            parsed = json.loads(str(raw or ""))
        except (TypeError, json.JSONDecodeError):
            return []

    found: list[dict[str, Any]] = []

    def visit(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if not isinstance(value, dict):
            return
        tag = str(value.get("tag") or "").strip().lower()
        if tag in {"at", "mention"}:
            target_id = value.get("user_id") or value.get("open_id") or ""
            found.append(
                {
                    "name": str(
                        value.get("user_name")
                        or value.get("name")
                        or value.get("text")
                        or value.get("content")
                        or ""
                    ).strip(),
                    "id": {"open_id": str(target_id).strip()} if target_id else {},
                }
            )
            return
        for child in value.values():
            visit(child)

    visit(parsed)
    return found


def _message_mentions_agent(message: dict[str, Any], agent_id: str) -> tuple[bool, bool]:
    """Return (has_explicit_mention, targets_this_agent) for one message."""
    listed = message.get("mentions")
    mentions = [item for item in listed if isinstance(item, dict)] if isinstance(listed, list) else []
    mentions.extend(_structured_content_mentions(message))
    if mentions:
        return True, _mention_targets_agent(mentions, agent_id)
    return False, False


def _message_agent_mention_ids(message: dict[str, Any], content: str) -> tuple[bool, list[str]]:
    listed = message.get("mentions")
    mentions = [item for item in listed if isinstance(item, dict)] if isinstance(listed, list) else []
    mentions.extend(_structured_content_mentions(message))
    target_ids = agent_ids_from_structured_mentions(mentions)
    target_ids.extend(item.agent_id for item in parse_agent_mentions(content))
    explicit = bool(mentions) or has_any_agent_or_user_mention(content)
    return explicit, list(dict.fromkeys(target_ids))


def _message_common(message: dict[str, Any]) -> dict[str, Any]:
    chat_id = str(message.get("chat_id") or "").strip()
    try:
        mapped = resolve_project(chat_id=chat_id, mapping=load_chat_project_map())
    except Exception:
        mapped = None
    workspace = Path(str((mapped or {}).get("workspace") or "").strip()).expanduser()
    common_path = workspace / "config" / "common.json"
    if not workspace.is_dir() or not common_path.is_file():
        return {}
    try:
        data = json.loads(common_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _thread_native_enabled(message: dict[str, Any]) -> bool:
    return thread_native_config(_message_common(message), message).enabled


def _waiting_loop_owner(message: dict[str, Any]) -> str:
    chat_id = str(message.get("chat_id") or "").strip()
    if not chat_id or not any(str(message.get(key) or "").strip() for key in ("thread_id", "parent_id", "root_id")):
        return ""
    try:
        from agents.jobs.store import AgentJobStore

        store = AgentJobStore()
        try:
            job = store.find_waiting_loop(
                chat_id=chat_id,
                thread_id=str(message.get("thread_id") or ""),
                parent_id=str(message.get("parent_id") or ""),
                root_id=str(message.get("root_id") or ""),
            )
            return str(job.target_agent or "").strip().lower() if job is not None else ""
        finally:
            store.close()
    except Exception:
        return ""


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
    native = _thread_native_enabled(message)
    # An explicit target is always the latest user intent.  A pending Loop
    # must not hijack a message addressed to the host agent or another owner.
    has_explicit_mention, targets_agent = _message_mentions_agent(message, agent_id)
    if has_explicit_mention:
        return targets_agent
    content = extract_text(event)
    if native:
        text_explicit, target_ids = _message_agent_mention_ids(message, content)
        if text_explicit:
            return agent_id in target_ids
    elif _content_targets_agent(content, agent_id):
        return True

    if native:
        # A direct human reply to an Agent message belongs to that Agent only;
        # a waiting Job must never hijack it.
        parent_id = str(message.get("parent_id") or "").strip()
        root_id = str(message.get("root_id") or "").strip()
        thread_id = str(message.get("thread_id") or "").strip()
        try:
            transcript = ThreadTranscriptStore()
            try:
                owner = transcript.agent_for_message(parent_id) if parent_id else ""
                owner = owner or (transcript.agent_for_message(root_id) if root_id else "")
                if owner:
                    return owner == agent_id
                owners = transcript.agent_ids_in_thread(
                    chat_id=str(message.get("chat_id") or ""),
                    thread_id=thread_id,
                    root_id=root_id,
                    parent_id=parent_id,
                    message_id=str(message.get("message_id") or ""),
                )
                if len(owners) == 1 and (parent_id or root_id or thread_id):
                    return owners[0] == agent_id
            finally:
                transcript.close()
        except Exception:
            pass
        # Messages created before M0.6 may only exist in the per-Agent
        # reply-anchor cache.  Keep that cache as a routing compatibility
        # fallback while the shared transcript is populated organically.
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

    loop_owner = "" if native else _waiting_loop_owner(message)
    if loop_owner:
        # A Loop answer belongs to the child agent only when the user replied
        # to that child's concrete question message.  Waiting status alone is
        # not a conversation lock.
        return loop_owner == agent_id
    if chat_type in {"p2p", "private"}:
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
    body = event.get("event") if isinstance(event.get("event"), dict) else {}
    message = body.get("message") if isinstance(body, dict) else {}
    if not isinstance(message, dict):
        return
    sender = body.get("sender") if isinstance(body, dict) else {}
    sender_type = str(sender.get("sender_type") or "").strip().lower() if isinstance(sender, dict) else ""
    if sender_type in {"bot", "app"}:
        log.info("ignore bot/app message message_id=%s", message.get("message_id"))
        return

    # Every human message becomes shared context, even when this particular
    # Agent is not the owner.  The transcript store is idempotent because one
    # Feishu event is delivered to more than one Agent app.
    meta = extract_message_meta(event)
    text = extract_text(event)
    text, meta = _hydrate_missing_text(text, meta, client)
    if not meta.get("app_id"):
        meta["app_id"] = client.app_id
    if meta.get("message_id") and meta.get("chat_id"):
        try:
            message_mentions = message.get("mentions") if isinstance(message.get("mentions"), list) else []
            structured_mentions = _structured_content_mentions(message)
            mentioned_agents = agent_ids_from_structured_mentions([*message_mentions, *structured_mentions])
            mentioned_agents.extend(item.agent_id for item in parse_agent_mentions(text))
            image_keys = []
            try:
                raw_keys = json.loads(str(meta.get("image_keys") or "[]"))
                image_keys = [str(item) for item in raw_keys] if isinstance(raw_keys, list) else []
            except (TypeError, json.JSONDecodeError):
                pass
            try:
                raw_refs = json.loads(str(meta.get("attachment_refs") or "[]"))
                attachment_refs = [str(item) for item in raw_refs] if isinstance(raw_refs, list) else []
            except (TypeError, json.JSONDecodeError):
                attachment_refs = []
            record_inbound_message(
                message_id=meta["message_id"],
                meta=meta,
                text=text,
                mentions=mentioned_agents,
                attachment_refs=attachment_refs or image_keys,
            )
            log.info(
                "thread.message.inbound chat_id=%s thread_id=%s message_id=%s mentions=%s",
                meta.get("chat_id"),
                meta.get("thread_id") or meta.get("root_id") or meta.get("parent_id"),
                meta.get("message_id"),
                ",".join(dict.fromkeys(mentioned_agents)),
            )
        except Exception as exc:
            log.warning("thread inbound record failed message_id=%s err=%s", meta.get("message_id"), exc)

    if not should_handle(event, client):
        log.info(
            "ignore message chat_type=%s mentions=%s parent_id=%s thread_id=%s",
            (message.get("chat_type") if isinstance(message, dict) else None),
            (message.get("mentions") if isinstance(message, dict) else None),
            (message.get("parent_id") if isinstance(message, dict) else None),
            (message.get("thread_id") if isinstance(message, dict) else None),
        )
        return
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
