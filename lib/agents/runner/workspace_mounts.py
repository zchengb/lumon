from __future__ import annotations

import os
from pathlib import Path


def lumen_home() -> Path:
    return Path(os.environ.get("LUMEN_HOME", Path.home() / ".lumon")).expanduser().resolve()


def runner_root(agent_id: str) -> Path:
    agent = str(agent_id or "agent").strip().lower() or "agent"
    return lumen_home() / "agent-runners" / agent


def ensure_runner_dirs(agent_id: str) -> dict[str, Path]:
    root = runner_root(agent_id)
    home = root / "home"
    tmp = root / "tmp"
    home.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)
    (home / ".cursor").mkdir(parents=True, exist_ok=True)
    # Keep provider and connected-tool credentials in the Agent service HOME.
    # These directories are intentionally created empty; provisioning never
    # copies the operator's personal auth files into them.
    for relative in (".config/twg", ".config/gh", ".codex", ".local/bin", ".local/share"):
        (home / relative).mkdir(parents=True, exist_ok=True)
    return {"root": root, "home": home, "tmp": tmp}
