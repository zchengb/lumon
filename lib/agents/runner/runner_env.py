from __future__ import annotations

from typing import Any, Optional

from agents.runner.workspace_mounts import ensure_runner_dirs
from agents.security.env import build_agent_env
from agents.security.flags import security_flags


def build_runner_env(
    *,
    agent_id: str,
    project: str = "",
    source: Optional[dict[str, str]] = None,
    config: Optional[dict[str, Any]] = None,
) -> dict[str, str]:
    flags = security_flags(config)
    dirs = ensure_runner_dirs(agent_id)
    extra = {
        "HOME": str(dirs["home"]),
        "TMPDIR": str(dirs["tmp"]),
        "TMP": str(dirs["tmp"]),
        "TEMP": str(dirs["tmp"]),
        "LUMEN_AGENT_RUNNER": "local_isolated",
        "LUMEN_AGENT_HOME": str(dirs["home"]),
        "LUMEN_AGENT_WORKSPACE": str(dirs["root"] / "workspaces"),
        "LUMEN_HOST_BOUNDARY": "closed",
        "LUMEN_AGENT_WORLD": "1",
        "LUMEN_ROOT_ESCALATION": "disabled",
        "LUMEN_SERVICE_IDENTITY": f"agent:{str(agent_id or 'unknown').strip().lower()}",
    }
    env = build_agent_env(agent_id=agent_id, project=project, extra=extra, source=source)
    env["HOME"] = str(dirs["home"])
    env["TMPDIR"] = str(dirs["tmp"])
    env["TMP"] = str(dirs["tmp"])
    env["TEMP"] = str(dirs["tmp"])
    # The child receives an isolated CLI environment, not the host's Lumon
    # credential/configuration store. Provider authentication is handled by a
    # dedicated provider channel (for example Codex account selection).
    env.pop("LUMEN_HOME", None)
    if not flags.get("cursor_api_key_in_child_env", True):
        env.pop("CURSOR_API_KEY", None)
        env.setdefault("AGENT_CLI_CREDENTIAL_STORE", "file")
    else:
        env["LUMEN_CURSOR_KEY_IN_CHILD"] = "1"
    return env
