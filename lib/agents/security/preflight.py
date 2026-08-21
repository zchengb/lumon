from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Optional

from agents.dylan.permission_policy import OPEN_SANDBOX_PERMISSIONS
from agents.runner.isolation import protected_delete_probe
from agents.runner.workspace_mounts import ensure_runner_dirs
from agents.security.actions import ActionRequest
from agents.security.broker import CapabilityBroker
from agents.security.env import build_agent_env, env_contains_secrets
from agents.security.flags import security_flags, workspace_isolation_v2_enabled
from agents.security.resources import (
    HOST_INTROSPECTION_COMMANDS,
    assert_within_workspace,
    is_forbidden_host_path,
)
from agents.security.trusted import bind_action_request, trusted_context_from_meta
from feishu.config import load_agents_config


def _cursor_available() -> bool:
    return bool(shutil.which("agent") or shutil.which("cursor-agent"))


def _opencode_available() -> bool:
    from agents.runtime.opencode_runtime import find_opencode_bin

    return bool(find_opencode_bin())


def _codex_available() -> bool:
    from agents.runtime.codex_runtime import find_codex_bin

    return bool(find_codex_bin())


def _sandbox_defaults_ok() -> bool:
    from agents.runtime.cursor_runtime import CursorAgentRuntime

    runtime = CursorAgentRuntime()
    return runtime.sandbox not in {"restricted", "read-only"}


def _permission_profile_ok() -> bool:
    permissions = OPEN_SANDBOX_PERMISSIONS.get("permissions", {})
    allow = permissions.get("allow") or []
    deny = permissions.get("deny") or []
    return "Read(**)" in allow and "Write(**)" in allow and "Shell(**)" in allow and not any(
        item.startswith("Shell(") for item in deny
    )


