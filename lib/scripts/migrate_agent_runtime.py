#!/usr/bin/env python3
"""Migrate legacy conversational DeepSeek settings to OpenCode + DeepSeek."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


LEGACY = {"deepseek", "deepseek_api", "opencode_deepseek"}


def migrate_provider(provider: dict[str, Any]) -> bool:
    if str(provider.get("type") or provider.get("provider") or "").strip().casefold() not in LEGACY:
        return False
    if "type" in provider:
        provider["type"] = "opencode"
    else:
        provider["provider"] = "opencode"
    provider["base_url"] = ""
    provider["api_key_env"] = provider.get("api_key_env") or "DEEPSEEK_API_KEY"
    provider["output_format"] = "json"
    provider["resume_sessions"] = True
    return True


def migrate_execution(execution: dict[str, Any]) -> bool:
    changed = False
    provider = str(execution.get("provider") or "").strip().casefold()
    if provider in LEGACY:
        execution["provider"] = "opencode"
        execution["base_url"] = ""
        execution["api_key_env"] = execution.get("api_key_env") or "DEEPSEEK_API_KEY"
        changed = True
    patch_provider = str(execution.get("patch_provider") or "").strip().casefold()
    if patch_provider in LEGACY:
        execution["patch_provider"] = "opencode"
        execution["patch_base_url"] = ""
        execution["patch_api_key_env"] = execution.get("patch_api_key_env") or "DEEPSEEK_API_KEY"
        changed = True
    return changed


def migrate_config(config: dict[str, Any]) -> bool:
    changed = False

    def visit(value: Any) -> None:
        nonlocal changed
        if not isinstance(value, dict):
            if isinstance(value, list):
                for item in value:
                    visit(item)
            return
        if isinstance(value.get("execution"), dict):
            changed = migrate_execution(value["execution"]) or changed
        if isinstance(value.get("provider"), dict):
            changed = migrate_provider(value["provider"]) or changed
        if isinstance(value.get("model"), dict):
            changed = migrate_provider(value["model"]) or changed
        for item in value.values():
            visit(item)

    visit(config)
    return changed


def migrate_file(path: Path) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict) or not migrate_config(payload):
        return False
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def migrate_registered_workspaces(lumen_home: Path) -> int:
    registry_path = lumen_home / "projects.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    changed = 0
    projects = registry.get("projects") if isinstance(registry, dict) else []
    for project in projects if isinstance(projects, list) else []:
        if not isinstance(project, dict):
            continue
        workspace = Path(str(project.get("workspace") or "")).expanduser()
        if not workspace.is_dir():
            continue
        for name in ("config/common.json", "config/delivery.json"):
            if migrate_file(workspace / name):
                changed += 1
    return changed


if __name__ == "__main__":
    paths = [Path(value).expanduser() for value in sys.argv[1:] if not value.startswith("--")]
    migrate_workspaces = "--migrate-workspaces" in sys.argv[1:]
    lumen_home = Path(os.environ.get("LUMON_HOME") or os.environ.get("LUMEN_HOME") or Path.home() / ".lumon").expanduser()
    targets = paths or [lumen_home / "agents" / "config.json"]
    for target in targets:
        migrate_file(target)
    if migrate_workspaces:
        migrate_registered_workspaces(lumen_home)
    raise SystemExit(0)
