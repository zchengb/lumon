from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from feishu.config import (
    agents_home,
    load_agents_config,
    lumen_env_local_path,
    mask_credential,
    read_lumen_env_var,
    save_agents_config,
    upsert_lumen_env_var,
)
from agents.registry import APP_ID_ENV
from feishu.client_registry import APP_SECRET_ENV

AGENT_META = {
    "dylan": {
        "display_name": "Dylan",
        "role": "scan",
        "workflow": "auto_scan",
        "title": "Engineering Risk Analyst",
    },
    "mark": {
        "display_name": "Mark",
        "role": "delivery",
        "workflow": "auto_delivery",
        "title": "Delivery Lead",
    },
    "irving": {
        "display_name": "Irving",
        "role": "patch",
        "workflow": "auto_patch",
        "title": "Remediation Engineer",
    },
    "milchick": {
        "display_name": "Milchick",
        "role": "orchestrator",
        "workflow": "operations",
        "title": "Engineering Operations Manager",
    },
}


def packaged_soul_path(agent_id: str) -> Path:
    agent = str(agent_id or "").strip().lower()
    return Path(__file__).resolve().parent / agent / "soul.md"


def soul_override_path(agent_id: str) -> Path:
    agent = str(agent_id or "").strip().lower()
    return agents_home() / "souls" / f"{agent}.md"


def load_agent_soul(agent_id: str) -> tuple[str, str]:
    agent = str(agent_id or "").strip().lower()
    override = soul_override_path(agent)
    if override.is_file():
        return override.read_text(encoding="utf-8"), "override"
    packaged = packaged_soul_path(agent)
    if packaged.is_file():
        return packaged.read_text(encoding="utf-8"), "packaged"
    return "", "missing"


def save_agent_soul(agent_id: str, text: str) -> Path:
    agent = str(agent_id or "").strip().lower()
    if agent not in AGENT_META:
        raise ValueError(f"Unknown agent: {agent}")
    path = soul_override_path(agent)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or "").rstrip() + "\n", encoding="utf-8")
    return path


