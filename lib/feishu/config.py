from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional


def agents_home() -> Path:
    override = os.environ.get("LUMEN_AGENTS_HOME", "").strip()
    if override:
        path = Path(override).expanduser().resolve()
    else:
        path = Path.home() / ".lumon" / "agents"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_agents_config() -> dict[str, Any]:
    path = agents_home() / "config.json"
    if not path.is_file():
        return {"enabled": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"enabled": False}
    except Exception:
        return {"enabled": False}


def save_agents_config(config: dict[str, Any]) -> Path:
    path = agents_home() / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = config if isinstance(config, dict) else {"enabled": False}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def lumen_env_local_path() -> Path:
    home = Path(os.environ.get("LUMEN_HOME", Path.home() / ".lumon")).expanduser()
    return home / ".env.local"


def read_lumen_env_var(key: str) -> str:
    path = lumen_env_local_path()
    if not path.is_file():
        return ""
    needle = f"{key}="
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or not raw.startswith(needle):
            continue
        value = raw.split("=", 1)[1].strip().strip("'").strip('"')
        return value
    return ""


def upsert_lumen_env_var(key: str, value: str) -> Path:
    path = lumen_env_local_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    name = str(key or "").strip()
    if not name:
        raise ValueError("env key is required")
    next_value = str(value or "").strip()
    lines: list[str] = []
    if path.is_file():
        lines = path.read_text(encoding="utf-8").splitlines()
    prefix = f"{name}="
    replaced = False
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(prefix) and not stripped.startswith("#"):
            if next_value:
                out.append(f"{name}={next_value}")
            replaced = True
            continue
        out.append(line)
    if not replaced and next_value:
        if out and out[-1].strip():
            out.append("")
        out.append(f"{name}={next_value}")
    text = "\n".join(out).rstrip() + "\n"
    path.write_text(text, encoding="utf-8")
    if next_value:
        os.environ[name] = next_value
    elif name in os.environ:
        os.environ.pop(name, None)
    return path


def mask_credential(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if len(raw) <= 8:
        return "[set]"
    return f"{raw[:4]}…{raw[-4:]}"


def agents_enabled(config: Optional[dict[str, Any]] = None) -> bool:
    data = config if config is not None else load_agents_config()
    env = os.environ.get("LUMEN_AGENTS_ENABLED", "").strip().casefold()
    if env in {"1", "true", "yes"}:
        return True
    if env in {"0", "false", "no"}:
        return False
    return bool(data.get("enabled"))


def ensure_lumen_env_loaded() -> None:
    path = lumen_env_local_path()
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if not key or key in os.environ:
            continue
        os.environ[key] = value
