from __future__ import annotations

import os
from typing import Any, Optional

from feishu.config import load_agents_config


TRUSTED_DEDICATED_MACHINE = "trusted_dedicated_machine"
ISOLATED_AGENT_WORLD = "isolated_agent_world"


def canonical_agent_security_mode(value: str = "") -> str:
    """Normalize the two M0.8 execution worlds.

    Older installations used names such as ``dedicated_agent_machine`` and
    ``sandbox_exec``.  They remain accepted as configuration aliases, while
    the persisted/runtime vocabulary is deliberately small and explicit.
    """

    normalized = str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")
    trusted = {
        "trusted_dedicated_machine",
        "dedicated_agent_machine",
        "dedicated_machine",
        "dedicated",
        "host",
        "host_user",
        "trusted",
    }
    isolated = {
        "isolated_agent_world",
        "agent_world",
        "sandbox_exec",
        "sandboxed",
        "isolated",
        "disposable_agent_world",
    }
    if normalized in trusted:
        return TRUSTED_DEDICATED_MACHINE
    if normalized in isolated:
        return ISOLATED_AGENT_WORLD
    return normalized or TRUSTED_DEDICATED_MACHINE


def agent_security_mode(config: Optional[dict[str, Any]] = None) -> str:
    """Return the configured execution world.

    An explicit M0.7 isolation flag remains a compatibility signal for older
    test/workspace configurations.  New configurations default to the
    trusted dedicated-machine world described by M0.8.
    """

    data = config if isinstance(config, dict) else load_agents_config()
    security = data.get("agent_security") if isinstance(data.get("agent_security"), dict) else {}
    runtime = data.get("runtime") if isinstance(data.get("runtime"), dict) else {}
    raw = (
        os.environ.get("LUMON_AGENT_SECURITY_MODE", "").strip()
        or str(runtime.get("mode") or "").strip()
        or str(security.get("mode") or "").strip()
    )
    if raw:
        return canonical_agent_security_mode(raw)
    if "workspace_isolation_v2" in security:
        return ISOLATED_AGENT_WORLD if bool(security.get("workspace_isolation_v2")) else TRUSTED_DEDICATED_MACHINE
    return TRUSTED_DEDICATED_MACHINE


def trusted_dedicated_machine_enabled(config: Optional[dict[str, Any]] = None) -> bool:
    return agent_security_mode(config) == TRUSTED_DEDICATED_MACHINE


def isolated_agent_world_enabled(config: Optional[dict[str, Any]] = None) -> bool:
    return agent_security_mode(config) == ISOLATED_AGENT_WORLD


def workspace_isolation_v2_enabled(config: Optional[dict[str, Any]] = None) -> bool:
    data = config if isinstance(config, dict) else load_agents_config()
    security = data.get("agent_security") if isinstance(data.get("agent_security"), dict) else {}
    if "workspace_isolation_v2" in security:
        return bool(security.get("workspace_isolation_v2"))
    # M0.5 is fail-closed by default. Existing installations may explicitly
    # opt out during migration, but a missing flag must never silently run a
    # provider in the host workspace.
    return True


def security_flags(config: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    data = config if isinstance(config, dict) else load_agents_config()
    security = data.get("agent_security") if isinstance(data.get("agent_security"), dict) else {}
    harness = data.get("harness") if isinstance(data.get("harness"), dict) else {}
    mode = agent_security_mode(data)
    trusted = mode == TRUSTED_DEDICATED_MACHINE
    return {
        "workspace_isolation_v2": workspace_isolation_v2_enabled(data),
        "cursor_api_key_in_child_env": bool(security.get("allow_cursor_api_key_in_child_env", False)),
        "mode": mode,
        "harness_mode": str(harness.get("mode") or "unshackled").strip().casefold(),
        "agent_security_mode": mode,
        "delete_policy": str(
            security.get("delete_policy") or ("prompt_only" if trusted else "no_irreversible_delete")
        ).strip().casefold(),
        "network": str(harness.get("network") or security.get("network") or "allow").strip().casefold(),
        "secret_isolation": bool(security.get("secret_isolation", False if trusted else True)),
        "host_visibility": str(
            security.get("host_visibility") or ("full" if trusted else "denied")
        ).strip().casefold(),
        "raw": security,
    }