def run_security_check(
    *,
    agent_id: str = "dylan",
    project: str = "",
    config: Optional[dict[str, Any]] = None,
    live: bool = False,
) -> dict[str, Any]:
    agent = str(agent_id or "dylan").strip().lower()
    cfg = config if isinstance(config, dict) else load_agents_config()
    flags = security_flags(cfg)
    from agents.dylan.model_client import _load_lumen_dotenv
    from agents.dylan.schemas import ConversationFlags
    from agents.runtime.openai_compatible import default_api_key_env, is_api_provider
    from agents.runtime.cursor_runtime import canonical_agent_provider

    _load_lumen_dotenv()
    model_flags = ConversationFlags.from_common({}, cfg, agent_id=agent)
    runtime_provider = canonical_agent_provider(model_flags.model.provider)
    api_provider = is_api_provider(model_flags.model.provider)
    checks: dict[str, Any] = {}
    warnings: list[str] = []
    critical_fail = False

    if runtime_provider == "opencode":
        from agents.runtime.opencode_runtime import is_local_opencode_provider

        checks["cursor_cli"] = "not_required"
        checks["opencode_cli"] = "pass" if _opencode_available() else "fail"
        local_model = is_local_opencode_provider(model_flags.model.model_name, model_flags.model.base_url)
        key_env = model_flags.model.api_key_env or "DEEPSEEK_API_KEY"
        checks["model_api"] = "pass" if local_model or os.environ.get(key_env, "").strip() else f"missing:{key_env}"
        if checks["opencode_cli"] != "pass" or checks["model_api"] != "pass":
            critical_fail = True
    elif runtime_provider == "codex":
        from agents.runtime.codex_runtime import codex_account_status

        checks["cursor_cli"] = "not_required"
        checks["codex_cli"] = "pass" if _codex_available() else "fail"
        account = codex_account_status(model_flags.model.account_email)
        checks["codex_account"] = "pass" if account["matches"] else f"mismatch:{account.get('email') or 'not_logged_in'}"
        if checks["codex_cli"] != "pass" or checks["codex_account"] != "pass":
            critical_fail = True
    elif api_provider:
        checks["cursor_cli"] = "not_required"
        key_env = model_flags.model.api_key_env or default_api_key_env(model_flags.model.provider)
        checks["model_api"] = "pass" if os.environ.get(key_env, "").strip() else f"missing:{key_env}"
        if checks["model_api"] != "pass":
            critical_fail = True
    else:
        checks["cursor_cli"] = "pass" if _cursor_available() else "fail"
        if checks["cursor_cli"] == "fail":
            critical_fail = True

    checks["sandbox"] = _sandbox_defaults_ok()
    checks["provider_sandbox_mode"] = str(
        (cfg.get("agent_security") or {}).get("provider_sandbox")
        if isinstance(cfg.get("agent_security"), dict)
        else "unrestricted"
    )
    if not checks["sandbox"]:
        warnings.append("provider requested a restricted mode; Agent-world boundary remains authoritative")

    checks["workspace_isolation_v2"] = "on" if workspace_isolation_v2_enabled(cfg) else "off"
    checks["permission_profile_v2"] = "pass" if _permission_profile_ok() else "fail"
    if checks["permission_profile_v2"] == "fail":
        critical_fail = True

    if flags.get("workspace_isolation_v2"):
        from agents.runner.runner_env import build_runner_env

        env = build_runner_env(agent_id=agent, project=project, config=cfg)
    else:
        env = build_agent_env(agent_id=agent, project=project)
    leaked = env_contains_secrets(env)
    checks["secret_env"] = "isolated" if not leaked else f"leaked:{','.join(leaked)}"
    if leaked:
        critical_fail = True
    if env.get("CURSOR_API_KEY"):
        warnings.append("CURSOR_API_KEY is explicitly enabled as a provider-scoped credential")
        checks["cursor_api_key"] = "provider_scoped"
    else:
        checks["cursor_api_key"] = "absent"

    if flags.get("workspace_isolation_v2"):
        dirs = ensure_runner_dirs(agent)
        runner_env = build_runner_env(agent_id=agent, project=project, source={"PATH": "/usr/bin"}, config=cfg)
        checks["runner"] = "local_isolated"
        checks["runner_home"] = str(dirs["home"])
        if Path(runner_env.get("HOME", "")).resolve() != dirs["home"].resolve():
            checks["runner_home_env"] = "fail"
            critical_fail = True
        else:
            checks["runner_home_env"] = "pass"
        if Path(runner_env.get("TMPDIR", "")).resolve() != dirs["tmp"].resolve():
            checks["runner_tmpdir"] = "fail"
            critical_fail = True
        else:
            checks["runner_tmpdir"] = "pass"
        checks["agent_world"] = "pass" if runner_env.get("LUMEN_AGENT_WORLD") == "1" else "fail"
        checks["root_escalation"] = "blocked" if runner_env.get("LUMEN_ROOT_ESCALATION") == "disabled" else "fail"
        checks["service_identity"] = "pass" if str(runner_env.get("LUMEN_SERVICE_IDENTITY") or "").startswith("agent:") else "fail"
        if (
            checks["agent_world"] == "fail"
            or checks["service_identity"] == "fail"
            or checks["root_escalation"] != "blocked"
        ):
            critical_fail = True
    else:
        checks["runner"] = "host"
        warnings.append("workspace_isolation_v2 disabled")

    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        (workspace / "ok.txt").write_text("ok\n", encoding="utf-8")
        try:
            assert_within_workspace(workspace / "ok.txt", workspace)
            checks["workspace_read"] = "allowed"
        except Exception as exc:
            checks["workspace_read"] = f"fail:{exc}"
            critical_fail = True
        desktop = Path.home() / "Desktop" / "lumen-security-probe.png"
        try:
            assert_within_workspace(desktop, workspace)
            checks["workspace_escape"] = "fail"
            critical_fail = True
        except PermissionError:
            checks["workspace_escape"] = "blocked"
        apps = Path("/Applications")
        try:
            assert_within_workspace(apps, workspace)
            checks["host_apps"] = "fail"
            critical_fail = True
        except PermissionError:
            checks["host_apps"] = "blocked"
        checks["host_write"] = "blocked" if is_forbidden_host_path(Path.home() / "Library" / "LaunchAgents") else "fail"
        if checks["host_write"] != "blocked":
            critical_fail = True
        checks["host_introspection_deny"] = "pass" if "system_profiler" in HOST_INTROSPECTION_COMMANDS else "fail"
        if checks["host_introspection_deny"] != "pass":
            critical_fail = True
        link = workspace / "escape-link"
        try:
            link.symlink_to(Path.home() / "Desktop")
            try:
                assert_within_workspace(link, workspace)
                checks["symlink_escape"] = "fail"
                critical_fail = True
            except PermissionError:
                checks["symlink_escape"] = "blocked"
        except OSError:
            checks["symlink_escape"] = "skipped"

    broker = CapabilityBroker(config=cfg, audit=False)
    denied = broker.execute(
        ActionRequest(
            agent_id=agent,
            action="filesystem.delete",
            project_slug=project or "probe",
            actor_user_id="security-check",
            chat_id="security-check",
            thread_id="",
            source_message_id="security-check",
            trace_id="security-check",
            explicit_authorization=True,
        )
    )
    checks["broker"] = "active" if denied.status == "denied" else "fail"
    if checks["broker"] != "active":
        critical_fail = True

    forged = trusted_context_from_meta(
        agent_id=agent,
        project_slug=project or "probe",
        meta={"user_id": "ou_trusted", "chat_id": "oc_trusted", "message_id": "om1"},
        trace_id="security-check",
        explicit_authorization=False,
    )
    bound = bind_action_request(
        context=forged,
        action="risk.read",
        arguments={"actor_user_id": "ou_forged", "explicit_authorization": True},
    )
    checks["trusted_context"] = (
        "pass"
        if bound.actor_user_id == "ou_trusted" and bound.explicit_authorization is False
        else "fail"
    )
    if checks["trusted_context"] != "pass":
        critical_fail = True

    access = cfg.get("access") if isinstance(cfg.get("access"), dict) else {}
    checks["authorization"] = "active"
    checks["network"] = str(flags.get("network") or "allow")
    checks["access_configured"] = bool(
        access.get("mutation_allowed_user_ids") or access.get("admin_user_ids")
    )
    checks["host_visibility"] = "denied" if flags.get("workspace_isolation_v2") else "limited"

    delete_probe = protected_delete_probe()
    checks["protected_delete"] = (
        "blocked"
        if delete_probe.get("status") == "blocked" and not delete_probe.get("canonical_deleted")
        else "fail"
    )
    if checks["protected_delete"] != "blocked":
        critical_fail = True
    checks["identity_forgery"] = checks.get("trusted_context")

    if live:
        if os.environ.get("LUMEN_SECURITY_E2E") != "1":
            checks["live"] = "skipped_set_LUMEN_SECURITY_E2E=1"
        else:
            checks["live"] = "requested"
            warnings.append("live probes are optional and not required for CI")

    status = "fail" if critical_fail else "pass"
    return {
        "status": status,
        "agent_id": agent,
        "project": project,
        "sandbox": bool(checks["sandbox"]),
        "workspace_escape": checks.get("workspace_escape"),
        "host_write": checks.get("host_write"),
        "host_visibility": checks.get("host_visibility"),
        "runner": checks.get("runner"),
        "secret_env": checks.get("secret_env"),
        "network": checks.get("network"),
        "broker": checks.get("broker"),
        "authorization": checks.get("authorization"),
        "workspace_isolation_v2": checks.get("workspace_isolation_v2"),
        "protected_delete": checks.get("protected_delete"),
        "identity_forgery": checks.get("identity_forgery"),
        "harness_mode": flags.get("mode"),
        "warnings": warnings,
        "checks": checks,
        "conversation_enabled": status == "pass",
    }


def assert_security_gate(config: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    result = run_security_check(config=config)
    if result.get("status") != "pass":
        raise RuntimeError(json.dumps(result, ensure_ascii=False))
    return result
