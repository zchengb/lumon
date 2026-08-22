#!/usr/bin/env python3
"""Migrate legacy runtime settings to the M0.9 senior-coworker contract."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


LEGACY = {"deepseek", "deepseek_api", "opencode_deepseek"}
LEGACY_CONVERSATION_KEYS = ("conversation_runtime", "conversation_v4", "conversation_v3", "conversation_v2")


def migrate_runtime_sections(config: dict[str, Any]) -> bool:
    """Converge old runtime flags onto the M0.9 conversation boundaries."""

    changed = False
    conversation = config.get("conversation")
    if not isinstance(conversation, dict):
        conversation = {}
        for key in reversed(LEGACY_CONVERSATION_KEYS):
            value = config.get(key)
            if isinstance(value, dict):
                conversation.update(value)
        config["conversation"] = conversation
        changed = True
    defaults = {
        "version": "3.3",
        "default_language": "zh-Hant",
        "native_first": True,
        "legacy_compatibility": False,
        "visible_workstream": True,
        "native_tools": True,
        "native_questions": True,
    }
    for key, value in defaults.items():
        if key == "version" and str(conversation.get(key) or "") != value:
            conversation[key] = value
            changed = True
        elif key != "version" and key not in conversation:
            conversation[key] = value
            changed = True
    for key in LEGACY_CONVERSATION_KEYS:
        if key in config:
            config.pop(key, None)
            changed = True
    risk = config.get("risk_analyst")
    if isinstance(risk, dict) and "conversation_v2" in risk:
        risk.pop("conversation_v2", None)
        changed = True

    access = config.get("access")
    if not isinstance(access, dict):
        access = {}
        config["access"] = access
        changed = True
    if access.get("authorization_mode") != "gate_only":
        access["authorization_mode"] = "gate_only"
        changed = True
    if "default_policy" not in access:
        access["default_policy"] = "deny"
        changed = True

    security = config.get("agent_security")
    if not isinstance(security, dict):
        security = {}
        config["agent_security"] = security
        changed = True
    raw_mode = str(security.get("mode") or "").strip().casefold().replace("-", "_")
    explicit_isolation = raw_mode in {
        "isolated_agent_world",
        "agent_world",
        "sandbox_exec",
        "sandboxed",
        "isolated",
    }
    # M0.8 is the default for existing installations unless they explicitly
    # opted into the named isolated world.  This is the migration point that
    # makes the dedicated Mac behave like the Agent's actual working machine.
    security_defaults = (
        {
            "mode": "isolated_agent_world",
            "workspace_isolation_v2": True,
            "agent_world_backend": "auto",
            "boundary_backend": "sandbox_exec",
            "canonical_workspace_access": "host_only",
            "identity_mode": "service_account",
            "world_contract": "agent-world/1",
            "delete_policy": "no_irreversible_delete",
            "secret_isolation": True,
            "host_visibility": "agent_world_only",
            "network": "allow",
        }
        if explicit_isolation
        else {
            "mode": "trusted_dedicated_machine",
            "workspace_isolation_v2": False,
            "agent_world_backend": "host",
            "boundary_backend": "host_user",
            "canonical_workspace_access": "read_write",
            "identity_mode": "host_user",
            "world_contract": "agent-world/1-trusted",
            "delete_policy": "prompt_only",
            "secret_isolation": False,
            "host_visibility": "full",
            "network": "allow",
        }
    )
    for key, value in security_defaults.items():
        if (not explicit_isolation and security.get(key) != value) or (explicit_isolation and key not in security):
            security[key] = value
            changed = True
    return changed


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
    changed = migrate_runtime_sections(config)

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
