from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

from agents.runner.workspace_mounts import ensure_runner_dirs
from agents.security.env import build_agent_env
from agents.security.flags import security_flags


def build_runner_env(
    *,
    agent_id: str,
    project: str = "",
    source: Optional[dict[str, str]] = None,
    config: Optional[dict[str, Any]] = None,
    world: Any | None = None,
    gate: Any | None = None,
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
        "LUMEN_AGENT_ID": str(agent_id or "unknown").strip().lower(),
        "LUMEN_PROJECT": str(project or ""),
        "LUMEN_AGENT_WORLD_CONTRACT": "agent-world/1",
        "LUMEN_CANONICAL_WORKSPACE": "host_only",
        "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
    }
    if world is not None:
        spec = getattr(world, "spec", None)
        if spec is not None:
            extra.update(
                {
                    "LUMEN_AGENT_WORLD_ID": str(getattr(spec, "world_id", "")),
                    "LUMEN_AGENT_WORLD_BACKEND": str(getattr(spec, "backend", "")),
                    "LUMEN_AGENT_WORLD_CONTRACT": str(getattr(spec, "contract", "agent-world/1")),
                }
            )
    if gate is not None:
        token = str(getattr(gate, "token", "") or "").strip()
        if token:
            extra.update(
                {
                    "LUMON_ENTRY_GATE_TOKEN": token,
                    "LUMON_GATE_USER_ID": str(getattr(gate, "user_id", "") or ""),
                    "LUMON_GATE_CHAT_ID": str(getattr(gate, "chat_id", "") or ""),
                    "LUMON_GATE_THREAD_ID": str(getattr(gate, "thread_id", "") or ""),
                    "LUMON_GATE_MESSAGE_ID": str(getattr(gate, "message_id", "") or ""),
                }
            )
            decision = getattr(gate, "decision", None)
            context = getattr(decision, "context", None)
            if decision is not None:
                extra.update(
                    {
                        "LUMON_GATE_ALLOWED": "1" if getattr(decision, "allowed", False) else "0",
                        "LUMON_GATE_TRUST_ZONE": str(getattr(decision, "trust_zone", "") or ""),
                        "LUMON_GATE_HOST_READ": "1" if getattr(decision, "host_read_allowed", False) else "0",
                        "LUMON_GATE_MUTATION": "1" if getattr(decision, "mutation_allowed", False) else "0",
                        "LUMON_GATE_CAPABILITIES": ",".join(sorted(getattr(decision, "effective_capabilities", frozenset()) or ())),
                    }
                )
            if context is not None:
                extra.update(
                    {
                        "LUMON_GATE_CHAT_TYPE": str(getattr(context, "chat_type", "") or ""),
                        "LUMON_GATE_IS_DM": "1" if getattr(context, "is_dm", False) else "0",
                    }
                )
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
    env.pop("LUMEN_CANONICAL_PATH", None)
    env.pop("LUMON_HOME", None)
    return env
