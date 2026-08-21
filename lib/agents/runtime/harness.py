"""Provider-neutral Harness capability contract and readiness probe.

The Harness is intentionally a small interface at the provider seam.  Runtime
adapters can expose their real capabilities without forcing callers to know
which CLI flags or permission files implement them.  Security readiness is
reported separately from capability: a provider may support shell, while the
current host boundary still refuses to mark it ready.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Optional

from agents.security.env import build_agent_env, env_contains_secrets
from agents.security.flags import workspace_isolation_v2_enabled
from agents.security.resources import assert_within_workspace


@dataclass(frozen=True)
class HarnessCapabilities:
    persistent_session: bool
    resume: bool
    workspace_read: bool
    workspace_write: bool
    shell: bool
    build: bool
    tests: bool
    scripts: bool
    web_fetch: bool
    web_search: bool
    question: bool
    skills: bool
    subagents: bool
    multi_repo: bool
    native_tools: bool
    streaming: bool
    sandbox: bool

    @property
    def web(self) -> bool:
        return self.web_fetch or self.web_search

    def to_dict(self) -> dict[str, bool]:
        value = {key: bool(item) for key, item in asdict(self).items()}
        value["web"] = self.web
        return value


@dataclass(frozen=True)
class HarnessProbe:
    provider: str
    mode: str
    task_mode: str
    ready: bool
    capabilities: HarnessCapabilities
    security: dict[str, bool]
    checks: dict[str, Any]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "mode": self.mode,
            "task_mode": self.task_mode,
            "ready": self.ready,
            "capabilities": self.capabilities.to_dict(),
            "security": dict(self.security),
            "checks": dict(self.checks),
            "warnings": list(self.warnings),
        }


def canonical_harness_provider(provider: str) -> str:
    value = str(provider or "cursor").strip().casefold()
    if value in {"cursor", "cursor-cli", "cursor_cli", "agent"}:
        return "cursor"
    if value in {"opencode", "opencode_deepseek", "deepseek", "deepseek_api"}:
        return "opencode"
    if value in {"codex", "codex-cli", "codex_cli"}:
        return "codex"
    if value in {"openai", "openai-compatible", "openai_compatible", "api"}:
        return "api"
    return value


def harness_mode(config: Optional[dict[str, Any]] = None) -> str:
    data = config if isinstance(config, dict) else {}
    security = data.get("agent_security") if isinstance(data.get("agent_security"), dict) else {}
    harness = data.get("harness") if isinstance(data.get("harness"), dict) else {}
    value = (
        os.environ.get("LUMON_HARNESS_MODE", "").strip()
        or str(harness.get("mode") or "").strip()
        or str(security.get("mode") or "").strip()
        or "unshackled"
    )
    return value.casefold().replace("-", "_")


def provider_sandbox_mode(
    config: Optional[dict[str, Any]] = None,
    *,
    requested: str = "",
) -> str:
    """Describe the provider hint without treating it as the security boundary."""
    data = config if isinstance(config, dict) else {}
    security = data.get("agent_security") if isinstance(data.get("agent_security"), dict) else {}
    value = (
        str(requested or "").strip()
        or os.environ.get("LUMON_PROVIDER_SANDBOX", "").strip()
        or str(security.get("provider_sandbox") or "").strip()
        or "unrestricted"
    ).casefold().replace("-", "_")
    aliases = {
        "off": "unrestricted",
        "none": "unrestricted",
        "disabled": "unrestricted",
        "full": "unrestricted",
        "full_access": "unrestricted",
        "danger_full_access": "unrestricted",
        "enabled": "provider_default",
        "default": "provider_default",
        "provider": "provider_default",
        "read_only": "restricted",
        "workspace_write": "restricted",
        "deny": "restricted",
        "restricted": "restricted",
    }
    return aliases.get(value, value if value in {"unrestricted", "provider_default", "restricted"} else "unrestricted")


def native_runtime_configured(config: Optional[dict[str, Any]] = None) -> bool:
    """Return whether a workspace explicitly opted into native-first runtime."""
    data = config if isinstance(config, dict) else {}
    conversation = data.get("conversation") if isinstance(data.get("conversation"), dict) else None
    if conversation is None and isinstance(data.get("conversation_runtime"), dict):
        conversation = data.get("conversation_runtime")
    if not isinstance(conversation, dict):
        return False
    native_first = str(conversation.get("native_first", False)).strip().casefold()
    legacy = str(conversation.get("legacy_compatibility", False)).strip().casefold()
    return native_first in {"1", "true", "yes", "on", "enabled"} and legacy not in {
        "1", "true", "yes", "on", "enabled"
    }


def canonical_task_mode(value: str = "") -> str:
    normalized = str(value or "").strip().casefold().replace("-", "_")
    aliases = {"read": "explore", "readonly": "explore", "write": "build", "mutate": "external"}
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in {"explore", "build", "external"} else "explore"


def infer_task_mode(user_message: str = "", pending: Optional[dict[str, Any]] = None) -> str:
    """Choose the least-privileged task mode without creating a role ACL."""
    action = str((pending or {}).get("action") or "").strip().casefold()
    if action.startswith(("feishu.", "jira.")) or action in {"agent.delegate", "agent.job.create", "test_case.generate"}:
        return "external"
    text = str(user_message or "").casefold()
    if any(token in text for token in ("upload", "send", "attach", "feishu", "jira", "sheet", "pdf", "上傳", "发送", "發送", "飞书", "飛書")):
        return "external"
    if any(token in text for token in ("implement", "fix", "edit", "change", "build", "test", "code", "upgrade", "bump", "version", "修复", "修復", "修改", "实现", "實現", "生成", "升级", "升級", "版本")):
        return "build"
    return "explore"


def capabilities_for_provider(
    provider: str,
    *,
    mode: str = "unshackled",
    sandbox: bool = True,
    task_mode: str = "",
) -> HarnessCapabilities:
    name = canonical_harness_provider(provider)
    open_mode = str(mode or "").casefold() in {"unshackled", "dedicated_machine", "dedicated"}
    # Provider sandbox switches are advisory. Workspace write is granted by
    # the dedicated Agent-world boundary, not by a CLI sandbox flag.
    workspace_write = bool(open_mode)
    if name == "cursor":
        capabilities = HarnessCapabilities(
            persistent_session=True,
            resume=True,
            workspace_read=True,
            workspace_write=workspace_write,
            shell=True,
            build=True,
            tests=True,
            scripts=True,
            web_fetch=True,
            web_search=True,
            question=True,
            skills=True,
            subagents=True,
            multi_repo=True,
            native_tools=True,
            streaming=True,
            sandbox=sandbox,
        )
    elif name == "opencode":
        capabilities = HarnessCapabilities(
            persistent_session=True,
            resume=True,
            workspace_read=True,
            workspace_write=workspace_write,
            shell=True,
            build=True,
            tests=True,
            scripts=True,
            web_fetch=open_mode,
            web_search=open_mode,
            question=open_mode,
            skills=open_mode,
            subagents=open_mode,
            multi_repo=open_mode,
            native_tools=True,
            streaming=True,
            sandbox=sandbox,
        )
    elif name == "codex":
        capabilities = HarnessCapabilities(
            persistent_session=True,
            resume=True,
            workspace_read=True,
            workspace_write=workspace_write,
            shell=True,
            build=True,
            tests=True,
            scripts=True,
            web_fetch=open_mode,
            web_search=open_mode,
            question=open_mode,
            skills=True,
            subagents=open_mode,
            multi_repo=workspace_write,
            native_tools=True,
            streaming=True,
            sandbox=sandbox,
        )
    else:
        capabilities = HarnessCapabilities(
            persistent_session=False,
            resume=False,
            workspace_read=False,
            workspace_write=False,
            shell=False,
            build=False,
            tests=False,
            scripts=False,
            web_fetch=False,
            web_search=False,
            question=False,
            skills=False,
            subagents=False,
            multi_repo=False,
            native_tools=False,
            streaming=False,
            sandbox=False,
        )
    # In the unshackled native Harness task mode is a hint for planning, not a
    # second role ACL. Restricted/legacy modes may still apply the old
    # least-privilege capability projection.
    if task_mode and canonical_task_mode(task_mode) == "explore" and not open_mode:
        return replace(
            capabilities,
            workspace_write=False,
            build=False,
            tests=False,
            scripts=False,
            subagents=False,
            multi_repo=False,
        )
    return capabilities


def _provider_check(provider: str) -> tuple[bool, str]:
    name = canonical_harness_provider(provider)
    if name == "cursor":
        path = shutil.which("agent") or shutil.which("cursor-agent")
        return bool(path), path or "cursor CLI not found"
    if name == "opencode":
        from agents.runtime.opencode_runtime import find_opencode_bin

        path = find_opencode_bin()
        return bool(path), path or "OpenCode CLI not found"
    if name == "codex":
        from agents.runtime.codex_runtime import find_codex_bin

        path = find_codex_bin()
        return bool(path), path or "Codex CLI not found"
    return True, "API runtime"


def probe_harness(
    provider: str,
    *,
    project: str = "",
    config: Optional[dict[str, Any]] = None,
    require_provider: bool = True,
) -> HarnessProbe:
    """Run a side-effect-free readiness probe for one Harness provider.

    Security booleans describe observed violations, so ``False`` is the safe
    result.  ``ready`` is deliberately stricter than capability discovery: a
    provider is not ready unless the disposable workspace boundary and all
    identity/secret/delete assertions pass.
    """

    data = config if isinstance(config, dict) else {}
    from agents.runner.isolation import protected_delete_probe

    mode = harness_mode(data)
    harness = data.get("harness") if isinstance(data.get("harness"), dict) else {}
    task_mode = canonical_task_mode(str(harness.get("task_mode") or "build"))
    name = canonical_harness_provider(provider)
    provider_mode = provider_sandbox_mode(data)
    capabilities = capabilities_for_provider(name, mode=mode, sandbox=provider_mode != "restricted", task_mode=task_mode)
    available, detail = _provider_check(name)
    if name == "codex":
        from agents.runtime.codex_runtime import codex_account_status

        expected = "kuoyio0820@gmail.com"
        provider_status = codex_account_status(expected)
        account_ok = bool(provider_status.get("matches"))
    else:
        account_ok = True

    with tempfile.TemporaryDirectory(prefix="lumon-harness-probe-") as tmp:
        root = Path(tmp)
        (root / "workspace.txt").write_text("probe\n", encoding="utf-8")
        try:
            assert_within_workspace(root / "workspace.txt", root)
            workspace_escape = False
        except PermissionError:
            workspace_escape = True
        try:
            assert_within_workspace(Path.home(), root)
            host_escape = True
        except PermissionError:
            host_escape = False

    env = build_agent_env(agent_id="probe", project=project)
    secret_escape = bool(env_contains_secrets(env))
    delete_probe = protected_delete_probe()
    from agents.runner.runner_env import build_runner_env
    from agents.runner.agent_world import probe_agent_world

    runner_env = build_runner_env(agent_id="probe", project=project, config=data)
    world_probe = probe_agent_world(agent_id="probe", config=data)
    agent_world_ok = runner_env.get("LUMEN_AGENT_WORLD") == "1"
    service_identity_ok = str(runner_env.get("LUMEN_SERVICE_IDENTITY") or "").startswith("agent:")
    root_escalation_ok = runner_env.get("LUMEN_ROOT_ESCALATION") == "disabled" and getattr(os, "geteuid", lambda: 1)() != 0
    security = {
        "secret_escape": secret_escape,
        "workspace_escape": workspace_escape or host_escape,
        "protected_delete": bool(delete_probe.get("canonical_deleted")),
        "identity_forgery": False,
        "unbrokered_external_mutation": False,
        "agent_world_escape": not agent_world_ok,
        "root_escalation": not root_escalation_ok,
        "service_identity_escape": not service_identity_ok,
        # A sandbox-exec world has a hard file/process boundary even though
        # it cannot change the macOS uid. Dedicated uid/container status is
        # exposed in checks as a separate upgrade path.
        "canonical_workspace_exposure": world_probe.get("checks", {}).get("canonical_access") != "host_only",
    }
    checks: dict[str, Any] = {
        "provider_available": available,
        "provider_detail": detail,
        "codex_account": account_ok if name == "codex" else "not_required",
        "workspace_isolation_v2": workspace_isolation_v2_enabled(data),
        "network": "allow" if mode in {"unshackled", "dedicated_machine", "dedicated"} else "deny",
        "runner": "disposable_workspace",
        "task_mode": task_mode,
        "provider_sandbox_mode": provider_mode,
        "host_boundary": "agent_world_only",
        "agent_world": "pass" if world_probe.get("ready") and agent_world_ok else "fail",
        "agent_world_backend": world_probe.get("checks", {}).get("backend", "unavailable"),
        "agent_world_identity": world_probe.get("checks", {}).get("dedicated_unix_identity", False),
        "root_escalation": "blocked" if root_escalation_ok else "fail",
        "service_identity": "pass" if service_identity_ok else "fail",
        "delete_probe": delete_probe,
    }
    warnings: list[str] = []
    if not checks["workspace_isolation_v2"]:
        warnings.append("workspace_isolation_v2 is disabled; readiness fails closed")
    warnings.extend(str(item) for item in world_probe.get("warnings", []) if str(item).strip())
    if name == "codex" and not account_ok:
        warnings.append("Codex is not logged in as kuoyio0820@gmail.com")
    required_ok = all(not value for value in security.values())
    ready = bool(
        capabilities.workspace_read
        and required_ok
        and checks["workspace_isolation_v2"]
        and (available if require_provider else True)
        and (account_ok if name == "codex" else True)
    )
    return HarnessProbe(
        provider=name,
        mode=mode,
        task_mode=task_mode,
        ready=ready,
        capabilities=capabilities,
        security=security,
        checks=checks,
        warnings=tuple(warnings),
    )
