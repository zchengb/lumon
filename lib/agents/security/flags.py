from __future__ import annotations

from typing import Any, Optional

from feishu.config import load_agents_config


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
    return {
        "workspace_isolation_v2": workspace_isolation_v2_enabled(data),
        "cursor_api_key_in_child_env": bool(security.get("allow_cursor_api_key_in_child_env", False)),
        "mode": str(harness.get("mode") or security.get("mode") or "unshackled").strip().casefold(),
        "delete_policy": str(security.get("delete_policy") or "no_irreversible_delete").strip().casefold(),
        "network": str(harness.get("network") or security.get("network") or "allow").strip().casefold(),
        "secret_isolation": bool(security.get("secret_isolation", True)),
        "host_visibility": str(security.get("host_visibility") or "denied").strip().casefold(),
        "raw": security,
    }
