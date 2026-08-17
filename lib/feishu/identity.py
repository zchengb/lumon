from __future__ import annotations

import re
from typing import Any

from feishu.client_registry import GATEWAY_AGENTS, load_client_config
from feishu.config import ensure_lumen_env_loaded
from feishu.messenger import FeishuMessenger

_OPEN_USER_RE = re.compile(r"^ou_[a-fA-F0-9]{16,}$")
_OPEN_CHAT_RE = re.compile(r"^oc_[a-fA-F0-9]{16,}$")


def is_feishu_open_user_id(value: str) -> bool:
    return bool(_OPEN_USER_RE.fullmatch(str(value or "").strip()))


def is_feishu_open_chat_id(value: str) -> bool:
    return bool(_OPEN_CHAT_RE.fullmatch(str(value or "").strip()))


def _messenger_for(agent_id: str) -> FeishuMessenger | None:
    if load_client_config(agent_id) is None:
        return None
    try:
        return FeishuMessenger(agent_id)
    except Exception:
        return None


def _resolve_one(
    *,
    store: Any,
    identity_id: str,
    identity_type: str,
    preferred_agent: str = "",
) -> str:
    cached = store.get_feishu_display_name(identity_id)
    if cached:
        return cached
    preferred = str(preferred_agent or "").strip().lower()
    agents = [preferred] if preferred else []
    agents.extend(a for a in GATEWAY_AGENTS if a not in agents)
    for agent_id in agents:
        messenger = _messenger_for(agent_id)
        if messenger is None:
            continue
        if identity_type == "user":
            profile = messenger.safe_get_user_profile(identity_id)
            name = str(profile.get("name") or "").strip()
            union_id = str(profile.get("union_id") or "").strip()
            if name or union_id:
                store.upsert_feishu_identity(
                    identity_id=identity_id,
                    identity_type=identity_type,
                    display_name=name or identity_id,
                    union_id=union_id,
                )
                return name
        else:
            name = messenger.safe_get_chat_name(identity_id)
            if name:
                store.upsert_feishu_identity(
                    identity_id=identity_id,
                    identity_type=identity_type,
                    display_name=name,
                )
                return name
    return ""


def remember_user_identity(
    *,
    store: Any,
    open_id: str,
    display_name: str = "",
    union_id: str = "",
    agent_id: str = "",
) -> None:
    uid = str(open_id or "").strip()
    if not uid or not is_feishu_open_user_id(uid):
        return
    name = str(display_name or "").strip() or store.get_feishu_display_name(uid)
    union = str(union_id or "").strip() or store.get_feishu_union_id(uid)
    if name or union:
        store.upsert_feishu_identity(
            identity_id=uid,
            identity_type="user",
            display_name=name,
            union_id=union,
        )
        if union:
            return
    agents = [str(agent_id or "").strip().lower()] if agent_id else []
    agents.extend(a for a in GATEWAY_AGENTS if a not in agents)
    for aid in agents:
        messenger = _messenger_for(aid)
        if messenger is None:
            continue
        profile = messenger.safe_get_user_profile(uid)
        resolved_name = str(profile.get("name") or "").strip()
        resolved_union = str(profile.get("union_id") or "").strip()
        if resolved_name or resolved_union:
            store.upsert_feishu_identity(
                identity_id=uid,
                identity_type="user",
                display_name=resolved_name or name or uid,
                union_id=resolved_union or union,
            )
            return
    if name:
        store.upsert_feishu_identity(
            identity_id=uid,
            identity_type="user",
            display_name=name,
            union_id=union,
        )
    else:
        # The sender open_id is still useful for Dashboard authorization even
        # when Feishu refuses cross-app profile lookup (41050/99992361).
        store.upsert_feishu_identity(
            identity_id=uid,
            identity_type="user",
            display_name="",
            union_id=union,
        )


def remember_chat_identity(
    *,
    store: Any,
    chat_id: str,
    display_name: str = "",
    agent_id: str = "",
) -> None:
    cid = str(chat_id or "").strip()
    if not cid or not is_feishu_open_chat_id(cid):
        return
    name = str(display_name or "").strip() or store.get_feishu_display_name(cid)
    if name:
        store.upsert_feishu_identity(identity_id=cid, identity_type="chat", display_name=name)
        return
    _resolve_one(store=store, identity_id=cid, identity_type="chat", preferred_agent=agent_id)


def link_access_identities(*, store: Any, identity_ids: list[str]) -> None:
    for identity_id in identity_ids:
        uid = str(identity_id or "").strip()
        if not uid or not is_feishu_open_user_id(uid):
            continue
        if store.get_feishu_union_id(uid) and store.get_feishu_display_name(uid):
            continue
        remember_user_identity(store=store, open_id=uid)

def enrich_feishu_identities(
    *,
    user_ids: list[str],
    chat_ids: list[str],
    store: Any,
    agent_id: str = "dylan",
    network: bool = True,
) -> dict[str, Any]:
    ensure_lumen_env_loaded()
    users: list[dict[str, Any]] = []
    chats: list[dict[str, str]] = []
    names: dict[str, str] = {}
    project_names: dict[str, str] = {}
    try:
        for row in store.conn.execute(
            "SELECT chat_id, project_slug FROM chat_project_map WHERE chat_id != ''"
        ).fetchall():
            chat = str(row["chat_id"] if hasattr(row, "keys") else row[0] or "").strip()
            slug = str(row["project_slug"] if hasattr(row, "keys") else row[1] or "").strip()
            if chat and slug:
                project_names[chat] = slug
    except Exception:
        project_names = {}

    for user_id in user_ids:
        uid = str(user_id or "").strip()
        if not uid or not is_feishu_open_user_id(uid):
            continue
        name = store.get_feishu_display_name(uid)
        known_union = store.get_feishu_union_id(uid)
        if not name and network and not known_union:
            name = _resolve_one(
                store=store,
                identity_id=uid,
                identity_type="user",
                preferred_agent=agent_id,
            )
        users.append(
            {
                "id": uid,
                "name": name or "",
                "union_id": store.get_feishu_union_id(uid) or known_union,
                "pending": not bool(name),
            }
        )
        if name:
            names[uid] = name

    for chat_id in chat_ids:
        cid = str(chat_id or "").strip()
        if not cid:
            continue
        if not is_feishu_open_chat_id(cid):
            alias = project_names.get(cid) or ""
            if alias:
                chats.append({"id": cid, "name": alias, "kind": "alias"})
                names[cid] = alias
            continue
        name = store.get_feishu_display_name(cid)
        if not name and network:
            name = _resolve_one(
                store=store,
                identity_id=cid,
                identity_type="chat",
                preferred_agent=agent_id,
            )
        chats.append({"id": cid, "name": name or "", "kind": "chat", "project": project_names.get(cid) or ""})
        if name:
            names[cid] = name

    return {"users": users, "chats": chats, "names": names}
