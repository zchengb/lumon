from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path
from typing import Any

from agents.security.actions import ActionRequest
from agents.security.errors import AuthorizationDenied, CapabilityDenied


def _disk_summary() -> dict[str, Any]:
    usage = shutil.disk_usage("/")
    total_gb = round(usage.total / (1024**3), 1)
    free_gb = round(usage.free / (1024**3), 1)
    used_percent = int(round((usage.used / usage.total) * 100)) if usage.total else 0
    return {"total_gb": total_gb, "free_gb": free_gb, "used_percent": used_percent}


def _runtime_summary() -> dict[str, Any]:
    version = "unknown"
    try:
        root = Path(__file__).resolve().parents[3]
        version_path = root / "VERSION"
        if version_path.is_file():
            version = version_path.read_text(encoding="utf-8").strip() or version
    except Exception:
        pass
    return {
        "os": platform.system(),
        "architecture": platform.machine(),
        "lumen_version": version,
        "cursor_cli": bool(shutil.which("agent") or shutil.which("cursor-agent")),
    }


def _applications_summary() -> dict[str, Any]:
    apps = Path("/Applications")
    names: list[str] = []
    if apps.is_dir():
        for path in sorted(apps.iterdir()):
            if path.suffix == ".app":
                names.append(path.stem)
    return {"application_count": len(names), "applications": names[:40]}


def _system_health() -> dict[str, Any]:
    from agents.definitions import list_definitions
    from agents.security.flags import workspace_isolation_v2_enabled

    return {
        "agents": [{"id": d.id, "role": d.role} for d in list_definitions()],
        "workspace_isolation_v2": workspace_isolation_v2_enabled(),
        "lumen_home": str(Path(os.environ.get("LUMEN_HOME", Path.home() / ".lumon")).expanduser()),
    }


def execute_host_read_action(request: ActionRequest) -> dict[str, Any]:
    action = str(request.action or "").strip()
    decision = request.arguments.get("_access_decision") if isinstance(request.arguments, dict) else None
    allowed_caps = set()
    if isinstance(decision, dict):
        caps = decision.get("effective_capabilities") or []
        if isinstance(caps, (list, tuple, set, frozenset)):
            allowed_caps = {str(c) for c in caps}
        if not decision.get("host_read_allowed") and not any(c.startswith("lumen.") for c in allowed_caps):
            raise AuthorizationDenied("host read denied for trust zone")
    if allowed_caps and action not in allowed_caps:
        raise AuthorizationDenied(f"{action} not in effective capabilities")

    if action == "host.disk.summary":
        return _disk_summary()
    if action == "host.runtime.summary":
        return _runtime_summary()
    if action == "host.applications.summary":
        return _applications_summary()
    if action == "lumen.system.health":
        return _system_health()
    if action == "lumen.agent.status":
        from agents.definitions import list_definitions

        return {"agents": [{"id": d.id, "role": d.role, "status": "registered"} for d in list_definitions()]}
    if action == "lumen.runner.status":
        from agents.runner.workspace_mounts import runner_root

        root = runner_root(request.agent_id or "dylan")
        return {"runner_root": str(root), "exists": root.is_dir()}
    raise CapabilityDenied(f"unsupported host read action: {action}")
