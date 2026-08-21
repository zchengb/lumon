from __future__ import annotations

from typing import Any, Optional

from agents.role_policy import has_role_policy, is_action_forbidden_for_agent
from agents.security.actions import ALL_ACTIONS
from feishu.config import load_agents_config


def load_access_config(config: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    data = config if isinstance(config, dict) else load_agents_config()
    access = data.get("access") if isinstance(data.get("access"), dict) else {}
    legacy = access.get("legacy") if isinstance(access.get("legacy"), dict) else {}
    src = legacy if legacy else access
    return {
        "allowed_chat_ids": [str(x).strip() for x in (src.get("allowed_chat_ids") or access.get("allowed_chat_ids") or []) if str(x).strip()],
        "allowed_user_ids": [str(x).strip() for x in (src.get("allowed_user_ids") or access.get("allowed_user_ids") or []) if str(x).strip()],
        "mutation_allowed_user_ids": [
            str(x).strip()
            for x in (src.get("mutation_allowed_user_ids") or access.get("mutation_allowed_user_ids") or [])
            if str(x).strip()
        ],
        "admin_user_ids": [str(x).strip() for x in (src.get("admin_user_ids") or access.get("admin_user_ids") or []) if str(x).strip()],
        "default_policy": str(access.get("default_policy") or "legacy_allow"),
        "owners": [str(x).strip() for x in (access.get("owners") or []) if str(x).strip()],
        "admins": [str(x).strip() for x in (access.get("admins") or access.get("admin_user_ids") or []) if str(x).strip()],
        "authorization_mode": str(access.get("authorization_mode") or "gate_only").strip().casefold(),
    }


def agent_allowed_actions(agent_id: str) -> frozenset[str]:
    """Return registered actions minus the role document's explicit blacklist.

    The old implementation used four positive capability lists as business
    routing policy.  Keep this compatibility interface for access-zone and
    dashboard callers, but make the responsibility documents the source of
    role-specific decisions.
    """
    key = str(agent_id or "").strip().lower()
    if not has_role_policy(key):
        return frozenset()
    return frozenset(action for action in ALL_ACTIONS if not is_action_forbidden_for_agent(key, action))


def is_action_known(action: str) -> bool:
    return str(action or "").strip().lower() in ALL_ACTIONS


def is_action_allowed_for_agent(agent_id: str, action: str) -> bool:
    value = str(action or "").strip().lower()
    return is_action_known(value) and value in agent_allowed_actions(agent_id)
