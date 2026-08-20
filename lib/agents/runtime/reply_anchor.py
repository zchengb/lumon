from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional


def agents_home() -> Path:
    override = os.environ.get("LUMEN_AGENTS_HOME", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".lumon" / "agents"


def outbound_path(agent_id: str = "dylan") -> Path:
    agent = str(agent_id or "dylan").strip().lower() or "dylan"
    return agents_home() / f"{agent}_outbound.jsonl"


def _append_row(row: dict[str, Any]) -> None:
    path = outbound_path(str(row.get("agent_id") or "dylan"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) > 600:
            path.write_text("\n".join(lines[-500:]) + "\n", encoding="utf-8")
    except Exception:
        pass


def remember_outbound(
    *,
    message_id: str,
    text: str,
    chat_id: str = "",
    agent_id: str = "dylan",
    reply_to: str = "",
    thread_id: str = "",
) -> None:
    mid = str(message_id or "").strip()
    body = str(text or "").strip()
    reply_to_id = str(reply_to or "").strip()
    tid = str(thread_id or "").strip()
    if mid and body:
        _append_row(
            {
                "message_id": mid,
                "chat_id": str(chat_id or ""),
                "agent_id": str(agent_id or "dylan"),
                "kind": "outbound",
                "text": body[:8000],
                "reply_to": reply_to_id,
                "thread_id": tid,
            }
        )
    if reply_to_id:
        _append_row(
            {
                "message_id": reply_to_id,
                "chat_id": str(chat_id or ""),
                "agent_id": str(agent_id or "dylan"),
                "kind": "thread_root",
                "text": body[:8000] if body else "(agent thread)",
                "thread_id": tid,
            }
        )
    if tid:
        _append_row(
            {
                "message_id": tid,
                "chat_id": str(chat_id or ""),
                "agent_id": str(agent_id or "dylan"),
                "kind": "thread",
                "text": body[:8000] if body else "(agent topic)",
            }
        )


def lookup_outbound(message_id: str, *, agent_id: str = "") -> str:
    mid = str(message_id or "").strip()
    if not mid:
        return ""
    wanted = str(agent_id or "").strip().lower()
    path = outbound_path(wanted or "dylan")
    if not path.is_file():
        return ""
    found = ""
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if mid not in line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if str(row.get("message_id") or "") != mid:
                continue
            if wanted and str(row.get("agent_id") or "").strip().lower() not in {"", wanted}:
                continue
            kind = str(row.get("kind") or "outbound")
            text = str(row.get("text") or "").strip()
            if kind == "outbound" and text:
                found = text
            elif kind in {"thread_root", "thread"} and not found and text:
                found = text
    except Exception:
        return found
    return found


def is_agent_thread_context(
    *,
    agent_id: str,
    parent_id: str = "",
    root_id: str = "",
    thread_id: str = "",
) -> bool:
    agent = str(agent_id or "").strip().lower()
    if not agent:
        return False
    for mid in (parent_id, root_id, thread_id):
        if lookup_outbound(str(mid or "").strip(), agent_id=agent):
            return True
    return False


def is_dylan_thread_context(*, parent_id: str = "", root_id: str = "", thread_id: str = "") -> bool:
    return is_agent_thread_context(
        agent_id="dylan",
        parent_id=parent_id,
        root_id=root_id,
        thread_id=thread_id,
    )


def _collect_feishu_post_text(value: Any, chunks: list[str]) -> None:
    if isinstance(value, list):
        for item in value:
            _collect_feishu_post_text(item, chunks)
        return
    if not isinstance(value, dict):
        text = str(value or "").strip()
        if text:
            chunks.append(text)
        return

    tag = str(value.get("tag") or "").strip().lower()
    if tag in {"text", "a", "at"}:
        text = str(value.get("text") or value.get("content") or value.get("user_name") or "").strip()
        if text:
            chunks.append(text)
        return
    if tag in {"img", "image"} or value.get("image_key"):
        chunks.append("[Image attachment]")
        return
    if tag in {"file", "media", "audio", "sticker"}:
        chunks.append("[File attachment]")
        return

    for key in ("title", "text", "content", "zh_cn", "en_us", "ja_jp", "body", "elements"):
        if key in value:
            _collect_feishu_post_text(value[key], chunks)


def extract_feishu_image_keys(msg_type: str, content: Any) -> list[str]:
    raw = content
    if isinstance(content, dict):
        raw = json.dumps(content, ensure_ascii=False)
    try:
        parsed = json.loads(str(raw or ""))
    except Exception:
        return []
    keys: list[str] = []

    def collect(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                collect(item)
            return
        if not isinstance(value, dict):
            return
        image_key = str(value.get("image_key") or "").strip()
        if image_key:
            keys.append(image_key)
        for item in value.values():
            collect(item)

    collect(parsed)
    return list(dict.fromkeys(keys))[:8]


def extract_feishu_attachment_refs(msg_type: str, content: Any) -> list[str]:
    """Return bounded file/media/image references for shared thread context."""

    raw = content
    if isinstance(content, dict):
        raw = json.dumps(content, ensure_ascii=False)
    try:
        parsed = json.loads(str(raw or ""))
    except Exception:
        return []
    refs: list[str] = []
    keys = {
        "image_key": "image",
        "file_key": "file",
        "media_key": "media",
        "audio_key": "audio",
        "video_key": "video",
    }

    def collect(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                collect(item)
            return
        if not isinstance(value, dict):
            return
        for key, kind in keys.items():
            ref = str(value.get(key) or "").strip()
            if ref:
                refs.append(f"{kind}:{ref}")
        for item in value.values():
            collect(item)

    collect(parsed)
    if str(msg_type or "").strip().lower() in {"file", "media", "audio", "video", "image"} and not refs:
        # Some webhook payloads omit the key but still carry an attachment
        # message type; retain a useful provider-neutral marker.
        refs.append(f"{str(msg_type).strip().lower()}:attached")
    return list(dict.fromkeys(refs))[:12]


def extract_content_text(msg_type: str, content: Any) -> str:
    raw = content
    if isinstance(content, dict):
        raw = json.dumps(content, ensure_ascii=False)
    text = str(raw or "").strip()
    if not text:
        return ""
    try:
        parsed = json.loads(text)
    except Exception:
        return text
    if not isinstance(parsed, dict):
        return text
    if msg_type == "text" or "text" in parsed:
        return str(parsed.get("text") or "").strip()
    chunks: list[str] = []
    if msg_type in {"post", "rich_text"} or any(key in parsed for key in ("zh_cn", "en_us", "ja_jp")):
        _collect_feishu_post_text(parsed, chunks)
        return "\n".join(dict.fromkeys(chunk.strip() for chunk in chunks if chunk.strip())).strip() or "[Message attachment]"
    body = parsed.get("body") if isinstance(parsed.get("body"), dict) else {}
    elements = body.get("elements") if isinstance(body.get("elements"), list) else parsed.get("elements")
    if isinstance(elements, list):
        for el in elements:
            if not isinstance(el, dict):
                continue
            if el.get("tag") == "markdown" and el.get("content"):
                chunks.append(str(el["content"]))
            text_obj = el.get("text") if isinstance(el.get("text"), dict) else {}
            if text_obj.get("content"):
                chunks.append(str(text_obj["content"]))
    header = parsed.get("header") if isinstance(parsed.get("header"), dict) else {}
    title = header.get("title") if isinstance(header.get("title"), dict) else {}
    if title.get("content"):
        chunks.insert(0, str(title["content"]))
    extracted = "\n".join(c.strip() for c in chunks if str(c).strip()).strip()
    if extracted:
        return extracted
    if msg_type in {"image", "file", "media", "audio", "sticker"}:
        return "[Image attachment]" if msg_type == "image" else "[File attachment]"
    return text[:2000]


def resolve_reply_anchor(
    *,
    messenger: Any,
    parent_id: str = "",
    root_id: str = "",
    agent_id: str = "dylan",
) -> str:
    agent = str(agent_id or "dylan").strip().lower()
    for mid in (str(parent_id or "").strip(), str(root_id or "").strip()):
        if not mid:
            continue
        cached = lookup_outbound(mid, agent_id=agent)
        if cached and cached not in {"(agent thread)", "(agent topic)"}:
            return cached
        try:
            msg = messenger.get_message(mid)
        except Exception:
            continue
        if not isinstance(msg, dict):
            continue
        data = msg.get("data") if isinstance(msg.get("data"), dict) else msg
        items = data.get("items") if isinstance(data.get("items"), list) else None
        row = items[0] if items else data
        if not isinstance(row, dict):
            continue
        msg_type = str(row.get("msg_type") or "")
        body = row.get("body") if isinstance(row.get("body"), dict) else {}
        content = body.get("content") if body else row.get("content")
        text = extract_content_text(msg_type, content)[:6000]
        if text:
            return text
    return ""


def format_anchored_user_message(*, user_message: str, parent_id: str = "", anchor_text: str = "") -> str:
    text = str(user_message or "").strip()
    anchor = str(anchor_text or "").strip()
    pid = str(parent_id or "").strip()
    if not anchor:
        return text
    return (
        "[FEISHU REPLY ANCHOR]\n"
        "The user is replying to the PRIOR message below (not necessarily the latest topic in this chat).\n"
        "If they say follow/accept/do your suggestion, apply the suggestion from THAT prior message only.\n"
        f"Prior message_id: {pid or '(unknown)'}\n"
        "Prior message content:\n"
        "-----\n"
        f"{anchor}\n"
        "-----\n\n"
        "[USER REPLY]\n"
        f"{text}\n"
    )