def _ensure_dict(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        value = {}
        parent[key] = value
    return value


def _agent_section(config: dict[str, Any], agent_id: str) -> dict[str, Any]:
    return _ensure_dict(config, agent_id)


def _conversation_v4(agent_cfg: dict[str, Any]) -> dict[str, Any]:
    return _ensure_dict(agent_cfg, "conversation_v4")


def agent_settings_view(agent_id: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    agent = str(agent_id or "").strip().lower()
    meta = AGENT_META.get(agent)
    if meta is None:
        raise ValueError(f"Unknown agent: {agent}")
    data = config if isinstance(config, dict) else load_agents_config()
    agent_cfg = data.get(agent) if isinstance(data.get(agent), dict) else {}
    v4 = agent_cfg.get("conversation_v4") if isinstance(agent_cfg.get("conversation_v4"), dict) else {}
    provider = v4.get("provider") if isinstance(v4.get("provider"), dict) else {}
    runtime = v4.get("runtime") if isinstance(v4.get("runtime"), dict) else {}
    reaction = v4.get("reaction") if isinstance(v4.get("reaction"), dict) else {}
    soul_cfg = v4.get("soul") if isinstance(v4.get("soul"), dict) else {}
    profiles = data.get("profiles") if isinstance(data.get("profiles"), dict) else {}
    profile = profiles.get(agent) if isinstance(profiles.get(agent), dict) else {}
    soul_text, soul_source = load_agent_soul(agent)
    app_id_env = APP_ID_ENV.get(agent, "")
    app_secret_env = APP_SECRET_ENV.get(agent, "")
    app_id = read_lumen_env_var(app_id_env) if app_id_env else ""
    app_secret = read_lumen_env_var(app_secret_env) if app_secret_env else ""
    provider_type = str(provider.get("type") or "cursor_cli").strip().casefold()
    model_configured = True
    if provider_type in {"codex", "codex_cli", "codex-cli", "opencode", "opencode_deepseek", "deepseek", "deepseek_api", "openai", "openai_compatible"}:
        if provider_type in {"codex", "codex_cli", "codex-cli"}:
            from agents.runtime.codex_runtime import codex_account_status, find_codex_bin

            account = codex_account_status(provider.get("account_email") or "kuoyio0820@gmail.com")
            model_configured = bool(find_codex_bin()) and bool(account["matches"])
            model_key_env = "ChatGPT login"
        else:
            model_key_env = ""
        from agents.runtime.openai_compatible import default_api_key_env
        from agents.runtime.opencode_runtime import is_local_opencode_provider

        if provider_type not in {"codex", "codex_cli", "codex-cli"}:
            model_key_env = str(provider.get("api_key_env") or ("DEEPSEEK_API_KEY" if provider_type in {"opencode", "opencode_deepseek", "deepseek", "deepseek_api"} else default_api_key_env(provider_type))).strip()
            model_configured = is_local_opencode_provider(provider.get("model", ""), provider.get("base_url", "")) or bool(os.environ.get(model_key_env, "").strip() or read_lumen_env_var(model_key_env))
    security = {
        "filesystem": "workspace_read",
        "mutations": "brokered",
        "network": "allow",
        "sandbox": "unrestricted",
        "secrets": "isolated",
        "runner": "local_isolated",
        "host_visibility": "denied",
        "workspace_isolation_v2": True,
        "exposure_mode": "owner_private" if agent == "dylan" else ("admin_private" if agent == "milchick" else "restricted_team"),
        "dm_only": agent in {"dylan", "milchick"},
        "host_read": "selected" if agent == "dylan" else ("system_only" if agent == "milchick" else "deny"),
        "default_policy": "deny",
    }
    try:
        from agents.definitions import ensure_definitions_loaded, get_definition
        from agents.security.access_policy import load_agent_access_policy
        from agents.security.flags import workspace_isolation_v2_enabled

        ensure_definitions_loaded()
        isolation = workspace_isolation_v2_enabled()
        policy = load_agent_access_policy(agent, data)
        definition = get_definition(agent)
        if definition is not None:
            caps = definition.capabilities
            security = {
                "filesystem": caps.filesystem_mode,
                "mutations": "brokered",
                "network": caps.network_profile,
                "sandbox": "unrestricted",
                "secrets": caps.secret_profile,
                "actions": list(caps.actions),
                "runner": "local_isolated" if isolation else "host",
                "host_visibility": "denied" if isolation else "limited",
                "workspace_isolation_v2": isolation,
                "exposure_mode": policy.exposure_mode,
                "dm_only": policy.dm_only,
                "host_read": policy.host_read_mode,
                "default_policy": policy.default_policy,
                "allowed_user_ids": sorted(policy.allowed_user_ids),
                "allowed_chat_ids": sorted(policy.allowed_chat_ids),
                "mutation_allowed_user_ids": sorted(policy.mutation_allowed_user_ids),
                "policy_source": policy.source,
            }
        else:
            security["workspace_isolation_v2"] = isolation
            security["runner"] = "local_isolated" if isolation else "host"
            security["host_visibility"] = "denied" if isolation else "limited"
            security["exposure_mode"] = policy.exposure_mode
            security["dm_only"] = policy.dm_only
            security["host_read"] = policy.host_read_mode
            security["default_policy"] = policy.default_policy
            security["policy_source"] = policy.source
    except Exception:
        pass
    return {
        "id": agent,
        "display_name": meta["display_name"],
        "title": meta["title"],
        "role": str(profile.get("role") or meta["role"]),
        "workflow": str(profile.get("workflow") or meta["workflow"]),
        "conversation_enabled": bool(v4.get("enabled", False)),
        "mode": str(v4.get("mode") or "autonomous_workspace"),
        "provider": str(provider.get("type") or "cursor_cli"),
        "base_url": str(provider.get("base_url") or ""),
        "api_key_env": str(provider.get("api_key_env") or ""),
        "model_configured": model_configured,
        "model": str(provider.get("model") or "cursor-grok-4.5-medium"),
        "soft_timeout_seconds": int(runtime.get("soft_timeout_seconds") or 90),
        "hard_timeout_seconds": int(runtime.get("hard_timeout_seconds") or 3600),
        "reaction_enabled": bool(reaction.get("enabled", True)),
        "max_concurrent_jobs": int(agent_cfg.get("max_concurrent_jobs") or 3),
        "soul_version": str(soul_cfg.get("version") or ""),
        "soul": soul_text,
        "soul_source": soul_source,
        "soul_override_path": str(soul_override_path(agent)),
        "app_id": app_id,
        "app_id_masked": mask_credential(app_id),
        "app_secret_configured": bool(app_secret),
        "app_secret_masked": mask_credential(app_secret) if app_secret else "",
        "credentials_path": str(lumen_env_local_path()),
        "security": security,
    }


def test_case_settings_view(project_slug: str = "", config: dict[str, Any] | None = None) -> dict[str, Any]:
    from skills.test_case.config import load_test_case_config, normalize_test_case_language

    data = config if isinstance(config, dict) else load_agents_config()
    slug = str(project_slug or "").strip().lower()
    loaded = load_test_case_config(slug, config=data) if slug else {
        "language": "zh-Hant",
        "table_name": "Sheet1",
        "destination": "sheet",
        "base_app_token": "",
        "spreadsheet_token": "",
        "view_strategy": "story",
    }
    destination = str(loaded.get("destination") or "bitable")
    token = str(
        (loaded.get("spreadsheet_token") if destination == "sheet" else loaded.get("base_app_token")) or ""
    ).strip()
    raw = loaded.get("raw") if isinstance(loaded.get("raw"), dict) else {}
    if destination == "sheet":
        token_env = str(raw.get("spreadsheet_token_env") or raw.get("base_app_token_env") or "").strip()
        default_env = "FEISHU_MBPASS_QA_SHEET_TOKEN"
        table_name = str(loaded.get("sheet_name") or loaded.get("table_name") or "Sheet1")
    else:
        token_env = str(raw.get("base_app_token_env") or "").strip()
        default_env = "FEISHU_MBPASS_QA_APP_TOKEN"
        table_name = str(loaded.get("table_name") or "Test Cases")
    return {
        "project": slug,
        "destination": destination,
        "language": normalize_test_case_language(str(loaded.get("language") or "zh-Hant")),
        "table_name": table_name,
        "view_strategy": str(loaded.get("view_strategy") or "story"),
        "base_app_token_env": token_env or default_env,
        "base_app_token_configured": bool(token),
        "base_app_token_masked": mask_credential(token) if token else "",
        "spreadsheet_url": (
            f"https://inspiregroup.feishu.cn/sheets/{token}" if destination == "sheet" and token else ""
        ),
    }


def agents_settings_payload(*, network: bool = False, project: str = "") -> dict[str, Any]:
    config = load_agents_config()
    access = config.get("access") if isinstance(config.get("access"), dict) else {}
    recent = {"user_ids": [], "chat_ids": [], "direct_chat_ids": [], "users": [], "chats": [], "names": {}}
    pending_questions: list[dict[str, Any]] = []
    try:
        from risk.store import GlobalAgentStore
        from feishu.identity import discover_feishu_group_chats, enrich_feishu_identities

        store = GlobalAgentStore()
        try:
            access_user_ids = [
                str(x).strip()
                for x in (
                    list(access.get("allowed_user_ids") or [])
                    + list(access.get("mutation_allowed_user_ids") or [])
                    + list(access.get("admin_user_ids") or [])
                    + list(access.get("owners") or [])
                    + list(access.get("admins") or [])
                )
                if str(x).strip()
            ]
            access_chat_ids = [str(x).strip() for x in (access.get("allowed_chat_ids") or []) if str(x).strip()]
            private_user_ids = store.list_recent_feishu_dm_user_ids(limit=50)
            observed_group_chat_ids = store.list_recent_feishu_group_chat_ids(limit=100)
            known_dm_chat_ids = set(store.list_recent_feishu_dm_chat_ids(limit=100))
            discovered_chats = discover_feishu_group_chats(store=store, network=network)
            discovered_chat_ids = [str(item.get("id") or "").strip() for item in discovered_chats if item.get("id")]
            all_users = list(dict.fromkeys([*private_user_ids, *access_user_ids]))
            all_chats = [
                chat_id
                for chat_id in list(dict.fromkeys([*discovered_chat_ids, *observed_group_chat_ids, *access_chat_ids]))
                if chat_id not in known_dm_chat_ids
            ]
            enriched = enrich_feishu_identities(
                user_ids=all_users,
                chat_ids=all_chats,
                store=store,
                network=network,
            )
            private_user_set = set(private_user_ids) | set(access_user_ids)
            chat_details = {
                str(item.get("id") or ""): item
                for item in discovered_chats
                if str(item.get("id") or "").strip()
            }
            recent_users = [item for item in enriched.get("users", []) if item.get("id") in private_user_set]
            recent_chats = []
            direct_chat_ids = set(known_dm_chat_ids)
            for item in enriched.get("chats", []):
                chat_id = str(item.get("id") or "").strip()
                name = str(item.get("name") or "").strip()
                context_type = str(item.get("context_type") or "").strip().lower()
                chat_mode = str(item.get("chat_mode") or "").strip().lower()
                kind = str(item.get("kind") or "").strip().lower()
                is_direct = (
                    context_type == "dm"
                    or kind in {"dm", "private"}
                    or chat_mode in {"p2p", "private", "dm"}
                    or name.casefold() == "direct message"
                )
                if not chat_id:
                    continue
                if is_direct:
                    direct_chat_ids.add(chat_id)
                    continue
                details = chat_details.get(chat_id, {})
                recent_chats.append({**item, "agents": details.get("agents", [])})
            recent = {
                "user_ids": [str(item.get("id")) for item in recent_users if item.get("id")],
                "chat_ids": [str(item.get("id")) for item in recent_chats if item.get("id")],
                "users": recent_users,
                "private_user_ids": [str(item.get("id")) for item in recent_users if item.get("id")],
                "private_users": recent_users,
                "direct_chat_ids": sorted(direct_chat_ids),
                "group_chat_ids": [str(item.get("id")) for item in recent_chats if item.get("id")],
                "group_chats": recent_chats,
                "chats": recent_chats,
                "names": enriched.get("names") or {},
            }
        finally:
            store.close()
    except Exception:
        pass
    try:
        from risk.store import GlobalAgentStore

        store = GlobalAgentStore()
        try:
            rows = store.conn.execute(
                """
                SELECT agent_id, project_slug, pending_json, last_active_at
                FROM agent_session
                WHERE pending_json IS NOT NULL AND pending_json != ''
                ORDER BY last_active_at DESC
                LIMIT 50
                """
            ).fetchall()
            for row in rows:
                try:
                    pending = json.loads(row["pending_json"])
                except (TypeError, json.JSONDecodeError):
                    continue
                if not isinstance(pending, dict):
                    continue
                if project and str(row["project_slug"] or "").strip() not in {"", str(project).strip()}:
                    continue
                pending_questions.append(
                    {
                        "question_id": str(pending.get("question_id") or ""),
                        "agent_id": str(pending.get("agent_id") or row["agent_id"] or ""),
                        "action": str(pending.get("action") or ""),
                        "question": str(pending.get("question") or ""),
                        "missing": pending.get("missing") if isinstance(pending.get("missing"), list) else [],
                        "created_at": str(pending.get("created_at") or row["last_active_at"] or ""),
                        "expires_at": str(pending.get("expires_at") or ""),
                    }
                )
        finally:
            store.close()
    except Exception:
        pass
    return {
        "enabled": bool(config.get("enabled", False)),
        "home": str(agents_home()),
        "config_path": str(agents_home() / "config.json"),
        "access": {
            "default_policy": str(access.get("default_policy") or "deny"),
            "owners": [str(x) for x in (access.get("owners") or []) if str(x).strip()],
            "admins": [str(x) for x in (access.get("admins") or access.get("admin_user_ids") or []) if str(x).strip()],
            "allowed_chat_ids": [str(x) for x in (access.get("allowed_chat_ids") or []) if str(x).strip()],
            "allowed_user_ids": [str(x) for x in (access.get("allowed_user_ids") or []) if str(x).strip()],
            "mutation_allowed_user_ids": [
                str(x) for x in (access.get("mutation_allowed_user_ids") or []) if str(x).strip()
            ],
            "admin_user_ids": [str(x) for x in (access.get("admin_user_ids") or []) if str(x).strip()],
            "agents": access.get("agents") if isinstance(access.get("agents"), dict) else {},
            "legacy_warning": str(access.get("default_policy") or "deny") == "legacy_allow",
        },
        "recent_feishu": recent,
        "pending_questions": pending_questions,
        "agents": [agent_settings_view(agent_id, config) for agent_id in AGENT_META],
        "test_case": test_case_settings_view(project, config),
    }


def apply_agent_settings(payload: dict[str, Any]) -> dict[str, Any]:
    from skills.test_case.config import normalize_test_case_language

    config = load_agents_config()
    project_slug = str(payload.get("project") or "").strip().lower()
    if "enabled" in payload:
        config["enabled"] = bool(payload.get("enabled"))
    if "access" in payload and isinstance(payload.get("access"), dict):
        access_in = payload["access"]
        access = _ensure_dict(config, "access")
        if "default_policy" in access_in:
            default_policy = str(access_in.get("default_policy") or "deny").strip().lower()
            if default_policy not in {"deny", "legacy_allow"}:
                raise ValueError("default_policy must be deny or legacy_allow")
            access["default_policy"] = default_policy
        for key in ("allowed_chat_ids", "allowed_user_ids", "mutation_allowed_user_ids", "admin_user_ids"):
            if key in access_in:
                raw = access_in.get(key)
                if isinstance(raw, str):
                    values = [part.strip() for part in raw.replace("\n", ",").split(",") if part.strip()]
                elif isinstance(raw, list):
                    values = [str(item).strip() for item in raw if str(item).strip()]
                else:
                    values = []
                access[key] = values
    if "test_case" in payload and isinstance(payload.get("test_case"), dict) and project_slug:
        tc_in = payload["test_case"]
        projects = _ensure_dict(config, "projects")
        project_cfg = _ensure_dict(projects, project_slug)
        test_case = _ensure_dict(project_cfg, "test_case")
        if "language" in tc_in:
            test_case["language"] = normalize_test_case_language(str(tc_in.get("language") or "zh-Hant"))
        if "destination" in tc_in and str(tc_in.get("destination") or "").strip():
            dest = str(tc_in.get("destination") or "").strip().lower()
            test_case["destination"] = "sheet" if dest in {"sheet", "sheets", "spreadsheet"} else "bitable"
        if "table_name" in tc_in and str(tc_in.get("table_name") or "").strip():
            name = str(tc_in.get("table_name")).strip()
            test_case["table_name"] = name
            if str(test_case.get("destination") or "") == "sheet":
                test_case["sheet_name"] = name
        if "view_strategy" in tc_in and str(tc_in.get("view_strategy") or "").strip():
            test_case["view_strategy"] = str(tc_in.get("view_strategy")).strip()
        destination = str(test_case.get("destination") or "bitable")
        if destination == "sheet":
            if "base_app_token_env" in tc_in and str(tc_in.get("base_app_token_env") or "").strip():
                test_case["spreadsheet_token_env"] = str(tc_in.get("base_app_token_env")).strip()
            token = str(tc_in.get("base_app_token") or tc_in.get("spreadsheet_token") or tc_in.get("spreadsheet_url") or "").strip()
            if token:
                from feishu.sheets import parse_spreadsheet_token

                env_name = str(test_case.get("spreadsheet_token_env") or "FEISHU_MBPASS_QA_SHEET_TOKEN").strip()
                upsert_lumen_env_var(env_name, parse_spreadsheet_token(token))
                test_case["spreadsheet_token_env"] = env_name
                test_case.pop("base_app_token", None)
        else:
            if "base_app_token_env" in tc_in and str(tc_in.get("base_app_token_env") or "").strip():
                test_case["base_app_token_env"] = str(tc_in.get("base_app_token_env")).strip()
            token = str(tc_in.get("base_app_token") or "").strip()
            if token:
                env_name = str(test_case.get("base_app_token_env") or "FEISHU_MBPASS_QA_APP_TOKEN").strip()
                upsert_lumen_env_var(env_name, token)
                test_case["base_app_token_env"] = env_name
    profiles = _ensure_dict(config, "profiles")
    agents = payload.get("agents")
    if not isinstance(agents, list):
        raise ValueError("agents must be a list")
    for item in agents:
        if not isinstance(item, dict):
            continue
        agent_id = str(item.get("id") or "").strip().lower()
        if agent_id not in AGENT_META:
            raise ValueError(f"Unknown agent: {agent_id}")
        meta = AGENT_META[agent_id]
        agent_cfg = _agent_section(config, agent_id)
        if "max_concurrent_jobs" in item:
            jobs = int(item.get("max_concurrent_jobs") or 3)
            if jobs < 1 or jobs > 32:
                raise ValueError("max_concurrent_jobs must be between 1 and 32")
            agent_cfg["max_concurrent_jobs"] = jobs
        v4 = _conversation_v4(agent_cfg)
        if "conversation_enabled" in item:
            v4["enabled"] = bool(item.get("conversation_enabled"))
        if not v4.get("mode"):
            v4["mode"] = "autonomous_workspace"
        if "mode" in item and str(item.get("mode") or "").strip():
            v4["mode"] = str(item.get("mode")).strip()
        provider = _ensure_dict(v4, "provider")
        provider.setdefault("type", "opencode")
        provider.setdefault("output_format", "stream-json")
        provider.setdefault("resume_sessions", True)
        if "provider" in item:
            provider_name = str(item.get("provider") or "").strip().casefold()
            if provider_name not in {"codex", "codex_cli", "codex-cli", "cursor", "cursor_cli", "opencode", "opencode_deepseek", "deepseek", "deepseek_api", "openai", "openai_compatible"}:
                raise ValueError(f"Unsupported model provider: {provider_name}")
            provider["type"] = provider_name
            if provider_name in {"opencode", "opencode_deepseek", "deepseek", "deepseek_api"}:
                provider["type"] = "opencode"
                provider["output_format"] = "json"
                provider["resume_sessions"] = True
            elif provider_name in {"openai", "openai_compatible"}:
                provider["output_format"] = "text"
                provider["resume_sessions"] = False
        if "base_url" in item:
            provider["base_url"] = str(item.get("base_url") or "").strip()
        if "api_key_env" in item:
            provider["api_key_env"] = str(item.get("api_key_env") or "").strip()
        if "model" in item:
            model = str(item.get("model") or "").strip()
            if not model:
                raise ValueError(f"{agent_id} model is required")
            provider["model"] = model
        runtime = _ensure_dict(v4, "runtime")
        if "soft_timeout_seconds" in item:
            soft = int(item.get("soft_timeout_seconds") or 90)
            if soft < 10 or soft > 3600:
                raise ValueError("soft_timeout_seconds must be between 10 and 3600")
            runtime["soft_timeout_seconds"] = soft
        if "hard_timeout_seconds" in item:
            hard = int(item.get("hard_timeout_seconds") or 3600)
            if hard < 30 or hard > 7200:
                raise ValueError("hard_timeout_seconds must be between 30 and 7200")
            runtime["hard_timeout_seconds"] = hard
        soft = int(runtime.get("soft_timeout_seconds") or 90)
        hard = int(runtime.get("hard_timeout_seconds") or 3600)
        if hard < soft:
            raise ValueError("hard_timeout_seconds must be >= soft_timeout_seconds")
        reaction = _ensure_dict(v4, "reaction")
        if "reaction_enabled" in item:
            reaction["enabled"] = bool(item.get("reaction_enabled"))
        reaction.setdefault("emoji_type", "Typing")
        reaction.setdefault("add_immediately", True)
        reaction.setdefault("remove_on_success", True)
        reaction.setdefault("remove_on_failure", True)
        soul_cfg = _ensure_dict(v4, "soul")
        if "soul_version" in item and str(item.get("soul_version") or "").strip():
            soul_cfg["version"] = str(item.get("soul_version")).strip()
        soul_cfg.setdefault("bootstrap_once", True)
        profile = _ensure_dict(profiles, agent_id)
        profile["role"] = str(item.get("role") or profile.get("role") or meta["role"]).strip() or meta["role"]
        profile["workflow"] = str(item.get("workflow") or profile.get("workflow") or meta["workflow"]).strip() or meta["workflow"]
        if "soul" in item:
            save_agent_soul(agent_id, str(item.get("soul") or ""))
        app_id_env = APP_ID_ENV.get(agent_id, "")
        app_secret_env = APP_SECRET_ENV.get(agent_id, "")
        if "app_id" in item and app_id_env:
            upsert_lumen_env_var(app_id_env, str(item.get("app_id") or "").strip())
        if "app_secret" in item and app_secret_env:
            secret = str(item.get("app_secret") or "").strip()
            if secret:
                upsert_lumen_env_var(app_secret_env, secret)
    save_agents_config(config)
    return agents_settings_payload(project=project_slug)
