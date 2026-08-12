from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


_ROOT = Path(__file__).resolve().parent / "responsibilities"
_ACTION_TOKEN = re.compile(r"`([a-z][a-z0-9_-]*(?:\.[a-z0-9_*-]+)+)`")


@dataclass(frozen=True)
class RolePolicy:
    agent_id: str
    path: Path
    text: str
    forbidden_actions: tuple[str, ...] = ()


def _section(text: str, heading: str) -> str:
    pattern = rf"(?ms)^##\s+{re.escape(heading)}\s*$\n?(.*?)(?=^##\s+|\Z)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def _forbidden_actions(text: str) -> tuple[str, ...]:
    values = _ACTION_TOKEN.findall(_section(text, "Forbidden actions"))
    return tuple(dict.fromkeys(values))


@lru_cache(maxsize=8)
def load_role_policy(agent_id: str) -> RolePolicy:
    key = str(agent_id or "").strip().lower()
    path = _ROOT / f"{key}.md"
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return RolePolicy(agent_id=key, path=path, text="")
    return RolePolicy(
        agent_id=key,
        path=path,
        text=text,
        forbidden_actions=_forbidden_actions(text),
    )


@lru_cache(maxsize=1)
def load_common_blacklist() -> str:
    try:
        return (_ROOT / "blacklist.md").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def responsibility_document(agent_id: str) -> str:
    return load_role_policy(agent_id).text


def forbidden_actions_for_agent(agent_id: str) -> frozenset[str]:
    return frozenset(load_role_policy(agent_id).forbidden_actions)


def is_action_forbidden_for_agent(agent_id: str, action: str) -> bool:
    value = str(action or "").strip().lower()
    return any(fnmatch.fnmatchcase(value, pattern) for pattern in forbidden_actions_for_agent(agent_id))


def has_role_policy(agent_id: str) -> bool:
    return bool(load_role_policy(agent_id).text)


def build_role_guidance(agent_id: str) -> str:
    policy = load_role_policy(agent_id)
    common = load_common_blacklist()
    document = policy.text or "No responsibility document is installed for this Agent. Route conservatively."
    return (
        "# Responsibility and Safety Guidance\n\n"
        "Before deciding how to handle the latest user request, use the responsibility document below as the "
        "first ownership check. Decide in your own reasoning whether the request belongs to you or another Agent. "
        "If it belongs to another Agent, route the original user input and attachments without inventing a new "
        "scope. If it is ambiguous, ask one focused question. This document is the business routing guide; the "
        "host still enforces identity, access, resource boundaries, and the common blacklist.\n\n"
        f"Document path: {policy.path}\n\n"
        f"{document}\n\n"
        "# Common hard blacklist\n\n"
        f"{common or 'The host denies secrets, host introspection, unsafe paths, and unauthorized mutations.'}\n"
    )
