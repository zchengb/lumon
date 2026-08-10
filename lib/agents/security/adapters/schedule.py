from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any

from agents.security.actions import ActionRequest
from agents.security.errors import CapabilityDenied, ResourceDenied


def _project_workspace(slug: str) -> Path | None:
    from agents.project_resolver import resolve_project

    project = resolve_project(slug=slug)
    if not project or not project.get("workspace"):
        return None
    return Path(str(project["workspace"])).expanduser().resolve()


def schedule_show(project: str) -> dict[str, Any]:
    slug = str(project or "").strip()
    if not slug:
        raise ResourceDenied("project required")
    import scan_launchd

    label = scan_launchd.label_for(slug)
    path = scan_launchd.plist_path(label)
    if not path.is_file():
        return {"project": slug, "configured": False, "cron": "", "plist": str(path)}
    try:
        import plistlib

        payload = plistlib.loads(path.read_bytes())
    except Exception:
        payload = {}
    cron = ""
    interval = payload.get("StartCalendarInterval")
    if isinstance(interval, dict):
        cron = f"{interval.get('Minute', 0)} {interval.get('Hour', 0)} * * *"
    elif isinstance(interval, list) and interval:
        first = interval[0] if isinstance(interval[0], dict) else {}
        cron = f"{first.get('Minute', 0)} {first.get('Hour', 0)} * * 1-5"
    elif payload.get("StartInterval"):
        minutes = max(1, int(payload["StartInterval"]) // 60)
        cron = f"*/{minutes} * * * *"
    return {
        "project": slug,
        "configured": True,
        "cron": cron,
        "label": label,
        "plist": str(path),
        "program_arguments": payload.get("ProgramArguments") or [],
    }


def schedule_update(project: str, cron: str) -> dict[str, Any]:
    slug = str(project or "").strip()
    expression = str(cron or "").strip()
    if not slug:
        raise ResourceDenied("project required")
    if not expression:
        raise ResourceDenied("cron required")
    import scan_launchd

    parsed = scan_launchd.launchd_schedule_from_cron(expression)
    if parsed is None:
        raise ResourceDenied("unsupported cron expression")
    workspace = _project_workspace(slug)
    lumen_bin = shutil.which("lumen") or str(Path.home() / ".local/bin/lumen")
    lumen_home = os.environ.get("LUMEN_HOME", str(Path.home() / ".lumon"))
    log_file = str((workspace or Path.home()) / "lumen" / "logs" / "scan-schedule.log")
    if workspace:
        log_dir = workspace / "lumen" / "logs" if (workspace / "lumen").is_dir() else workspace / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = str(log_dir / "scan-schedule.log")
    args = argparse.Namespace(
        project=slug,
        cron=expression,
        lumen_bin=lumen_bin,
        lumen_home=lumen_home,
        path=os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
        log_file=log_file,
        dry_run=False,
    )
    code = scan_launchd.install(args)
    if code != 0:
        raise RuntimeError("schedule install failed")
    shown = schedule_show(slug)
    shown["updated"] = True
    shown["cron"] = expression
    return shown


def execute_schedule_action(request: ActionRequest) -> dict[str, Any]:
    project = str(request.project_slug or request.arguments.get("project") or "").strip()
    if request.action == "scan.schedule.read":
        return schedule_show(project)
    if request.action == "scan.schedule.update":
        cron = str(request.arguments.get("cron") or request.resource.get("cron") or "").strip()
        return schedule_update(project, cron)
    raise CapabilityDenied(f"unsupported schedule action: {request.action}")
