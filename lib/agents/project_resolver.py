from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from projects_registry import find_by_slug, load_registry, resolve_slug  # noqa: E402


def known_project_slugs() -> set[str]:
    registry = load_registry()
    return {
        str(project.get("slug") or "").strip().lower()
        for project in registry.get("projects", [])
        if str(project.get("slug") or "").strip()
    }


def resolve_project(slug: str = "", chat_id: str = "", mapping: Optional[dict] = None) -> Optional[dict]:
    value = str(slug or "").strip().lower()
    if value:
        try:
            return resolve_slug(value)
        except Exception:
            registry = load_registry()
            return find_by_slug(registry, value)

    chat = str(chat_id or "").strip()
    if chat:
        try:
            from risk.store import GlobalAgentStore

            gs = GlobalAgentStore()
            mapped_slug = gs.get_chat_project(chat)
            gs.close()
            if mapped_slug:
                try:
                    return resolve_slug(mapped_slug)
                except Exception:
                    pass
        except Exception:
            pass

    data = mapping if isinstance(mapping, dict) else {}
    chat_map = data.get("chat_project_map") if isinstance(data.get("chat_project_map"), dict) else {}
    mapped = str(chat_map.get(chat) or "").strip()
    if mapped:
        try:
            return resolve_slug(mapped)
        except Exception:
            return None

    default_slug = ""
    try:
        from projects_registry import load_config

        default_slug = str(load_config().get("default_project_slug") or "").strip()
    except Exception:
        default_slug = ""
    if default_slug:
        try:
            return resolve_slug(default_slug)
        except Exception:
            return None
    return None


def chat_project_map_path() -> Path:
    return Path.home() / ".lumon" / "agents" / "chat_projects.json"


def load_chat_project_map() -> dict:
    path = chat_project_map_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}
