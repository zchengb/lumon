#!/usr/bin/env python3
"""Serve Lumen's local interactive dashboard on loopback only."""

from __future__ import annotations

import argparse
import importlib.util
import json
import mimetypes
import os
import re
import shutil
import signal
import shlex
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from delivery_launchd import install as install_delivery_schedule
from delivery_launchd import remove as remove_delivery_schedule
from delivery_launchd import status as delivery_schedule_status
from patch_launchd import install as install_patch_schedule
from patch_launchd import remove as remove_patch_schedule
from patch_launchd import status as patch_schedule_status
from cleanup_delivery_worktrees import cleanup as cleanup_delivery_worktrees
from delivery_workspace import find_story_dir, load_story_context, normalize_verification_settings, read_json as read_delivery_json, workspace_lumen_dir
from jira_delivery_sync import add_delivery_comment, jira_delivery_config, should_sync_jira, transition_issue
from jira_sync import parse_twg_json, refresh_twg_auth, run_twg, twg_ready, workspace_jira_config
from issue_registry import set_issue_status
from projects_registry import find_by_slug, load_registry
from scan_launchd import install as install_scan_schedule
from scan_launchd import remove as remove_scan_schedule
from scan_launchd import status as scan_schedule_status
from discover_repos import default_branch, infer_profile
from delivery_scheduler import DEFAULT_ELIGIBLE_JIRA_STATUSES, eligible_jira_statuses, normalize_statuses
from sync_delivery_docs import commit_dirty_config, commit_paths, commit_story_metadata, lumen_commit_subject
from git_sync import force_push_conflict, read_conflict
from patch_runtime import DEFAULT_PATCH_TRIGGER_LABEL, patch_candidate_options, patch_config, publish_mode as patch_publish_mode
from deployment_tracking import normalized_config


SCRIPT_DIR = Path(__file__).resolve().parent
LIB_DIR = SCRIPT_DIR.parent
WORKSPACE_STATIC_DIRECTORIES = {"assets", "dashboard-app", "reports", "logs", "results"}
LUMON_PROVIDER_KEYS = {"DEEPSEEK_API_KEY", "OPENAI_API_KEY"}


def dashboard_provider(value: object) -> str:
    provider = str(value or "cursor_cli").strip().casefold()
    if provider in {"codex", "codex_cli", "codex-cli"}:
        return "codex"
    if provider in {"deepseek", "deepseek_api", "opencode_deepseek"}:
        return "opencode"
    if provider in {"cursor", "cursor-cli", "cursor_cli"}:
        return "cursor_cli"
    if provider in {"openai", "openai_compatible", "openai-compatible"}:
        return "openai_compatible"
    return provider


def opencode_runtime_status(workspace: Path, model: dict[str, str], configured_keys: list[str]) -> dict[str, Any]:
    provider = dashboard_provider(model.get("provider"))
    account: dict[str, str | bool] = {}
    login_detail = ""
    if provider == "opencode":
        try:
            from agents.runtime.opencode_runtime import find_opencode_bin

            command = find_opencode_bin()
        except Exception:
            command = shutil.which("opencode") or ""
    elif provider == "cursor_cli":
        command = shutil.which("agent") or shutil.which("cursor-agent") or ""
    elif provider == "codex":
        try:
            from agents.runtime.codex_runtime import codex_account_status, codex_login_status, find_codex_bin

            command = find_codex_bin()
            account = codex_account_status(model.get("account_email") or "kuoyio0820@gmail.com")
            _, login_detail = codex_login_status(command=command, codex_home=Path(str(account.get("home") or "")))
        except Exception as exc:
            command = ""
            login_detail = str(exc)[:160]
    else:
        command = ""
    version = ""
    if command:
        try:
            version = subprocess.run([command, "--version"], capture_output=True, text=True, timeout=5, check=False).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            version = ""
    local_opencode = provider == "opencode" and (
        str(model.get("model") or "").strip().casefold().startswith("qwen/")
        or str(model.get("base_url") or "").strip().casefold().startswith(("http://127.0.0.1", "http://localhost", "http://0.0.0.0"))
    )
    defaults = {
        "opencode": "" if local_opencode else "DEEPSEEK_API_KEY",
        "cursor_cli": "CURSOR_API_KEY",
        "codex": "ChatGPT login",
        "openai_compatible": "OPENAI_API_KEY",
    }
    key_env = model.get("api_key_env") or defaults.get(provider, "")
    codex_ready = bool(command) and bool(account.get("configured")) and bool(account.get("matches")) and not login_detail.casefold().startswith("not logged in")
    return {
        "harness": {"opencode": "OpenCode", "cursor_cli": "Cursor CLI", "codex": "Codex CLI"}.get(provider, "OpenAI-compatible API"),
        "provider": provider,
        "model": model.get("model", ""),
        "reasoning_effort": model.get("reasoning_effort", ""),
        "command": command,
        "version": version,
        "installed": bool(command) if provider in {"opencode", "cursor_cli", "codex"} else True,
        "api_key_env": key_env,
        "api_key_configured": codex_ready if provider == "codex" else local_opencode or key_env in configured_keys,
        "account_email": str(account.get("email") or "") if provider == "codex" else "",
        "expected_account_email": str(account.get("expected_email") or model.get("account_email") or "") if provider == "codex" else "",
        "account_configured": codex_ready if provider == "codex" else True,
        "account_match": bool(account.get("matches")) if provider == "codex" else True,
        "auth_detail": login_detail if provider == "codex" else "",
        "session_mode": "persistent Codex session" if provider == "codex" else "persistent provider session" if provider == "opencode" else "provider managed",
        "action_catalog": str((workspace / ".lumon" / "action-catalog.md").resolve()),
        "permission_profile": "workspace Codex sandbox policy" if provider == "codex" else "workspace OpenCode permission policy" if provider == "opencode" else "provider sandbox policy",
    }

if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))


def load_dashboard_renderer() -> Any:
    spec = importlib.util.spec_from_file_location("lumen_dashboard_renderer", SCRIPT_DIR / "render-dashboard.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Dashboard renderer is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RENDERER = load_dashboard_renderer()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def terminate_process_tree(pid: int) -> None:
    try:
        children = subprocess.run(["pgrep", "-P", str(pid)], capture_output=True, text=True, check=False).stdout.split()
    except OSError:
        children = []
    for child in children:
        try:
            terminate_process_tree(int(child))
        except ValueError:
            continue
    try:
        os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, OSError):
        pass


def delivery_process_active(workspace: Path) -> bool:
    pid_path = workspace / "locks" / "delivery-run" / "pid"
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
    return payload if isinstance(payload, dict) else default


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def prompt_files(workspace: Path) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for mode in ("scan", "delivery", "patch"):
        root = workspace / "prompts" / mode
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            items.append({"mode": mode, "path": str(path.relative_to(root))})
    return items


def safe_prompt_path(workspace: Path, mode: str, relative: str) -> Path:
    if mode not in {"scan", "delivery", "patch"}:
        raise ValueError("Unknown prompt mode")
    root = (workspace / "prompts" / mode).resolve()
    path = (root / relative).resolve()
    if root not in path.parents or path.suffix != ".md":
        raise ValueError("Invalid prompt path")
    return path


def safe_workspace_static_path(workspace: Path, request_path: str) -> Path:
    """Resolve a dashboard artifact without exposing the rest of the workspace."""
    relative = Path(unquote(request_path).lstrip("/"))
    if not relative.parts or relative.parts[0] not in WORKSPACE_STATIC_DIRECTORIES:
        raise ValueError("Unknown workspace artifact")
    root = (workspace / relative.parts[0]).resolve()
    path = (workspace / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("Invalid workspace artifact path") from exc
    return path


def schedule_payload(workspace: Path, project: str) -> dict[str, Any]:
    scan_raw = capture_schedule_status(scan_schedule_status, project)
    delivery_raw = capture_schedule_status(delivery_schedule_status, project)
    delivery_config = load_json(workspace / "config" / "delivery.json", {})
    automation = delivery_config.get("automation") if isinstance(delivery_config.get("automation"), dict) else {}
    scheduled = automation.get("scheduled_delivery") if isinstance(automation.get("scheduled_delivery"), dict) else {}
    scheduled_patch = automation.get("scheduled_auto_patch") if isinstance(automation.get("scheduled_auto_patch"), dict) else {}
    jira = delivery_config.get("jira") if isinstance(delivery_config.get("jira"), dict) else {}
    if delivery_raw is None:
        delivery_raw = {"enabled": False}
    delivery_raw.setdefault("enabled", True)
    configured_statuses = eligible_jira_statuses(delivery_config)
    scheduled_statuses = scheduled.get("eligible_jira_statuses") or scheduled.get("required_jira_status")
    runtime_statuses = normalize_statuses(scheduled_statuses or delivery_raw.get("jira_statuses") or delivery_raw.get("jira_status"), tuple(configured_statuses or DEFAULT_ELIGIBLE_JIRA_STATUSES))
    delivery_raw["jira_statuses"] = runtime_statuses
    delivery_raw["jira_status"] = runtime_statuses[0] if runtime_statuses else ""
    delivery_raw["in_dev_status"] = jira.get("in_dev_status", "")
    delivery_raw["dev_done_status"] = jira.get("dev_done_status", "")
    delivery_raw["blocked_status"] = jira.get("blocked_status", "Block")
    patch_raw = capture_schedule_status(patch_schedule_status, project) or {"enabled": False}
    patch_raw["enabled"] = bool(patch_raw.get("enabled")) and bool(scheduled_patch.get("enabled", True))
    patch_raw["interval_seconds"] = int(patch_raw.get("interval_seconds") or int(scheduled_patch.get("poll_interval_minutes", 5)) * 60)
    patch_raw["jira_statuses"] = normalize_statuses(scheduled_patch.get("eligible_jira_statuses"), ("To Do",))
    patch_raw["issue_types"] = normalize_statuses(scheduled_patch.get("issue_types"), ("Task", "Bug"))
    patch_raw["trigger_label"] = str(scheduled_patch.get("required_label") or DEFAULT_PATCH_TRIGGER_LABEL).strip()
    patch_raw["in_progress_status"] = scheduled_patch.get("in_progress_status", "In Progress")
    patch_raw["done_status"] = scheduled_patch.get("done_status", "Done")
    patch_raw["blocked_status"] = scheduled_patch.get("blocked_status", "Block")
    return {
        "scan": scan_raw,
        "delivery": delivery_raw,
        "patch": patch_raw,
        "platform": "launchd" if sys.platform == "darwin" else "unsupported",
    }


def jira_status_options(workspace: Path) -> dict[str, Any]:
    """Use an existing Story as the workflow probe; cache reads to keep dashboard refreshes cheap."""
    cache_path = workspace / "state" / "jira-workflow-statuses.json"
    cached = load_json(cache_path, {})
    cached_at = cached.get("fetched_at", "")
    try:
        fresh = datetime.now(timezone.utc) - datetime.fromisoformat(str(cached_at).replace("Z", "+00:00")) < timedelta(minutes=5)
    except ValueError:
        fresh = False
    if fresh and isinstance(cached.get("options"), list):
        return cached

    ready, detail = twg_ready()
    if not ready:
        return {"options": [], "detail": detail}
    stories = workspace.parent / "stories"
    metadata_paths = sorted(stories.glob("*/metadata.json")) if stories.is_dir() else []
    metadata = next((load_json(path, {}) for path in metadata_paths if str(load_json(path, {}).get("jiraKey", "")).strip()), {})
    jira_key = str(metadata.get("jiraKey", "")).strip()
    if not jira_key:
        return {"options": [], "detail": "No JIRA-backed Story is available to inspect the workflow."}
    code, output = run_twg(["jira", "workitem", "get", jira_key, "-o", "json"])
    if code != 0:
        return {"options": [], "detail": "Unable to read JIRA workflow status."}
    payload = parse_twg_json(output) or {}
    data = payload.get("data") if isinstance(payload, dict) else {}
    item = data[0] if isinstance(data, list) and data else data
    if not isinstance(item, dict) or not item.get("id"):
        return {"options": [], "detail": "JIRA workflow probe returned no work item."}
    current = item.get("status") if isinstance(item.get("status"), dict) else {}
    current_name = str(current.get("name", "")).strip()
    code, output = run_twg(["jira", "workitem", "transitions", "query", "--id", str(item["id"]), "-o", "json"])
    if code != 0:
        return {"options": [current_name] if current_name else [], "source_jira_key": jira_key, "detail": "Unable to read available Jira transitions."}
    transitions_payload = parse_twg_json(output) or {}
    transition_data = transitions_payload.get("data") if isinstance(transitions_payload, dict) else {}
    transitions = transition_data.get("transitions") if isinstance(transition_data, dict) else []
    names = [current_name] + [str(item.get("toName") or item.get("name") or "").strip() for item in transitions if isinstance(item, dict)]
    result = {"options": list(dict.fromkeys(name for name in names if name)), "source_jira_key": jira_key, "fetched_at": utc_now()}
    write_json(cache_path, result)
    return result


def capture_schedule_status(func: Any, project: str) -> dict[str, Any] | None:
    parser = argparse.Namespace(project=project)
    from contextlib import redirect_stdout
    from io import StringIO

    output = StringIO()
    with redirect_stdout(output):
        func(parser)
    text = output.getvalue().strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {"detail": text}
    return payload if isinstance(payload, dict) else None


def workflow_model_config(execution: object, prefix: str = "") -> dict[str, str]:
    values = execution if isinstance(execution, dict) else {}
    provider = dashboard_provider(values.get(f"{prefix}provider") or values.get("provider") or "cursor_cli")
    default_model = {
        "codex": "gpt-5.6-luna",
        "opencode": "deepseek-v4-flash",
        "openai_compatible": "gpt-4o-mini",
    }.get(provider, "cursor-grok-4.5-medium")
    model = str(values.get(f"{prefix}model") or values.get("model") or default_model).strip()
    base_url = str(values.get(f"{prefix}base_url") or values.get("base_url") or "").strip()
    api_key_env = str(values.get(f"{prefix}api_key_env") or values.get("api_key_env") or "").strip()
    reasoning_effort = str(values.get(f"{prefix}reasoning_effort") or values.get("reasoning_effort") or ("xhigh" if provider == "codex" else "")).strip()
    account_email = str(values.get(f"{prefix}account_email") or values.get("account_email") or ("kuoyio0820@gmail.com" if provider == "codex" else "")).strip()
    return {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "api_key_env": api_key_env,
        "reasoning_effort": reasoning_effort,
        "account_email": account_email,
    }


def workspace_payload(workspace: Path) -> dict[str, Any]:
    common = load_json(workspace / "config" / "common.json", {})
    env_local = workspace / ".env.local"
    configured_keys: list[str] = []
    integration_sources: dict[str, str] = {}
    if env_local.is_file():
        for line in env_local.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" not in line or line.lstrip().startswith("#"):
                continue
            key, value = line.split("=", 1)
            if value.strip().strip('"').strip("'"):
                name = key.strip()
                configured_keys.append(name)
                integration_sources[name] = "workspace"
    lumen_env_local = Path(os.environ.get("LUMON_HOME", Path.home() / ".lumon")).expanduser() / ".env.local"
    if lumen_env_local.is_file():
        for line in lumen_env_local.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" not in line or line.lstrip().startswith("#"):
                continue
            key, value = line.split("=", 1)
            name = key.strip()
            if name in LUMON_PROVIDER_KEYS and value.strip().strip('"').strip("'"):
                configured_keys.append(name)
                integration_sources[name] = "lumon_local"
    repos_config = load_json(workspace / "config" / "repos.json", {"repositories": []})
    profiles = load_json(workspace / "config" / "runtime-profiles.json", {})
    delivery_config = load_json(workspace / "config" / "delivery.json", {})
    verification = delivery_config.get("verification") if isinstance(delivery_config.get("verification"), dict) else {}
    steps = verification.get("steps") if isinstance(verification.get("steps"), dict) else {}
    repositories = repos_config.get("repositories") if isinstance(repos_config.get("repositories"), list) else []
    enriched_repositories = []
    for repository in repositories:
        if not isinstance(repository, dict):
            continue
        entry = dict(repository)
        runtime = entry.pop("runtime", {})
        runtime = runtime if isinstance(runtime, dict) else {}
        entry["runtime_configured"] = bool(runtime)
        entry["automation"] = repository_automation(entry)
        repository_name = str(entry.get("name", ""))
        delivery_steps = steps.get(repository_name, [])
        entry["delivery_steps"] = delivery_steps
        entry["verification"] = normalize_verification_settings(
            repository.get("verification"),
            has_custom_commands=bool(delivery_steps),
        )
        path = Path(str(entry.get("path", "")))
        entry["branches"] = repository_branches(path, str(entry.get("default_branch", "main")))
        entry["health"] = repository_health(path, str(entry.get("default_branch", "main")), runtime, str(entry.get("runtime_profile", "")))
        enriched_repositories.append(entry)
    git_conflict = read_conflict(workspace / "state")
    if not all(str(git_conflict.get(key) or "").strip() for key in ("repo", "branch", "remote_oid", "local_oid")):
        git_conflict = None
    return {
        "path": str(workspace),
        "scan_window_days": (common.get("execution") or {}).get("scan_window_days", 7),
        "configured_integrations": sorted(set(key for key in configured_keys if key)),
        "integration_sources": integration_sources,
        "repositories": enriched_repositories,
        "runtime_profiles": profiles,
        "publish": {
            "scan": str(((common.get("auto_fix") or {}).get("publish_mode") or "pr")),
            "delivery": str(((delivery_config.get("publish") or {}).get("mode") or "pr")),
            # patch_runtime expects the docs workspace root, while this
            # function receives its visible `lumen/` directory.
            "patch": patch_publish_mode(workspace.parent),
        },
        "model_config": workflow_model_config(common.get("execution")),
        "runtime": opencode_runtime_status(workspace, workflow_model_config(common.get("execution")), sorted(set(configured_keys))),
        # Keep the old per-workflow shape for existing dashboard clients. The
        # values intentionally all come from the one workspace-level config.
        "models": {
            "scan": workflow_model_config(common.get("execution")).get("model", ""),
            "delivery": workflow_model_config(common.get("execution")).get("model", ""),
            "patch": workflow_model_config(common.get("execution")).get("model", ""),
        },
        "model_configs": {
            "scan": workflow_model_config(common.get("execution")),
            "delivery": workflow_model_config(common.get("execution")),
            "patch": workflow_model_config(common.get("execution")),
        },
        "deployment_tracking": normalized_config(delivery_config),
        "feishu_notifications_enabled": feishu_notifications_enabled(workspace),
        "git_sync_conflict": git_conflict,
    }


def repository_automation(repository: dict[str, Any]) -> dict[str, dict[str, bool]]:
    automation = repository.get("automation") if isinstance(repository.get("automation"), dict) else {}
    scan = automation.get("scan") if isinstance(automation.get("scan"), dict) else {}
    delivery = automation.get("delivery") if isinstance(automation.get("delivery"), dict) else {}
    patch = automation.get("patch") if isinstance(automation.get("patch"), dict) else {}
    return {
        "scan": {
            "allow_auto_fix": bool(scan.get("allow_auto_fix", repository.get("allow_auto_fix", True))),
        },
        "delivery": {"enabled": bool(delivery.get("enabled", True))},
        "patch": {"enabled": bool(patch.get("enabled", True))},
    }


def git_output(repository: Path, *args: str) -> str:
    if not repository.is_dir() or not (repository / ".git").exists():
        return ""
    completed = subprocess.run(["git", "-C", str(repository), *args], capture_output=True, text=True, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def configured_node_version(repository: Path, runtime: dict[str, Any]) -> str:
    configured = str(runtime.get("node_version", "")).strip()
    if configured:
        return configured
    for name in (".nvmrc", ".node-version"):
        path = repository / name
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="ignore").strip()
    package = repository / "package.json"
    if package.is_file():
        try:
            engines = json.loads(package.read_text(encoding="utf-8")).get("engines", {})
            if isinstance(engines, dict):
                return str(engines.get("node", "")).strip()
        except (OSError, json.JSONDecodeError):
            pass
    return ""


def configured_java_version(repository: Path) -> str:
    version_file = repository / ".java-version"
    if version_file.is_file():
        match = re.search(r"\b(8|11|17|21)\b", version_file.read_text(encoding="utf-8", errors="ignore"))
        if match:
            return match.group(1)
    files = (repository / "build.gradle", repository / "build.gradle.kts", repository / "pom.xml")
    source = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in files if path.is_file())
    for pattern in (
        r"JavaLanguageVersion\.of\((\d+)\)",
        r"(?:sourceCompatibility|targetCompatibility)\s*=\s*(?:JavaVersion\.VERSION_|['\"]?)(\d+)",
        r"<(?:java\.version|maven\.compiler\.(?:release|source))>\s*(\d+)\s*</",
    ):
        match = re.search(pattern, source)
        if match:
            return match.group(1)
    return ""


def package_manager(repository: Path) -> str:
    for filename, name in (("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"), ("package-lock.json", "npm"), ("bun.lockb", "bun")):
        if (repository / filename).is_file():
            return name
    return ""


def repository_health(repository: Path, branch: str, runtime: dict[str, Any], profile: str) -> dict[str, Any]:
    files = {item.name for item in repository.iterdir()} if repository.is_dir() else set()
    is_java = bool(files & {"gradlew", "build.gradle", "build.gradle.kts", "pom.xml"})
    is_node = "package.json" in files
    tools = []
    if any((repository / name).is_file() for name in ("gradlew", "build.gradle", "build.gradle.kts")):
        tools.append("Gradle")
    elif (repository / "pom.xml").is_file():
        tools.append("Maven")
    manager = package_manager(repository)
    if manager:
        tools.append(manager)
    language = "Java" if is_java else "Node.js" if is_node else "PHP" if "composer.json" in files else str(profile or "Generic").replace("local-", "").replace("-review-only", "").replace("-", " ").title()
    package: dict[str, Any] = {}
    if is_node:
        try:
            package = json.loads((repository / "package.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            package = {}
    command_prefix = manager or "npm"
    suggestions: list[str] = []
    if (repository / "gradlew").is_file():
        suggestions = ["./gradlew compileJava compileTestJava -x test", "./gradlew test"]
    elif (repository / "pom.xml").is_file():
        suggestions = ["./mvnw test" if (repository / "mvnw").is_file() else "mvn test"]
    elif is_node:
        scripts = package.get("scripts") if isinstance(package.get("scripts"), dict) else {}
        for name in ("typecheck", "lint", "test"):
            if name in scripts:
                suggestions.append(f"{command_prefix} run {name}")
    status = git_output(repository, "status", "--porcelain")
    remote = git_output(repository, "remote", "get-url", "origin")
    counts = git_output(repository, "rev-list", "--left-right", "--count", f"origin/{branch}...HEAD").split()
    sync = "unknown"
    if len(counts) == 2 and all(count.isdigit() for count in counts):
        behind, ahead = (int(count) for count in counts)
        sync = "synced" if not ahead and not behind else "diverged" if ahead and behind else "ahead" if ahead else "behind"
    return {
        "language": language,
        "java_version": configured_java_version(repository) if is_java else "",
        "node_version": configured_node_version(repository, runtime) if is_node else "",
        "build_tools": tools,
        "git_status": "changes" if status else "clean",
        "sync_status": sync,
        "remote_url": remote,
        "suggested_commands": suggestions,
    }


def repository_branches(repository: Path, default: str) -> list[str]:
    if not repository.is_dir() or not (repository / ".git").exists():
        return [default] if default else []
    branches: list[str] = []
    for args in (("for-each-ref", "--format=%(refname:short)", "refs/heads"), ("for-each-ref", "--format=%(refname:short)", "refs/remotes/origin")):
        completed = subprocess.run(["git", *args], cwd=repository, capture_output=True, text=True)
        if completed.returncode != 0:
            continue
        for branch in completed.stdout.splitlines():
            name = branch.strip().removeprefix("origin/")
            if name and name != "HEAD" and not name.endswith("/HEAD") and name not in branches:
                branches.append(name)
    if default and default not in branches:
        branches.insert(0, default)
    return branches


def repository_name_from_url(url: str) -> str:
    candidate = url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
    name = candidate.removesuffix(".git")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", name):
        raise ValueError("Repository URL must end with a repository name")
    return name


def auto_commit_delivery_config(workspace: Path, summary: str = "update delivery config", *, push: bool = True) -> str:
    docs_dir = docs_dir_for_workspace(workspace)
    if not (docs_dir / ".git").exists():
        return "skipped"
    return commit_dirty_config(docs_dir, summary, push=push)


def save_repositories(workspace: Path, repositories: object, *, include_payload: bool = True) -> dict[str, Any]:
    if not isinstance(repositories, list):
        raise ValueError("Repositories must be a list")
    profiles = load_json(workspace / "config" / "runtime-profiles.json", {})
    cleaned = []
    delivery = load_json(workspace / "config" / "delivery.json", {})
    existing_config = load_json(workspace / "config" / "repos.json", {"repositories": []})
    existing_repositories = existing_config.get("repositories") if isinstance(existing_config.get("repositories"), list) else []
    verification = delivery.setdefault("verification", {})
    steps = verification.setdefault("steps", {})
    seen = set()
    for repository in repositories:
        if not isinstance(repository, dict):
            raise ValueError("Each repository must be an object")
        name = str(repository.get("name", "")).strip()
        path = Path(str(repository.get("path", "")).strip()).expanduser()
        branch = str(repository.get("default_branch", "")).strip() or "main"
        profile = str(repository.get("runtime_profile", "")).strip() or "local-generic-review-only"
        if not name or name in seen:
            raise ValueError("Repository names must be unique")
        if profile not in profiles:
            raise ValueError(f"Unknown runtime profile: {profile}")
        if not path.is_dir() or not (path / ".git").exists():
            raise ValueError(f"Repository is not a local Git checkout: {path}")
        seen.add(name)
        existing = next((item for item in existing_repositories if isinstance(item, dict) and str(item.get("name", "")).strip() == name), {})
        automation_source = dict(existing) if isinstance(existing, dict) else {}
        automation_source.update(repository)
        existing_automation = existing.get("automation") if isinstance(existing, dict) and isinstance(existing.get("automation"), dict) else {}
        supplied_automation = repository.get("automation") if isinstance(repository.get("automation"), dict) else {}
        automation_source["automation"] = {
            key: {**(existing_automation.get(key) if isinstance(existing_automation.get(key), dict) else {}), **(supplied_automation.get(key) if isinstance(supplied_automation.get(key), dict) else {})}
            for key in ("scan", "delivery", "patch")
        }
        automation = repository_automation(automation_source)
        existing_steps = steps.get(name, [])
        raw_verification = repository.get("verification")
        if not isinstance(raw_verification, dict):
            raw_verification = existing.get("verification") if isinstance(existing, dict) else {}
        incoming_commands = repository.get("delivery_commands")
        incoming_lines = incoming_commands.splitlines() if isinstance(incoming_commands, str) else incoming_commands
        has_incoming_commands = isinstance(incoming_lines, list) and any(str(command).strip() for command in incoming_lines)
        verification_settings = normalize_verification_settings(
            raw_verification,
            has_custom_commands=(isinstance(existing_steps, list) and bool(existing_steps)) or has_incoming_commands,
        )
        cleaned.append({
            "name": name,
            "path": str(path.resolve()),
            "remote_url": str(repository.get("remote_url", "")).strip() or git_output(path, "remote", "get-url", "origin"),
            "default_branch": branch,
            "runtime_profile": profile,
            "allow_auto_fix": automation["scan"]["allow_auto_fix"],
            "automation": automation,
            "verification": verification_settings,
        })
        if "generate_tests" in repository:
            cleaned[-1]["generate_tests"] = bool(repository.get("generate_tests"))
        runtime = repository.get("runtime")
        existing_runtime = existing.get("runtime") if isinstance(existing, dict) and isinstance(existing.get("runtime"), dict) else {}
        if runtime is not None or existing_runtime:
            if runtime is not None and not isinstance(runtime, dict):
                raise ValueError(f"Runtime configuration for {name} must be an object")
            stored_runtime = dict(existing_runtime)
            if isinstance(runtime, dict):
                stored_runtime.update({key: value for key, value in runtime.items() if key != "visual_auth_configured"})
            try:
                json.dumps(stored_runtime)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Runtime configuration for {name} must contain JSON values") from exc
            cleaned[-1]["runtime"] = stored_runtime
        if verification_settings["mode"] in {"auto", "skip"}:
            steps.pop(name, None)
        elif "delivery_commands" in repository:
            commands = repository["delivery_commands"]
            lines = commands.splitlines() if isinstance(commands, str) else commands
            if not isinstance(lines, list):
                raise ValueError("Delivery commands must be a list or text")
            parsed = [shlex.split(str(command)) for command in lines if str(command).strip()]
            if not parsed:
                raise ValueError(f"Custom verification for {name} requires at least one command")
            steps[name] = [
                {"id": f"configured-{index + 1}", "label": f"Configured verification {index + 1}", "command": command, "optional": False}
                for index, command in enumerate(parsed)
            ]
        elif not isinstance(existing_steps, list) or not existing_steps:
            raise ValueError(f"Custom verification for {name} requires at least one command")
    write_json(workspace / "config" / "repos.json", {"repositories": cleaned})
    write_json(workspace / "config" / "delivery.json", delivery)
    # Repository governance is edited interactively; do not block the Save
    # request on a remote fetch/rebase/push or trigger credential helpers.
    auto_commit_delivery_config(workspace, push=False)
    return workspace_payload(workspace) if include_payload else {"saved_at": utc_now()}


def clone_repository(workspace: Path, url: object, *, include_payload: bool = True) -> dict[str, Any]:
    remote_url = str(url).strip()
    if not remote_url:
        raise ValueError("Repository clone URL is required")
    name = repository_name_from_url(remote_url)
    destination = workspace.parent / "repos" / name
    if destination.exists():
        raise ValueError(f"Repository destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(["git", "clone", remote_url, str(destination)], capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "git clone failed").strip())
    config_path = workspace / "config" / "repos.json"
    config = load_json(config_path, {"repositories": []})
    repositories = config.get("repositories") if isinstance(config.get("repositories"), list) else []
    repositories.append({
        "name": name,
        "path": str(destination.resolve()),
        "remote_url": remote_url,
        "default_branch": default_branch(destination),
        "runtime_profile": infer_profile(destination),
        "allow_auto_fix": True,
        "automation": {
            "scan": {"allow_auto_fix": True},
            "delivery": {"enabled": True},
            "patch": {"enabled": True},
        },
    })
    return save_repositories(workspace, repositories, include_payload=include_payload)


def save_delivery_steps(workspace: Path, repository: str, commands: object, *, include_payload: bool = True) -> dict[str, Any]:
    name = str(repository).strip()
    if not name or not isinstance(commands, list):
        raise ValueError("Repository and commands are required")
    parsed = [shlex.split(str(command)) for command in commands if str(command).strip()]
    if any(not command for command in parsed):
        raise ValueError("Verification commands cannot be empty")
    path = workspace / "config" / "delivery.json"
    config = load_json(path, {})
    verification = config.setdefault("verification", {})
    steps = verification.setdefault("steps", {})
    steps[name] = [
        {"id": f"configured-{index + 1}", "label": f"Configured verification {index + 1}", "command": command, "optional": False}
        for index, command in enumerate(parsed)
    ]
    write_json(path, config)
    auto_commit_delivery_config(workspace)
    return workspace_payload(workspace) if include_payload else {"saved_at": utc_now()}


def save_publish_policy(workspace: Path, scan_mode: object, delivery_mode: object, patch_mode: object = "pr", *, push: bool = True, include_payload: bool = True) -> dict[str, Any]:
    if scan_mode not in {"pr", "merge"}:
        raise ValueError("Auto Scan supports only PR or Merge")
    if delivery_mode not in {"pr", "merge", "direct"}:
        raise ValueError("Auto Delivery supports PR, Merge, or Direct push")
    if patch_mode not in {"pr", "direct"}:
        raise ValueError("Auto Patch supports PR or Direct push")
    common_path = workspace / "config" / "common.json"
    common = load_json(common_path, {})
    common.setdefault("auto_fix", {})["publish_mode"] = scan_mode
    write_json(common_path, common)
    delivery_path = workspace / "config" / "delivery.json"
    delivery = load_json(delivery_path, {})
    delivery.setdefault("publish", {})["mode"] = delivery_mode
    delivery.setdefault("publish", {}).setdefault("auto_patch", {})["mode"] = patch_mode
    write_json(delivery_path, delivery)
    auto_commit_delivery_config(workspace, push=push)
    return workspace_payload(workspace) if include_payload else {"saved_at": utc_now()}


def integration_value(workspace: Path, key: str) -> str:
    if not key or not key.replace("_", "").isalnum() or key.upper() != key:
        raise ValueError("Integration key must use uppercase letters, numbers, and underscores")
    paths = [workspace / ".env.local"]
    if key in LUMON_PROVIDER_KEYS:
        paths.insert(0, Path(os.environ.get("LUMON_HOME", Path.home() / ".lumon")).expanduser() / ".env.local")
    for path in paths:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lstrip().startswith("#") or "=" not in line:
                continue
            candidate, value = line.split("=", 1)
            if candidate.strip() == key:
                try:
                    parsed = shlex.split(value, posix=True)
                except ValueError:
                    return value
                return parsed[0] if len(parsed) == 1 else value
    raise ValueError(f"Integration key is not configured: {key}")


def update_env_value(workspace: Path, key: str, value: str) -> None:
    if not key or not key.replace("_", "").isalnum() or key.upper() != key:
        raise ValueError("Integration key must use uppercase letters, numbers, and underscores")
    path = (
        Path(os.environ.get("LUMON_HOME", Path.home() / ".lumon")).expanduser() / ".env.local"
        if key in LUMON_PROVIDER_KEYS
        else workspace / ".env.local"
    )
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    serialized = value if value and not re.search(r"[\s#'\"\\]", value) else shlex.quote(value)
    entry = f"{key}={serialized}"
    for index, line in enumerate(lines):
        if line.split("=", 1)[0].strip() == key:
            lines[index] = entry
            break
    else:
        lines.append(entry)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_delivery_timestamp(value: object) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def delivery_duration(started_at: object, finished_at: object) -> str:
    started = parse_delivery_timestamp(started_at)
    finished = parse_delivery_timestamp(finished_at)
    if not started or not finished or finished < started:
        return "—"
    seconds = int((finished - started).total_seconds())
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m {seconds % 60:02d}s"


def phase_intervals(phase: dict[str, Any]) -> tuple[list[tuple[datetime, datetime]], bool]:
    attempts = phase.get("attempts")
    if isinstance(attempts, list):
        intervals = [
            (start, finish)
            for item in attempts
            if isinstance(item, dict)
            for start, finish in [(parse_delivery_timestamp(item.get("started_at")), parse_delivery_timestamp(item.get("finished_at")))]
            if start and finish and finish >= start
        ]
        return intervals, True
    start = parse_delivery_timestamp(phase.get("started_at"))
    finish = parse_delivery_timestamp(phase.get("finished_at"))
    return ([(start, finish)] if start and finish and finish >= start else []), False


def phase_attempt_records(phase: dict[str, Any]) -> list[tuple[datetime, datetime | None]]:
    raw_attempts = phase.get("attempts")
    if not isinstance(raw_attempts, list):
        raw_attempts = [{"started_at": phase.get("started_at"), "finished_at": phase.get("finished_at")}]
    records: list[tuple[datetime, datetime | None]] = []
    for item in raw_attempts:
        if not isinstance(item, dict):
            continue
        start = parse_delivery_timestamp(item.get("started_at"))
        finish = parse_delivery_timestamp(item.get("finished_at"))
        if start and (finish is None or finish >= start):
            records.append((start, finish))
    return records


def intervals_duration(intervals: list[tuple[datetime, datetime]]) -> str:
    seconds = sum(int((finish - start).total_seconds()) for start, finish in intervals)
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m {seconds % 60:02d}s"


def story_title(workspace: Path, delivery: dict[str, Any], progress: dict[str, Any]) -> str:
    embedded_title = str(progress.get("story_title") or delivery.get("story_title") or "").strip()
    if embedded_title:
        return embedded_title
    story_path = str(progress.get("story_path") or delivery.get("story_path") or "").strip()
    if not story_path:
        return ""
    configured_docs = Path(str(progress.get("docs_dir") or delivery.get("docs_dir") or workspace.parent)).expanduser()
    for docs_dir in dict.fromkeys((configured_docs, workspace.parent)):
        metadata = read_delivery_json(docs_dir / story_path / "metadata.json", {})
        title = str(metadata.get("title") or "").strip()
        if title:
            return title
    return ""


def feishu_notifications_enabled(workspace: Path) -> bool:
    common = load_json(workspace / "config" / "common.json", {})
    notifications = common.get("notifications") if isinstance(common.get("notifications"), dict) else {}
    feishu = notifications.get("feishu") if isinstance(notifications.get("feishu"), dict) else {}
    if "enabled" in feishu:
        return bool(feishu.get("enabled"))
    delivery = load_json(workspace / "config" / "delivery.json", {})
    delivery_notifications = delivery.get("notifications") if isinstance(delivery.get("notifications"), dict) else {}
    delivery_feishu = delivery_notifications.get("feishu") if isinstance(delivery_notifications.get("feishu"), dict) else {}
    if "enabled" in delivery_feishu:
        return bool(delivery_feishu.get("enabled"))
    return True


def save_feishu_notifications(workspace: Path, enabled: bool, *, push: bool = True, include_payload: bool = True) -> dict[str, Any]:
    for relative in ("config/common.json", "config/delivery.json"):
        path = workspace / relative
        config = load_json(path, {})
        notifications = config.setdefault("notifications", {})
        if not isinstance(notifications, dict):
            notifications = {}
            config["notifications"] = notifications
        feishu = notifications.setdefault("feishu", {})
        if not isinstance(feishu, dict):
            feishu = {}
            notifications["feishu"] = feishu
        feishu["enabled"] = enabled
        write_json(path, config)
    auto_commit_delivery_config(workspace, push=push)
    return workspace_payload(workspace) if include_payload else {"saved_at": utc_now()}


def save_deployment_config(workspace: Path, body: dict[str, Any], *, include_payload: bool = True) -> dict[str, Any]:
    provider = str(body.get("provider") or "none").strip().casefold()
    if provider not in {"none", "jenkins", "github_actions"}:
        raise ValueError("Deployment provider must be none, jenkins, or github_actions")
    try:
        poll_interval = max(5, min(3600, int(body.get("poll_interval_seconds") or 30)))
        timeout = max(60, min(7 * 24 * 3600, int(body.get("timeout_seconds") or 3600)))
    except (TypeError, ValueError) as exc:
        raise ValueError("Deployment polling values must be valid numbers") from exc
    jenkins = body.get("jenkins") if isinstance(body.get("jenkins"), dict) else {}
    github = body.get("github_actions") if isinstance(body.get("github_actions"), dict) else {}
    deployment = {
        "enabled": bool(body.get("enabled", False)) and provider != "none",
        "provider": provider,
        "poll_interval_seconds": poll_interval,
        "timeout_seconds": timeout,
        "jenkins": {
            "job": str(jenkins.get("job") or "").strip(),
            "url_env": str(jenkins.get("url_env") or "JENKINS_URL").strip() or "JENKINS_URL",
            "auth_env": str(jenkins.get("auth_env") or "JENKINS_AUTH").strip() or "JENKINS_AUTH",
        },
        "github_actions": {
            "repository": str(github.get("repository") or "").strip(),
            "workflow": str(github.get("workflow") or "").strip(),
            "gh_bin": str(github.get("gh_bin") or "gh").strip() or "gh",
        },
    }
    path = workspace / "config" / "delivery.json"
    config = load_json(path, {})
    config["deployment_tracking"] = deployment
    write_json(path, config)
    auto_commit_delivery_config(workspace, push=False)
    return workspace_payload(workspace) if include_payload else {"saved_at": utc_now()}


def delivery_stages(phases: object, deployment: object = None) -> list[dict[str, Any]]:
    source = [phase for phase in phases or [] if isinstance(phase, dict)]
    definitions = [
        ("preflight", "Preflight", {"preflight", "worktrees", "jira_start"}),
        ("implement", "Implement", {"agent"}),
        ("verification", "Verification", {"verification"}),
        ("pr", "PR", {"finalize", "jira_done"}),
        ("notification", "Notification", {"notify"}),
    ]
    stages: list[dict[str, Any]] = []
    for stage_id, label, phase_ids in definitions:
        matched = [phase for phase in source if str(phase.get("id") or "") in phase_ids]
        statuses = [str(phase.get("status") or "pending").lower() for phase in matched]
        if any(status in {"failed", "blocked"} for status in statuses):
            status = "failed"
        elif any(status in {"in_progress", "running"} for status in statuses):
            status = "in_progress"
        elif matched and all(status in {"completed", "skipped"} for status in statuses):
            status = "completed"
        else:
            status = "pending"
        interval_sets = [phase_intervals(phase) for phase in matched]
        intervals = [interval for values, _ in interval_sets for interval in values]
        starts = [start for start, _ in intervals]
        finishes = [finish for _, finish in intervals]
        all_attempts = [attempt for phase in matched for attempt in phase_attempt_records(phase)]
        started_at = min((start for start, _ in all_attempts), default=min(starts) if starts else None)
        started_at = started_at.isoformat().replace("+00:00", "Z") if started_at else ""
        finished_at = max(finishes).isoformat().replace("+00:00", "Z") if finishes else ""
        detail = " · ".join(dict.fromkeys(str(phase.get("detail") or "").strip() for phase in matched if phase.get("detail")))
        attempts = [
            {
                "number": index + 1,
                "started_at": start.isoformat().replace("+00:00", "Z"),
                "finished_at": finish.isoformat().replace("+00:00", "Z") if finish else "",
                "duration": delivery_duration(start, finish) if finish else "Running",
            }
            for index, (start, finish) in enumerate(all_attempts)
        ]
        stages.append({
            "id": stage_id,
            "label": label,
            "status": status,
            "started_at": started_at,
            "finished_at": finished_at,
            "duration": intervals_duration(intervals) if intervals else "—",
            "duration_kind": "active" if matched and all(has_attempts for _, has_attempts in interval_sets) else "span",
            "active_started_at": next((start.isoformat().replace("+00:00", "Z") for start, finish in reversed(all_attempts) if finish is None), ""),
            "attempts": attempts,
            "detail": detail,
        })
    if isinstance(deployment, dict) and deployment.get("provider"):
        status = str(deployment.get("status") or "queued").lower()
        if status in {"succeeded", "completed"}:
            stage_status = "completed"
        elif status in {"failed", "cancelled", "timeout"}:
            stage_status = "failed"
        else:
            stage_status = "in_progress"
        stages.append(
            {
                "id": "deployment",
                "label": "Deployment",
                "status": stage_status,
                "started_at": deployment.get("started_at", ""),
                "finished_at": deployment.get("finished_at", ""),
                "duration": "—",
                "duration_kind": "span",
                "active_started_at": deployment.get("started_at", "") if stage_status == "in_progress" else "",
                "attempts": [],
                "detail": " · ".join(
                    value for value in (
                        str(deployment.get("provider") or "").replace("_", " ").title(),
                        str(deployment.get("detail") or "").strip(),
                    ) if value
                ),
                "url": deployment.get("url", ""),
            }
        )
    return stages


def patch_stages(phases: object) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for phase in phases if isinstance(phases, list) else []:
        if not isinstance(phase, dict):
            continue
        result.append({
            "id": phase.get("id", ""),
            "label": phase.get("label", phase.get("id", "")),
            "status": phase.get("status", "pending"),
            "started_at": phase.get("started_at", ""),
            "finished_at": phase.get("finished_at", ""),
            "detail": phase.get("detail", ""),
        })
    return result


def patch_payload(workspace: Path) -> dict[str, Any]:
    history_root = workspace / "history" / "patch"
    runs: list[dict[str, Any]] = []
    latest_history_current: dict[str, Any] = {}
    if history_root.is_dir():
        for source in sorted(history_root.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)[:20]:
            item = read_delivery_json(source, {})
            patch = item.get("patch") if isinstance(item.get("patch"), dict) else item
            progress = item.get("progress") if isinstance(item.get("progress"), dict) else {}
            if not latest_history_current:
                latest_history_current = {**progress, **patch}
            runs.append({
                "run_id": item.get("run_id") or source.stem,
                "status": patch.get("patch_status") or progress.get("patch_status") or "unknown",
                "jira_key": patch.get("jira_key") or progress.get("jira_key") or "",
                "jira_summary": patch.get("jira_summary") or progress.get("jira_summary") or "",
                "summary": patch.get("summary") or progress.get("jira_summary") or "",
                "jira_type": progress.get("jira_type") or "",
                "jira_status": progress.get("jira_status") or "",
                "branch": progress.get("branch") or "",
                "repositories": patch.get("repos_touched") or progress.get("repositories") or [],
                "self_checks": patch.get("self_checks") or progress.get("self_checks") or [],
                "pr_urls": patch.get("pr_urls") or [],
                "commits": patch.get("commits") or [],
                "question": patch.get("question") or progress.get("question") or "",
                "started_at": progress.get("started_at") or patch.get("started_at") or "",
                "finished_at": patch.get("finished_at") or progress.get("finished_at") or "",
                "log_file": progress.get("log_file") or "",
            })
    progress = read_delivery_json(workspace / "results" / "patch-progress.json", {})
    result = read_delivery_json(workspace / "results" / "patch-result.json", {})
    if progress.get("run_id") and (not result or result.get("jira_key") == progress.get("jira_key")):
        current = {**progress, **result}
    else:
        current = progress or result
    current = dict(current)
    lock = workspace / "locks" / "patch-run"
    current["active"] = lock.exists()
    current_status = str(current.get("patch_status") or "").strip().casefold()
    if not current["active"] and latest_history_current and current_status in {"", "idle", "not_started"}:
        current = {**latest_history_current, "active": False}
    current["stages"] = patch_stages(current.get("phases"))
    activity_path = workspace / "state" / "patch-scheduler-activity.jsonl"
    activity: list[dict[str, Any]] = []
    if activity_path.is_file():
        for line in activity_path.read_text(encoding="utf-8", errors="replace").splitlines()[-10:]:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                activity.append(value)
    return {
        "current": current,
        "runs": runs,
        "scheduler_activity": list(reversed(activity)),
        "scheduler_log_available": (workspace / "logs" / "patch-schedule.log").is_file(),
        "config": read_delivery_json(workspace / "config" / "delivery.json", {}),
    }


def delivery_payload(workspace: Path) -> dict[str, Any]:
    history_dir = workspace / "history" / "delivery"
    runs: list[dict[str, Any]] = []
    if history_dir.is_dir():
        for source in sorted(history_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)[:20]:
            item = read_delivery_json(source, {})
            delivery = item.get("delivery") if isinstance(item.get("delivery"), dict) else {}
            progress = item.get("progress") if isinstance(item.get("progress"), dict) else {}
            touched = delivery.get("repos_touched") if isinstance(delivery.get("repos_touched"), list) else []
            pull_requests = [
                {"repository": str(repo.get("name") or "Repository"), "url": str(repo.get("pr_url"))}
                for repo in touched
                if isinstance(repo, dict) and str(repo.get("pr_url") or "").strip()
            ]
            if not pull_requests:
                pull_requests = [
                    {"repository": "Pull request", "url": str(url)}
                    for url in delivery.get("pr_urls") or []
                    if str(url).strip()
                ]
            runs.append(
                {
                    "run_id": item.get("run_id") or source.stem,
                    "status": delivery.get("delivery_status") or progress.get("delivery_status") or "unknown",
                    "story": delivery.get("story_id") or progress.get("story_id") or "",
                    "story_title": story_title(workspace, delivery, progress),
                    "jira_key": delivery.get("jira_key") or progress.get("jira_key") or "",
                    "branch": delivery.get("branch") or progress.get("branch") or "",
                    "pull_requests": pull_requests,
                    "verification": delivery.get("verification_results") or progress.get("verification") or [],
                    "started_at": progress.get("started_at") or delivery.get("started_at") or "",
                    "finished_at": progress.get("finished_at") or delivery.get("finished_at") or "",
                    "log_file": item.get("log_file") or progress.get("log_file") or "",
                    "agent_trace": delivery.get("agent_trace") or {},
                    "deployment": delivery.get("deployment") or {},
                }
            )
    progress = read_delivery_json(workspace / "results" / "delivery-progress.json", {})
    result = read_delivery_json(workspace / "results" / "delivery-result.json", {})
    terminal_states = {"completed", "failed", "blocked", "dev_done", "pr_open", "awaiting_deploy"}
    progress_run_id = str(progress.get("run_id") or "").strip()
    result_run_id = str(result.get("run_id") or "").strip()
    result_matches_progress = not progress_run_id or result_run_id == progress_run_id
    if progress_run_id and not result_run_id:
        result_matches_progress = bool(
            result.get("started_at") and result.get("started_at") == progress.get("started_at")
        )
    if str(result.get("delivery_status") or "") in terminal_states and (
        result_matches_progress
    ):
        current = {**progress, **result}
        current["started_at"] = progress.get("started_at") or result.get("started_at") or ""
        current["finished_at"] = result.get("finished_at") or progress.get("finished_at") or ""
        current["current_phase"] = "completed" if result.get("delivery_status") == "completed" else result.get("delivery_status")
        current["verification"] = result.get("verification_results") or progress.get("verification") or []
    else:
        current = progress
    active = delivery_process_active(workspace)
    if str(current.get("delivery_status") or "").lower() in {"in_progress", "running"} and not active:
        current = dict(current)
        current["delivery_status"] = "failed"
        current["finished_at"] = current.get("updated_at") or current.get("started_at") or ""
        current["current_step"] = "Delivery process is no longer running"
    remediation = read_delivery_json(workspace / "results" / "delivery-remediation.json", {})
    if not remediation and isinstance(result.get("remediation"), dict):
        remediation = result["remediation"]
    run_ids = {
        str(item.get("run_id") or "").strip()
        for item in (current, progress, result)
        if isinstance(item, dict) and str(item.get("run_id") or "").strip()
    }
    story_ids = {
        str(item.get(key) or "").strip()
        for item in (current, progress, result)
        for key in ("jira_key", "story_id", "story")
        if isinstance(item, dict) and str(item.get(key) or "").strip()
    }
    remediation_run_id = str(remediation.get("run_id") or "").strip() if isinstance(remediation, dict) else ""
    remediation_story_id = next(
        (str(remediation.get(key) or "").strip() for key in ("jira_key", "story_id", "story") if str(remediation.get(key) or "").strip()),
        "",
    ) if isinstance(remediation, dict) else ""
    remediation_matches = bool(
        remediation
        and ((remediation_run_id and remediation_run_id in run_ids) or (not remediation_run_id and remediation_story_id and remediation_story_id in story_ids))
    )
    if str(current.get("delivery_status") or "").lower() == "blocked" and str(current.get("current_step") or "").lower() == "stopped from dashboard":
        remediation_matches = False
    if remediation_matches:
        current["remediation"] = remediation
    if isinstance(result.get("agent_trace"), dict):
        current["agent_trace"] = result["agent_trace"]
    current["story_title"] = story_title(workspace, current, progress)
    current["stages"] = delivery_stages(current.get("phases"), current.get("deployment"))
    activity_path = workspace / "state" / "delivery-scheduler-activity.jsonl"
    activity: list[dict[str, Any]] = []
    if activity_path.is_file():
        for line in activity_path.read_text(encoding="utf-8", errors="replace").splitlines()[-5:]:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                activity.append(event)
    return {
        "current": current,
        "runs": runs,
        "available_stories": available_delivery_stories(workspace, current),
        "scheduler_activity": list(reversed(activity)),
        "scheduler_log_available": (workspace / "logs" / "delivery-schedule.log").is_file(),
        "config": read_delivery_json(workspace / "config" / "delivery.json", {}),
    }


def available_delivery_stories(workspace: Path, current: dict[str, Any]) -> list[dict[str, str]]:
    docs_dir = docs_dir_for_workspace(workspace, current)
    stories = docs_dir / "stories"
    if not stories.is_dir():
        return []
    result: list[dict[str, str]] = []
    for story_dir in sorted(item for item in stories.iterdir() if item.is_dir()):
        metadata = read_delivery_json(story_dir / "metadata.json", {})
        if str(metadata.get("businessStatus") or "").casefold() != "ready":
            continue
        if str(metadata.get("technicalStatus") or "").casefold() != "approved":
            continue
        if str(metadata.get("deliveryStatus") or "not_started").casefold() not in {"", "not_started", "blocked"}:
            continue
        result.append({"story": story_dir.name, "jira_key": str(metadata.get("jiraKey") or ""), "title": str(metadata.get("title") or "")})
    return result


def docs_dir_for_workspace(workspace: Path, current: dict[str, Any] | None = None) -> Path:
    current = current if isinstance(current, dict) else {}
    docs_value = str(current.get("docs_dir") or "").strip()
    if docs_value:
        return Path(docs_value).expanduser().resolve()
    workspace_config = load_json(workspace / "config" / "workspace.json", {})
    configured_root = str(workspace_config.get("workspace_root") or "").strip()
    root = Path(configured_root).expanduser().resolve() if configured_root else workspace.parent.resolve()
    docs_repo = str(workspace_config.get("docs_repo") or ".").strip() or "."
    docs_path = Path(docs_repo).expanduser()
    if docs_path.is_absolute():
        return docs_path.resolve()
    return (root / docs_path).resolve()


def safe_story_dir(docs_dir: Path, story_ref: str) -> Path:
    stories_root = (docs_dir / "stories").resolve()
    if not stories_root.is_dir():
        raise ValueError(f"Stories directory not found: {stories_root}")
    story_dir = find_story_dir(docs_dir, story_ref)
    try:
        story_dir.resolve().relative_to(stories_root)
    except ValueError as exc:
        raise ValueError("Invalid story path") from exc
    return story_dir.resolve()


def story_markdown_paths(story_dir: Path, metadata: dict[str, Any]) -> tuple[Path, Path]:
    story_md = story_dir / "story.md"
    plan_name = str(metadata.get("technicalPlanFile") or "technical-plan.md").strip() or "technical-plan.md"
    if "/" in plan_name or plan_name.startswith(".") or Path(plan_name).name != plan_name:
        raise ValueError("Invalid technical plan file name")
    return story_md, story_dir / plan_name


def story_date_value(metadata: dict[str, Any]) -> str:
    for key in ("updatedAt", "jiraPublishedAt", "jiraImportedAt"):
        value = str(metadata.get(key) or "").strip()
        if value:
            return value[:10]
    return ""


def story_created_at(story_dir: Path, metadata: dict[str, Any]) -> str:
    for key in ("createdAt", "jiraImportedAt", "jiraPublishedAt"):
        value = str(metadata.get(key) or "").strip()
        if value:
            return value
    try:
        stat = story_dir.stat()
        stamp = getattr(stat, "st_birthtime", None) or stat.st_ctime
        return datetime.fromtimestamp(float(stamp), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except OSError:
        return str(metadata.get("updatedAt") or "").strip()


def story_assignee_name(docs_dir: Path, metadata: dict[str, Any], story_dir: Path | None = None) -> str:
    direct = str(metadata.get("jiraAssignee") or metadata.get("assignee") or "").strip()
    if direct:
        return direct
    candidates: list[Path] = []
    snap = str(metadata.get("jiraSnapshotFile") or "").strip()
    if snap:
        candidates.append(docs_dir / snap)
    if story_dir is not None:
        candidates.append(workspace_lumen_dir(docs_dir) / "context" / story_dir.name / "jira-import.json")
    for path in candidates:
        resolved = path.resolve()
        try:
            resolved.relative_to(docs_dir.resolve())
        except ValueError:
            continue
        if not resolved.is_file():
            continue
        payload = load_json(resolved, {})
        workitem = payload.get("workitem")
        if isinstance(workitem, list):
            workitem = workitem[0] if workitem else {}
        if not isinstance(workitem, dict):
            continue
        assignee = workitem.get("assignee")
        if isinstance(assignee, dict):
            name = str(assignee.get("displayName") or assignee.get("display_name") or assignee.get("name") or "").strip()
            if name:
                return name
        if isinstance(assignee, str) and assignee.strip():
            return assignee.strip()
    return ""


def list_observatory_stories(workspace: Path) -> list[dict[str, Any]]:
    docs_dir = docs_dir_for_workspace(workspace)
    stories = docs_dir / "stories"
    if not stories.is_dir():
        return []
    result: list[dict[str, Any]] = []
    for story_dir in (item for item in stories.iterdir() if item.is_dir()):
        metadata = read_delivery_json(story_dir / "metadata.json", {})
        created = story_created_at(story_dir, metadata)
        result.append(
            {
                "story": story_dir.name,
                "title": str(metadata.get("title") or story_dir.name),
                "jira_key": str(metadata.get("jiraKey") or ""),
                "jira_url": str(metadata.get("jiraUrl") or ""),
                "businessStatus": str(metadata.get("businessStatus") or ""),
                "technicalStatus": str(metadata.get("technicalStatus") or ""),
                "deliveryStatus": str(metadata.get("deliveryStatus") or "not_started"),
                "createdAt": created,
                "updatedAt": story_date_value(metadata),
                "assignee": story_assignee_name(docs_dir, metadata, story_dir),
            }
        )
    result.sort(
        key=lambda item: (
            str(item.get("updatedAt") or ""),
            str(item.get("createdAt") or ""),
            str(item.get("story") or ""),
        ),
        reverse=True,
    )
    return result


def observatory_story_content(workspace: Path, story_ref: str) -> dict[str, Any]:
    docs_dir = docs_dir_for_workspace(workspace)
    story_dir = safe_story_dir(docs_dir, story_ref)
    metadata = read_delivery_json(story_dir / "metadata.json", {})
    story_md, plan_md = story_markdown_paths(story_dir, metadata)
    return {
        "story": story_dir.name,
        "title": str(metadata.get("title") or story_dir.name),
        "jira_key": str(metadata.get("jiraKey") or ""),
        "jira_url": str(metadata.get("jiraUrl") or ""),
        "businessStatus": str(metadata.get("businessStatus") or ""),
        "technicalStatus": str(metadata.get("technicalStatus") or ""),
        "deliveryStatus": str(metadata.get("deliveryStatus") or "not_started"),
        "metadata": metadata,
        "story_markdown": story_md.read_text(encoding="utf-8") if story_md.is_file() else "",
        "plan_markdown": plan_md.read_text(encoding="utf-8") if plan_md.is_file() else "",
        "plan_path": plan_md.name,
        "story_path": "story.md",
    }


def save_observatory_story_content(workspace: Path, story_ref: str, story_markdown: str, plan_markdown: str) -> dict[str, Any]:
    docs_dir = docs_dir_for_workspace(workspace)
    story_dir = safe_story_dir(docs_dir, story_ref)
    metadata = read_delivery_json(story_dir / "metadata.json", {})
    story_md, plan_md = story_markdown_paths(story_dir, metadata)
    story_md.write_text(str(story_markdown).rstrip() + "\n", encoding="utf-8")
    plan_md.write_text(str(plan_markdown).rstrip() + "\n", encoding="utf-8")
    ticket = str(metadata.get("jiraKey") or metadata.get("storyId") or story_dir.name).strip() or "N/A"
    subject = lumen_commit_subject(ticket, f"update {ticket} story docs")
    relative_paths = [
        str(story_md.relative_to(docs_dir)),
        str(plan_md.relative_to(docs_dir)),
    ]
    commit = commit_paths(docs_dir, relative_paths, subject, push=True)
    return {"ok": True, "story": story_dir.name, "commit": commit, "subject": subject}


def trace_directory(workspace: Path, run_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
        raise ValueError("Invalid trace id")
    for candidate in (
        workspace / "results" / "agent-traces" / run_id,
        workspace / "history" / "delivery" / run_id / "agent-trace",
    ):
        if (candidate / "trace.json").is_file():
            return candidate
    raise ValueError("Agent trace is no longer available")


def capped_text(path: Path, maximum: int = 65536) -> tuple[str, bool]:
    try:
        data = path.read_bytes()
    except OSError:
        return "", False
    truncated = len(data) > maximum
    return data[-maximum:].decode("utf-8", errors="replace"), truncated


def capped_ndjson(path: Path, maximum: int = 500) -> list[dict[str, Any]]:
    text_value, _ = capped_text(path, 512 * 1024)
    events: list[dict[str, Any]] = []
    for line in text_value.splitlines()[-maximum:]:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


_AGENT_ACTIVITY_PROFILES = {
    "dylan": {"display_name": "Dylan", "role": "scan", "workflow": "auto_scan"},
    "mark": {"display_name": "Mark", "role": "delivery", "workflow": "auto_delivery"},
    "irving": {"display_name": "Irving", "role": "patch", "workflow": "auto_patch"},
    "milchick": {"display_name": "Milchick", "role": "orchestrator", "workflow": "manager"},
}
_ACTIVITY_TIMELINE_EVENTS = {
    "conversation.request",
    "conversation.completed",
    "agent.prompt.composed",
    "agent.jira.shortcut",
    "agent.run.started",
    "agent.result.completed",
    "security.action_requests.executed",
    "reply.succeeded",
    "reply.failed",
    "job.failed",
}


def _activity_log_index(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    traces: dict[str, dict[str, Any]] = {}
    outbound: dict[str, dict[str, Any]] = {}
    for agent_id, profile in _AGENT_ACTIVITY_PROFILES.items():
        for record in capped_ndjson(root / f"{agent_id}.jsonl", 5000):
            trace_id = str(record.get("trace_id") or "").strip()
            if trace_id:
                traces.setdefault(trace_id, {**profile, "agent_id": agent_id})
                traces[trace_id].update({key: record[key] for key in ("role", "workflow", "project_slug") if record.get(key)})
        for record in capped_ndjson(root / f"{agent_id}_outbound.jsonl", 5000):
            reply_to = str(record.get("reply_to") or "").strip()
            if reply_to:
                outbound[reply_to] = record
    return traces, outbound


def agent_activity_payload(project: str, limit: int = 240) -> dict[str, Any]:
    """Return a small, local-only conversation read model for the dashboard."""
    try:
        from risk.store import global_db_path

        database = global_db_path()
    except Exception as exc:
        return {"available": False, "items": [], "detail": str(exc)}
    if not database.is_file():
        return {"available": False, "items": [], "detail": "No Agent conversation store has been created yet."}

    try:
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        traces = connection.execute(
            """
            SELECT * FROM conversation_trace
            WHERE (? = '' OR project_slug = ? OR COALESCE(project_slug, '') = '')
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (str(project or ""), str(project or ""), max(1, min(int(limit), 240))),
        ).fetchall()
        total = int(connection.execute(
            """
            SELECT COUNT(*) FROM conversation_trace
            WHERE (? = '' OR project_slug = ? OR COALESCE(project_slug, '') = '')
            """,
            (str(project or ""), str(project or "")),
        ).fetchone()[0] or 0)
        log_index, outbound_index = _activity_log_index(database.parent)
        items: list[dict[str, Any]] = []
        for trace in traces:
            trace_id = str(trace["trace_id"] or "")
            raw_events = connection.execute(
                "SELECT event, payload_json, created_at FROM conversation_event WHERE trace_id = ? ORDER BY id ASC",
                (trace_id,),
            ).fetchall()
            events: list[dict[str, Any]] = []
            profile = dict(log_index.get(trace_id, {}))
            request_text = ""
            response_text = ""
            prompt_text = ""
            action = ""
            outcome = str(trace["state"] or "unknown")
            for row in raw_events:
                try:
                    payload = json.loads(row["payload_json"] or "{}")
                except (TypeError, json.JSONDecodeError):
                    payload = {}
                if not isinstance(payload, dict):
                    payload = {}
                profile.update({key: payload[key] for key in ("agent_id", "role", "workflow", "project_slug") if payload.get(key)})
                if row["event"] == "conversation.request":
                    request_text = str(payload.get("text") or "")[:4000]
                if row["event"] == "agent.prompt.composed":
                    prompt_text = str(payload.get("prompt") or "")[:20000]
                if row["event"] in {"conversation.completed", "conversation.result"}:
                    response_text = str(payload.get("text") or payload.get("response_text") or "")[:4000]
                    action = str(payload.get("action") or action)
                    outcome = str(payload.get("status") or outcome)
                elif row["event"] == "agent.jira.shortcut":
                    outcome = str(payload.get("status") or outcome)
                if row["event"] in _ACTIVITY_TIMELINE_EVENTS:
                    detail = str(payload.get("detail") or payload.get("error") or payload.get("action") or "").strip()
                    events.append({"event": row["event"], "at": row["created_at"], "detail": detail})

            outbound = outbound_index.get(str(trace["message_id"] or ""), {})
            if not response_text:
                response_text = str(outbound.get("text") or "")[:4000]
            agent_id = str(profile.get("agent_id") or "").strip().lower()
            fallback = _AGENT_ACTIVITY_PROFILES.get(agent_id, {})
            profile = {**fallback, **profile}
            source = "conversation" if request_text and response_text else "outcome" if response_text else "trace"
            items.append(
                {
                    "trace_id": trace_id,
                    "message_id": str(trace["message_id"] or ""),
                    "agent_id": agent_id,
                    "display_name": str(profile.get("display_name") or agent_id.title() or "Agent"),
                    "role": str(profile.get("role") or "agent"),
                    "workflow": str(profile.get("workflow") or ""),
                    "project_slug": str(trace["project_slug"] or project or ""),
                    "status": outcome,
                    "action": action,
                    "request_text": request_text,
                    "response_text": response_text,
                    "prompt_text": prompt_text,
                    "source": source,
                    "started_at": str(trace["started_at"] or ""),
                    "completed_at": str(trace["completed_at"] or ""),
                    "latency_ms": trace["latency_ms"],
                    "event_count": len(raw_events),
                    "timeline": events[-12:],
                }
            )
        connection.close()
        return {"available": True, "items": items, "count": len(items), "total": total}
    except (OSError, sqlite3.Error, ValueError) as exc:
        return {"available": False, "items": [], "detail": f"Unable to read Agent activity: {exc}"}


def delivery_trace_payload(workspace: Path, run_id: str) -> dict[str, Any]:
    root = trace_directory(workspace, run_id)
    trace = read_delivery_json(root / "trace.json", {})
    invocations = []
    for summary in trace.get("invocations", []):
        if not isinstance(summary, dict):
            continue
        invocation_id = str(summary.get("invocation_id") or "")
        if not re.fullmatch(r"[A-Za-z0-9._-]+", invocation_id):
            continue
        directory = root / "agents" / invocation_id
        stdout, stdout_truncated = capped_text(directory / "stdout.log")
        stderr, stderr_truncated = capped_text(directory / "stderr.log")
        prompt, prompt_truncated = capped_text(directory / "prompt.md", 100 * 1024)
        output, output_truncated = capped_text(directory / "final-output.md", 100 * 1024)
        invocations.append({
            **summary,
            "request": read_delivery_json(directory / "request.json", {}),
            "result": read_delivery_json(directory / "result.json", {}),
            "context_manifest": read_delivery_json(directory / "context-manifest.json", {}),
            "changed_files": read_delivery_json(directory / "changed-files.json", {}),
            "events": capped_ndjson(directory / "events.ndjson"),
            "prompt": prompt,
            "stdout": stdout,
            "stderr": stderr,
            "final_output": output,
            "truncated": {"prompt": prompt_truncated, "stdout": stdout_truncated, "stderr": stderr_truncated, "final_output": output_truncated},
        })
    return {"trace": trace, "spans": capped_ndjson(root / "spans.ndjson", 200), "invocations": invocations, "local_evidence": True}


class DashboardServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], workspace: Path, project: str, lumen_bin: str, lumen_home: str):
        super().__init__(address, DashboardHandler)
        self.workspace = workspace
        self.project = project
        self.lumen_bin = lumen_bin
        self.lumen_home = lumen_home

    def project_context(self, slug: str | None = None) -> tuple[Path, str, list[dict[str, Any]]]:
        registry = load_registry()
        entries = [
            {"name": str(entry.get("name") or entry.get("slug") or "Workspace"), "slug": str(entry.get("slug") or ""), "workspace": str(entry.get("workspace") or "")}
            for entry in registry.get("projects", [])
            if str(entry.get("slug") or "") and (Path(str(entry.get("workspace") or "")) / "config" / "common.json").is_file()
        ]
        selected = find_by_slug(registry, slug) if slug else None
        if selected and (Path(str(selected.get("workspace") or "")) / "config" / "common.json").is_file():
            return Path(str(selected["workspace"])).resolve(), str(selected["slug"]), entries
        return self.workspace, self.project, entries

    def dashboard_state(self, slug: str | None = None) -> dict[str, Any]:
        workspace, project, projects = self.project_context(slug)
        data = RENDERER.build_payload(workspace)
        agents_payload: dict[str, Any] = {"enabled": False, "agents": []}
        try:
            from agents.soul_store import agents_settings_payload

            agents_payload = agents_settings_payload(project=project)
        except Exception:
            pass

        data["interactive"] = {
            "enabled": True,
            "project": project,
            "projects": projects,
            "prompts": prompt_files(workspace),
            "schedules": schedule_payload(workspace, project),
            "workspace": workspace_payload(workspace),
            "agents": agents_payload,
        }
        data["delivery"] = delivery_payload(workspace)
        data["patch"] = patch_payload(workspace)
        data["activity"] = agent_activity_payload(project)
        return data

    def delivery_log(self, workspace: Path, run_id: str) -> dict[str, Any]:
        payload = delivery_payload(workspace)
        current = payload.get("current") if isinstance(payload.get("current"), dict) else {}
        selected = current if not run_id or run_id == current.get("run_id") else next(
            (item for item in payload.get("runs", []) if isinstance(item, dict) and item.get("run_id") == run_id),
            {},
        )
        log_value = str(selected.get("log_file") or "").strip()
        if not log_value:
            raise ValueError("No delivery log is available")
        log_file = Path(log_value).expanduser()
        try:
            log_file.resolve().relative_to(workspace.resolve())
        except ValueError as exc:
            raise ValueError("Invalid delivery log path") from exc
        if not log_file.is_file():
            raise ValueError("Delivery log is no longer available")
        lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        return {"run_id": selected.get("run_id", ""), "path": str(log_file.relative_to(workspace)), "content": "\n".join(lines[-220:])}

    def delivery_scheduler_log(self, workspace: Path) -> dict[str, Any]:
        log_file = workspace / "logs" / "delivery-schedule.log"
        if not log_file.is_file():
            raise ValueError("No scheduler log is available yet")
        lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        return {"path": str(log_file.relative_to(workspace)), "content": "\n".join(lines[-220:])}

    def patch_log(self, workspace: Path, run_id: str) -> dict[str, Any]:
        payload = patch_payload(workspace)
        current = payload.get("current") if isinstance(payload.get("current"), dict) else {}
        selected = current if not run_id or run_id == current.get("run_id") else next((item for item in payload.get("runs", []) if item.get("run_id") == run_id), {})
        log_value = str(selected.get("log_file") or "").strip()
        if not log_value:
            candidates = sorted((workspace / "logs" / "patch").glob("run-*.log"), key=lambda path: path.stat().st_mtime, reverse=True)
            log_value = str(candidates[0]) if candidates else ""
        if not log_value:
            raise ValueError("No Auto Patch log is available")
        path = Path(log_value).expanduser().resolve()
        try:
            path.relative_to(workspace.resolve())
        except ValueError as exc:
            raise ValueError("Invalid Auto Patch log path") from exc
        if not path.is_file():
            raise ValueError("Auto Patch log is no longer available")
        return {"run_id": selected.get("run_id", ""), "path": str(path.relative_to(workspace)), "content": "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-220:])}

    def patch_scheduler_log(self, workspace: Path) -> dict[str, Any]:
        path = workspace / "logs" / "patch-schedule.log"
        if not path.is_file():
            raise ValueError("No Auto Patch scheduler log is available yet")
        return {"path": str(path.relative_to(workspace)), "content": "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-220:])}

    def patch_candidates(self, workspace: Path) -> dict[str, Any]:
        # The interactive server is started with the visible lumen directory,
        # while Auto Patch runtime helpers expect the docs repository root.
        candidate_workspace = workspace
        if not (workspace / "stories").is_dir() and (workspace.parent / "stories").is_dir():
            candidate_workspace = workspace.parent
        return {"candidates": patch_candidate_options(candidate_workspace)}

    def start_patch(self, workspace: Path, project: str, jira_key: str = "") -> dict[str, Any]:
        if (workspace / "locks" / "patch-run").exists():
            raise RuntimeError("An Auto Patch run is already active")
        command = [self.lumen_bin, "patch", "run", "--project", project]
        if jira_key.strip():
            command.extend(["--jira-key", jira_key.strip()])
        subprocess.Popen(command, cwd=str(workspace), env=dict(os.environ, LUMEN_HOME=self.lumen_home), start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"project": project, "jira_key": jira_key.strip(), "started_at": utc_now()}

    def stop_patch(self, workspace: Path) -> dict[str, Any]:
        pid_path = workspace / "locks" / "patch-run" / "pid"
        if not pid_path.is_file():
            raise ValueError("No active Auto Patch run was found")
        pid = int(pid_path.read_text(encoding="utf-8").strip())
        terminate_process_tree(pid)
        return {"pid": pid, "stopped_at": utc_now()}

    def retry_delivery(self, workspace: Path, story_override: str = "") -> dict[str, Any]:
        progress = read_delivery_json(workspace / "results" / "delivery-progress.json", {})
        status = str(progress.get("delivery_status") or "").lower()
        active = delivery_process_active(workspace)
        if status in {"in_progress", "running"} and not active:
            status = "failed"
        current_story = str(progress.get("story_id") or progress.get("jira_key") or "").strip()
        story_ref = str(story_override or current_story).strip()
        retryable = {"failed", "blocked", "not_started", ""}
        same_story = bool(story_ref) and bool(current_story) and story_ref.casefold() == current_story.casefold()
        if status not in retryable and (not story_override or same_story):
            raise ValueError("Only a stopped, failed, blocked, or not-started delivery can be started")
        if (workspace / "locks" / "delivery-run").exists():
            raise RuntimeError("A delivery run is already active")
        docs_value = str(progress.get("docs_dir") or "").strip()
        if docs_value:
            docs_dir = Path(docs_value).expanduser().resolve()
        else:
            workspace_config = load_json(workspace / "config" / "workspace.json", {})
            docs_dir = Path(str(workspace_config.get("docs_repo") or workspace.parent)).expanduser().resolve()
        if not story_ref or workspace_lumen_dir(docs_dir).resolve() != workspace.resolve():
            raise ValueError("The failed delivery does not have a retryable workspace and story")
        context = load_story_context(docs_dir, story_ref, validate_gates=False)
        delivery_config = load_json(workspace / "config" / "delivery.json", {})
        jira_config = jira_delivery_config(delivery_config)
        jira_enabled, _ = should_sync_jira(delivery_config)
        reset_status = str(
            ((delivery_config.get("automation") or {}).get("scheduled_delivery") or {}).get("required_jira_status") or "Ready for Dev"
        ).strip()
        if jira_enabled and context.metadata.get("jiraKey") and reset_status:
            refreshed, reason = refresh_twg_auth(force=True)
            if not refreshed:
                raise RuntimeError(reason)
            transition_issue(str(context.metadata["jiraKey"]), reset_status, jira_config)
            add_delivery_comment(str(context.metadata["jiraKey"]), "Lumen Delivery · Reset\n\n- Failed run reset; a new delivery run will start.", jira_config)
        cleaned = cleanup_delivery_worktrees(docs_dir, story_ref)
        metadata = load_json(context.metadata_path, {})
        metadata["deliveryStatus"] = "not_started"
        metadata["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        metadata["deliveryResetAt"] = utc_now()
        for key in ("deliveryBranch", "prUrl", "jira_pr_url"):
            metadata.pop(key, None)
        write_json(context.metadata_path, metadata)
        try:
            commit_story_metadata(docs_dir, story_ref, push=True)
        except Exception:
            pass
        env = dict(os.environ, LUMEN_HOME=self.lumen_home)
        subprocess.Popen(
            [self.lumen_bin, "delivery", "run", str(docs_dir), "--story", story_ref],
            cwd=docs_dir, env=env, start_new_session=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return {"story": story_ref, "started_at": utc_now(), "worktrees": cleaned, "jira_status": reset_status if jira_enabled else "unchanged"}

    def start_scan(self, workspace: Path, project: str) -> dict[str, Any]:
        lock = workspace / "state" / "run.lock"
        if lock.exists():
            raise RuntimeError("A scan is already active for this project")
        env = dict(os.environ, LUMEN_HOME=self.lumen_home)
        subprocess.Popen(
            [self.lumen_bin, "scan", "--project", project],
            cwd=workspace,
            env=env,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {"ok": True, "project": project}

    def stop_delivery(self, workspace: Path) -> dict[str, Any]:
        lock = workspace / "locks" / "delivery-run"
        pid_path = lock / "pid"
        if not pid_path.is_file():
            raise ValueError("No active delivery run was found")
        try:
            pid = int(pid_path.read_text(encoding="utf-8").strip())
        except ValueError as exc:
            raise ValueError("Delivery process id is invalid") from exc
        terminate_process_tree(pid)
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except OSError:
                break
            time.sleep(0.05)

        progress_path = workspace / "results" / "delivery-progress.json"
        progress = read_delivery_json(progress_path, {})
        finished_at = utc_now()
        for phase in progress.get("phases") or []:
            if not isinstance(phase, dict) or str(phase.get("status") or "").lower() not in {"in_progress", "running"}:
                continue
            phase["status"] = "blocked"
            phase["finished_at"] = finished_at
            phase["detail"] = "Stopped from Dashboard"
            attempts = phase.get("attempts")
            if isinstance(attempts, list) and attempts and isinstance(attempts[-1], dict) and not attempts[-1].get("finished_at"):
                attempts[-1]["finished_at"] = finished_at
        progress["delivery_status"] = "blocked"
        progress["current_step"] = "Stopped from Dashboard"
        progress["finished_at"] = finished_at
        progress["updated_at"] = progress["finished_at"]
        write_json(progress_path, progress)
        try:
            delivery_config = load_json(workspace / "config" / "delivery.json", {})
            jira_enabled, _ = should_sync_jira(delivery_config)
            jira_key = str(progress.get("jira_key") or "").strip()
            blocked_status = str(jira_delivery_config(delivery_config).get("blocked_status") or "Block").strip()
            if jira_enabled and jira_key and blocked_status:
                refreshed, _ = refresh_twg_auth(force=True)
                if refreshed:
                    transition_issue(jira_key, blocked_status, jira_delivery_config(delivery_config))
        except Exception:
            pass

        docs_value = str(progress.get("docs_dir") or "").strip()
        if docs_value:
            docs_dir = Path(docs_value).expanduser().resolve()
        else:
            workspace_config = load_json(workspace / "config" / "workspace.json", {})
            docs_dir = Path(str(workspace_config.get("docs_repo") or workspace.parent)).expanduser().resolve()
        story_ref = str(progress.get("story_id") or progress.get("jira_key") or "").strip()
        cleaned: list[str] = []
        if story_ref and workspace_lumen_dir(docs_dir).resolve() == workspace.resolve():
            cleaned = cleanup_delivery_worktrees(docs_dir, story_ref)
        story_path = str(progress.get("story_path") or "").strip()
        if story_path:
            metadata_path = (docs_dir / story_path / "metadata.json").resolve()
            metadata = read_delivery_json(metadata_path, {})
            if metadata:
                metadata["deliveryStatus"] = "blocked"
                metadata["updatedAt"] = finished_at[:10]
                logs = metadata.get("logs") if isinstance(metadata.get("logs"), list) else []
                logs.append({"type": "delivery.run", "at": finished_at, "status": "blocked", "result": "stopped"})
                metadata["logs"] = logs[-20:]
                write_json(metadata_path, metadata)
                try:
                    commit_story_metadata(docs_dir, story_ref, push=True)
                except Exception:
                    pass

        result = {
            "schema_version": "1.0",
            "run_id": progress.get("run_id", ""),
            "delivery_status": "blocked",
            "current_step": "Stopped from Dashboard",
            "story_id": progress.get("story_id", ""),
            "story_path": progress.get("story_path", ""),
            "jira_key": progress.get("jira_key", ""),
            "docs_dir": progress.get("docs_dir", str(docs_dir)),
            "workspace_root": progress.get("workspace_root", str(workspace)),
            "branch": progress.get("branch", ""),
            "started_at": progress.get("started_at", ""),
            "finished_at": finished_at,
            "verification_results": progress.get("verification", []),
            "repos_touched": progress.get("repositories", []),
            "pr_urls": [],
            "publish_mode": "none",
            "failures": [{"label": "Stopped from Dashboard", "summary": "Delivery was stopped by the user before completion."}],
        }
        result_path = workspace / "results" / "delivery-result.json"
        write_json(result_path, result)
        archive_script = SCRIPT_DIR / "archive_delivery_run.py"
        if archive_script.is_file():
            subprocess.run([
                sys.executable, str(archive_script), "--workspace-root", str(docs_dir),
                "--result", str(result_path), "--progress", str(progress_path),
                "--log-file", str(progress.get("log_file") or ""),
            ], capture_output=True, text=True, check=False)
        shutil.rmtree(lock, ignore_errors=True)
        return {"pid": pid, "story": story_ref, "worktrees": cleaned}

    def delete_delivery_history(self, workspace: Path, run_id: str) -> dict[str, Any]:
        if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
            raise ValueError("Invalid delivery run id")
        current = delivery_payload(workspace).get("current") or {}
        if run_id == str(current.get("run_id") or "") and (workspace / "locks" / "delivery-run").exists():
            raise ValueError("The active delivery cannot be deleted")
        history_json = workspace / "history" / "delivery" / f"{run_id}.json"
        if not history_json.is_file():
            raise ValueError("Delivery history record was not found")
        item = read_delivery_json(history_json, {})
        removed: list[str] = []
        log_value = str(item.get("log_file") or "").strip()
        if log_value:
            log_path = Path(log_value).expanduser()
            try:
                log_path.resolve().relative_to(workspace.resolve())
                if log_path.is_file():
                    log_path.unlink()
                    removed.append(str(log_path))
            except ValueError:
                pass
        for path in (
            history_json,
            workspace / "history" / "delivery" / run_id,
            workspace / "results" / "agent-traces" / run_id,
        ):
            if path.is_dir():
                shutil.rmtree(path)
                removed.append(str(path))
            elif path.is_file():
                path.unlink()
                removed.append(str(path))
        return {"run_id": run_id, "removed": removed}

    def delete_patch_history(self, workspace: Path, run_id: str) -> dict[str, Any]:
        if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
            raise ValueError("Invalid patch run id")
        current = patch_payload(workspace).get("current") or {}
        if run_id == str(current.get("run_id") or "") and (workspace / "locks" / "patch-run").exists():
            raise ValueError("The active Auto Patch cannot be deleted")
        history_json = workspace / "history" / "patch" / f"{run_id}.json"
        if not history_json.is_file():
            raise ValueError("Patch history record was not found")
        item = read_delivery_json(history_json, {})
        progress = item.get("progress") if isinstance(item.get("progress"), dict) else {}
        patch = item.get("patch") if isinstance(item.get("patch"), dict) else item
        removed: list[str] = []
        log_value = str(progress.get("log_file") or patch.get("log_file") or item.get("log_file") or "").strip()
        if log_value:
            log_path = Path(log_value).expanduser()
            try:
                log_path.resolve().relative_to(workspace.resolve())
                if log_path.is_file():
                    log_path.unlink()
                    removed.append(str(log_path))
            except ValueError:
                pass
        history_json.unlink()
        removed.append(str(history_json))
        return {"run_id": run_id, "removed": removed}

    def update_observability(self, workspace: Path, body: dict[str, Any]) -> dict[str, Any]:
        mode = str(body.get("capture_mode") or "").strip().lower()
        if mode not in {"off", "metadata", "full"}:
            raise ValueError("Capture mode must be off, metadata, or full")
        retention = int(body.get("retention_days", 14))
        if retention < 1 or retention > 3650:
            raise ValueError("Retention must be between 1 and 3650 days")
        path = workspace / "config" / "delivery.json"
        config = load_json(path, {})
        observability = config.setdefault("observability", {})
        if not isinstance(observability, dict):
            raise ValueError("Invalid observability configuration")
        observability["agent_trace"] = {"enabled": mode != "off", "capture_mode": mode, "retention_days": retention}
        write_json(path, config)
        auto_commit_delivery_config(workspace)
        return observability["agent_trace"]

    def update_schedule(self, body: dict[str, Any], workspace: Path, project: str, *, push: bool = True) -> dict[str, Any]:
        kind = str(body.get("kind", ""))
        action = str(body.get("action", ""))
        if kind not in {"scan", "delivery", "patch"} or action not in {"save", "remove"}:
            raise ValueError("Invalid schedule request")
        if action == "remove":
            func = remove_scan_schedule if kind == "scan" else remove_delivery_schedule if kind == "delivery" else remove_patch_schedule
            func(argparse.Namespace(project=project))
            if kind == "delivery":
                config_path = workspace / "config" / "delivery.json"
                config = load_json(config_path, {})
                automation = config.setdefault("automation", {})
                scheduled = automation.setdefault("scheduled_delivery", {})
                scheduled["enabled"] = False
                write_json(config_path, config)
                auto_commit_delivery_config(workspace, push=push)
            if kind == "patch":
                config_path = workspace / "config" / "delivery.json"
                config = load_json(config_path, {})
                config.setdefault("automation", {}).setdefault("scheduled_auto_patch", {})["enabled"] = False
                write_json(config_path, config)
                auto_commit_delivery_config(workspace, push=push)
            return schedule_payload(workspace, project)

        if kind == "scan":
            cron = str(body.get("cron", "")).strip()
            if not cron:
                raise ValueError("A scan cron expression is required")
            args = argparse.Namespace(
                project=project,
                cron=cron,
                lumen_bin=self.lumen_bin,
                lumen_home=self.lumen_home,
                path=os.environ.get("PATH", ""),
                log_file=str(workspace / "logs" / "schedule.log"),
                dry_run=False,
            )
            if install_scan_schedule(args) != 0:
                raise RuntimeError("Unable to install scan schedule")
        elif kind == "delivery":
            interval = int(body.get("interval_minutes", 0))
            if interval < 1:
                raise ValueError("Delivery interval must be at least one minute")
            raw_jira_statuses = body.get("jira_statuses", body.get("jira_status"))
            jira_statuses = normalize_statuses(raw_jira_statuses, ())
            if not jira_statuses:
                raise ValueError("Select at least one eligible JIRA status")
            jira_status = jira_statuses[0]
            in_dev_status = str(body.get("in_dev_status", "")).strip()
            dev_done_status = str(body.get("dev_done_status", "")).strip()
            blocked_status = str(body.get("blocked_status", "Block")).strip() or "Block"
            args = argparse.Namespace(
                project=project,
                cron=f"*/{interval} * * * *",
                jira_statuses=jira_statuses,
                lumen_bin=self.lumen_bin,
                lumen_home=self.lumen_home,
                path=os.environ.get("PATH", ""),
                log_file=str(workspace / "logs" / "delivery-schedule.log"),
            )
            if install_delivery_schedule(args) != 0:
                raise RuntimeError("Unable to install delivery schedule")
            config_path = workspace / "config" / "delivery.json"
            config = load_json(config_path, {})
            automation = config.setdefault("automation", {})
            scheduled = automation.setdefault("scheduled_delivery", {})
            scheduled.update({"enabled": True, "eligible_jira_statuses": jira_statuses, "required_jira_status": jira_status})
            jira = config.setdefault("jira", {})
            if in_dev_status:
                jira["in_dev_status"] = in_dev_status
            if dev_done_status:
                jira["dev_done_status"] = dev_done_status
            jira["blocked_status"] = blocked_status
            write_json(config_path, config)
            auto_commit_delivery_config(workspace, push=push)
        else:
            interval = int(body.get("interval_minutes", 0))
            if interval < 1:
                raise ValueError("Auto Patch interval must be at least one minute")
            if not str(workspace_jira_config(workspace).get("project_key") or "").strip():
                raise ValueError("Configure the shared Jira project key in config/common.json before enabling Auto Patch")
            statuses = normalize_statuses(body.get("jira_statuses", body.get("jira_status")), ("To Do",))
            types = normalize_statuses(body.get("issue_types"), ("Task", "Bug"))
            args = argparse.Namespace(
                project=project,
                cron=f"*/{interval} * * * *",
                lumen_bin=self.lumen_bin,
                lumen_home=self.lumen_home,
                path=os.environ.get("PATH", ""),
                log_file=str(workspace / "logs" / "patch-schedule.log"),
            )
            if install_patch_schedule(args) != 0:
                raise RuntimeError("Unable to install Auto Patch schedule")
            config_path = workspace / "config" / "delivery.json"
            config = load_json(config_path, {})
            scheduled = config.setdefault("automation", {}).setdefault("scheduled_auto_patch", {})
            scheduled.update({"enabled": True, "poll_interval_minutes": interval, "eligible_jira_statuses": statuses, "issue_types": types})
            for key in ("in_progress_status", "done_status", "blocked_status"):
                value = str(body.get(key, "")).strip()
                if value:
                    scheduled[key] = value
            write_json(config_path, config)
            auto_commit_delivery_config(workspace, push=push)
        return schedule_payload(workspace, project)


class DashboardHandler(SimpleHTTPRequestHandler):
    server: DashboardServer

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        workspace, project, _ = self.server.project_context(query.get("project", [""])[0])
        if parsed.path == "/api/state":
            return self.respond_json(HTTPStatus.OK, self.server.dashboard_state(project))
        if parsed.path == "/api/agents":
            try:
                from agents.soul_store import agents_settings_payload

                return self.respond_json(HTTPStatus.OK, agents_settings_payload(network=True, project=project))
            except Exception as exc:
                return self.respond_error(HTTPStatus.BAD_REQUEST, str(exc))
        if parsed.path == "/api/prompt":
            try:
                path = safe_prompt_path(workspace, query.get("mode", [""])[0], query.get("path", [""])[0])
                return self.respond_json(HTTPStatus.OK, {"content": path.read_text(encoding="utf-8")})
            except (OSError, ValueError) as exc:
                return self.respond_error(HTTPStatus.BAD_REQUEST, str(exc))
        if parsed.path == "/api/integration":
            try:
                key = query.get("key", [""])[0]
                return self.respond_json(HTTPStatus.OK, {"key": key, "value": integration_value(workspace, key)})
            except (OSError, ValueError) as exc:
                return self.respond_error(HTTPStatus.BAD_REQUEST, str(exc))
        if parsed.path == "/api/delivery/log":
            try:
                return self.respond_json(HTTPStatus.OK, self.server.delivery_log(workspace, query.get("run_id", [""])[0]))
            except (OSError, ValueError) as exc:
                return self.respond_error(HTTPStatus.BAD_REQUEST, str(exc))
        if parsed.path == "/api/delivery/scheduler-log":
            try:
                return self.respond_json(HTTPStatus.OK, self.server.delivery_scheduler_log(workspace))
            except ValueError as exc:
                return self.respond_error(HTTPStatus.BAD_REQUEST, str(exc))
        if parsed.path == "/api/delivery/trace":
            try:
                return self.respond_json(HTTPStatus.OK, delivery_trace_payload(workspace, query.get("run_id", [""])[0]))
            except (OSError, ValueError) as exc:
                return self.respond_error(HTTPStatus.BAD_REQUEST, str(exc))
        if parsed.path == "/api/delivery/status-options":
            return self.respond_json(HTTPStatus.OK, jira_status_options(workspace))
        if parsed.path == "/api/patch/log":
            try:
                return self.respond_json(HTTPStatus.OK, self.server.patch_log(workspace, query.get("run_id", [""])[0]))
            except (OSError, ValueError) as exc:
                return self.respond_error(HTTPStatus.BAD_REQUEST, str(exc))
        if parsed.path == "/api/patch/scheduler-log":
            try:
                return self.respond_json(HTTPStatus.OK, self.server.patch_scheduler_log(workspace))
            except ValueError as exc:
                return self.respond_error(HTTPStatus.BAD_REQUEST, str(exc))
        if parsed.path == "/api/patch/trace":
            try:
                return self.respond_json(HTTPStatus.OK, self.server.patch_log(workspace, query.get("run_id", [""])[0]))
            except (OSError, ValueError) as exc:
                return self.respond_error(HTTPStatus.BAD_REQUEST, str(exc))
        if parsed.path == "/api/patch/candidates":
            try:
                return self.respond_json(HTTPStatus.OK, self.server.patch_candidates(workspace))
            except (OSError, RuntimeError, ValueError) as exc:
                return self.respond_error(HTTPStatus.BAD_REQUEST, str(exc))
        if parsed.path == "/api/stories":
            return self.respond_json(HTTPStatus.OK, {"stories": list_observatory_stories(workspace)})
        if parsed.path == "/api/stories/content":
            try:
                return self.respond_json(HTTPStatus.OK, observatory_story_content(workspace, query.get("story", [""])[0]))
            except (OSError, ValueError, FileNotFoundError) as exc:
                return self.respond_error(HTTPStatus.BAD_REQUEST, str(exc))
        if parsed.path in {"/", "/dashboard.html", "/overview", "/activity", "/scan", "/delivery", "/patch", "/repositories", "/prompts", "/settings", "/observatory"}:
            return self.serve_file(self.server.workspace / "dashboard.html", "text/html; charset=utf-8")
        if parsed.path == "/dashboard-data.js":
            return self.serve_file(self.server.workspace / "dashboard-data.js", "application/javascript; charset=utf-8")
        if parsed.path == "/assets/lumon-mark.png":
            return self.serve_file(self.server.workspace / "assets" / "lumon-mark.png", "image/png")
        try:
            path = safe_workspace_static_path(workspace, parsed.path)
        except ValueError:
            return self.respond_error(HTTPStatus.NOT_FOUND, "Not found")
        content_type, _ = mimetypes.guess_type(path.name)
        return self.serve_file(path, content_type or "application/octet-stream")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            body = self.read_json_body()
            workspace, project, _ = self.server.project_context(str(body.get("project", "")))
            if parsed.path == "/api/issue/ignore":
                issue_id = str(body.get("issue_id", "")).strip()
                if not issue_id:
                    raise ValueError("Issue id is required")
                reason = str(body.get("reason", "")).strip()
                issue = set_issue_status(workspace, issue_id, "ignored", reason)
                risk_db = workspace / "risk" / "risk.sqlite3"
                if risk_db.is_file():
                    if str(LIB_DIR) not in sys.path:
                        sys.path.insert(0, str(LIB_DIR))
                    from risk.lifecycle import upsert_ignore_policy
                    from risk.store import RiskStore

                    store = RiskStore(workspace)
                    try:
                        risk_finding_id = str(issue.get("risk_finding_id") or "").strip()
                        finding = store.get_finding(risk_finding_id) if risk_finding_id else None
                        if finding is None:
                            finding = store.fetchone(
                                "SELECT * FROM finding WHERE registry_issue_id = ? LIMIT 1",
                                (issue_id,),
                            )
                        if finding is not None:
                            finding_id = str(finding["id"] or "")
                            upsert_ignore_policy(
                                store,
                                finding_id,
                                ignored_by="dashboard",
                                reason=reason,
                            )
                            store.insert_event(
                                finding_id,
                                "ignored",
                                previous_status=str(finding["status"] or ""),
                                new_status="Ignored",
                                actor_type="user",
                                actor_id="dashboard",
                                reason=reason,
                            )
                            store.commit()
                    finally:
                        store.close()
                return self.respond_json(HTTPStatus.OK, {"issue": issue})
            if parsed.path == "/api/schedule":
                return self.respond_json(HTTPStatus.OK, {"schedules": self.server.update_schedule(body, workspace, project, push=False)})
            if parsed.path == "/api/agents":
                from agents.soul_store import apply_agent_settings

                return self.respond_json(HTTPStatus.OK, apply_agent_settings(body))
            if parsed.path == "/api/prompt":
                path = safe_prompt_path(workspace, str(body.get("mode", "")), str(body.get("path", "")))
                if not path.is_file():
                    raise ValueError("Prompt file does not exist")
                path.write_text(str(body.get("content", "")).rstrip() + "\n", encoding="utf-8")
                return self.respond_json(HTTPStatus.OK, {"saved_at": utc_now()})
            if parsed.path == "/api/stories/content":
                story = str(body.get("story") or "").strip()
                if not story:
                    raise ValueError("Story is required")
                return self.respond_json(
                    HTTPStatus.OK,
                    save_observatory_story_content(
                        workspace,
                        story,
                        str(body.get("story_markdown") or ""),
                        str(body.get("plan_markdown") or ""),
                    ),
                )
            if parsed.path == "/api/workspace":
                days = int(body.get("scan_window_days", 0))
                if days < 1 or days > 365:
                    raise ValueError("Scan window must be between 1 and 365 days")
                path = workspace / "config" / "common.json"
                config = load_json(path, {})
                execution = config.setdefault("execution", {})
                if not isinstance(execution, dict):
                    raise ValueError("Invalid workspace execution configuration")
                execution["scan_window_days"] = days
                workflow_providers = {"codex", "codex_cli", "codex-cli", "cursor_cli", "cursor", "cursor-cli", "opencode", "opencode_deepseek", "deepseek", "deepseek_api", "openai", "openai_compatible", "openai-compatible"}

                def apply_model_config(target: dict[str, Any], body_prefix: str, file_prefix: str = "") -> None:
                    provider = str(body.get(f"{body_prefix}provider") or "").strip()
                    model = str(body.get(f"{body_prefix}model") or "").strip()
                    if provider:
                        if provider not in workflow_providers:
                            raise ValueError(f"Unsupported workflow AI provider: {provider}")
                        target[f"{file_prefix}provider"] = dashboard_provider(provider)
                    if model:
                        target[f"{file_prefix}model"] = model
                    for suffix in ("base_url", "api_key_env", "reasoning_effort", "account_email"):
                        key = f"{body_prefix}{suffix}"
                        if key in body:
                            target[f"{file_prefix}{suffix}"] = str(body.get(key) or "").strip()

                global_model_keys = ("ai_provider", "ai_model", "ai_base_url", "ai_api_key_env", "ai_reasoning_effort", "ai_account_email")
                has_global_model = any(key in body for key in global_model_keys)
                if has_global_model:
                    apply_model_config(execution, "ai_")
                else:
                    # Compatibility for clients released before the global
                    # model center. New clients only send ai_* fields.
                    apply_model_config(execution, "scan_")
                    if "scan_model" in body:
                        execution["model"] = str(body.get("scan_model") or "").strip()
                write_json(path, config)
                delivery_model = str(body.get("delivery_model") or "").strip()
                patch_model = str(body.get("patch_model") or "").strip()
                has_legacy_delivery_model = delivery_model or patch_model or any(key in body for key in ("delivery_provider", "delivery_base_url", "delivery_api_key_env", "patch_provider", "patch_base_url", "patch_api_key_env"))
                if has_global_model or has_legacy_delivery_model:
                    delivery_path = workspace / "config" / "delivery.json"
                    delivery = load_json(delivery_path, {})
                    delivery_execution = delivery.setdefault("execution", {})
                    if not isinstance(delivery_execution, dict):
                        raise ValueError("Invalid delivery execution configuration")
                    if has_global_model:
                        for key in ("provider", "model", "base_url", "api_key_env", "reasoning_effort", "account_email"):
                            if key in execution:
                                delivery_execution[key] = execution[key]
                                delivery_execution[f"patch_{key}"] = execution[key]
                    else:
                        apply_model_config(delivery_execution, "delivery_")
                        apply_model_config(delivery_execution, "patch_", "patch_")
                        if delivery_model:
                            delivery_execution["model"] = delivery_model
                        if patch_model:
                            delivery_execution["patch_model"] = patch_model
                    write_json(delivery_path, delivery)
                if "feishu_notifications_enabled" in body:
                    save_feishu_notifications(workspace, bool(body.get("feishu_notifications_enabled")), push=False, include_payload=False)
                else:
                    auto_commit_delivery_config(workspace, push=False)
                return self.respond_json(HTTPStatus.OK, {"saved_at": utc_now()})
            if parsed.path == "/api/deployment-config":
                return self.respond_json(
                    HTTPStatus.OK,
                    {"workspace": save_deployment_config(workspace, body, include_payload=False)},
                )
            if parsed.path == "/api/integration":
                update_env_value(workspace, str(body.get("key", "")).strip(), str(body.get("value", "")))
                return self.respond_json(HTTPStatus.OK, {"saved_at": utc_now()})
            if parsed.path == "/api/git-sync/force":
                commit = force_push_conflict(workspace / "state")
                return self.respond_json(HTTPStatus.OK, {"ok": True, "commit": commit, "workspace": workspace_payload(workspace)})
            if parsed.path == "/api/repositories":
                return self.respond_json(HTTPStatus.OK, {"workspace": save_repositories(workspace, body.get("repositories"), include_payload=False)})
            if parsed.path == "/api/repositories/clone":
                return self.respond_json(HTTPStatus.OK, {"workspace": clone_repository(workspace, body.get("url"), include_payload=False)})
            if parsed.path == "/api/repository/verification":
                return self.respond_json(
                    HTTPStatus.OK,
                    {"workspace": save_delivery_steps(workspace, body.get("repository"), body.get("commands"), include_payload=False)},
                )
            if parsed.path == "/api/publish-policy":
                return self.respond_json(
                    HTTPStatus.OK,
                    {"workspace": save_publish_policy(workspace, body.get("scan_mode"), body.get("delivery_mode"), body.get("patch_mode", "pr"), push=False, include_payload=False)},
                )
            if parsed.path == "/api/observability":
                return self.respond_json(HTTPStatus.OK, {"agent_trace": self.server.update_observability(workspace, body)})
            if parsed.path == "/api/scan/start":
                return self.respond_json(HTTPStatus.ACCEPTED, {"scan": self.server.start_scan(workspace, project)})
            if parsed.path == "/api/patch/start":
                return self.respond_json(HTTPStatus.ACCEPTED, {"patch": self.server.start_patch(workspace, project, str(body.get("jira_key") or ""))})
            if parsed.path == "/api/patch/stop":
                return self.respond_json(HTTPStatus.ACCEPTED, {"patch": self.server.stop_patch(workspace)})
            if parsed.path == "/api/patch/history/delete":
                return self.respond_json(HTTPStatus.OK, {"patch": self.server.delete_patch_history(workspace, str(body.get("run_id") or ""))})
            if parsed.path == "/api/delivery/retry":
                return self.respond_json(HTTPStatus.ACCEPTED, {"delivery": self.server.retry_delivery(workspace)})
            if parsed.path == "/api/delivery/start":
                payload = delivery_payload(workspace)
                current = payload.get("current") or {}
                status = str(current.get("delivery_status") or "").lower()
                current_ref = str(current.get("story_id") or current.get("jira_key") or "").strip()
                story = str(body.get("story") or "").strip() or current_ref
                candidates = payload.get("available_stories") or []
                if status in {"completed", "success"} and (
                    not story or story.casefold() == current_ref.casefold()
                ):
                    story = next(
                        (
                            str(item.get("story") or item.get("jira_key") or "").strip()
                            for item in candidates
                            if str(item.get("story") or item.get("jira_key") or "").strip().casefold()
                            != current_ref.casefold()
                        ),
                        "",
                    )
                    if not story:
                        raise ValueError("Current delivery already completed; no other ready story to start")
                if not story:
                    story = str(candidates[0].get("story") or "") if candidates else ""
                return self.respond_json(HTTPStatus.ACCEPTED, {"delivery": self.server.retry_delivery(workspace, story)})
            if parsed.path == "/api/delivery/stop":
                return self.respond_json(HTTPStatus.OK, {"delivery": self.server.stop_delivery(workspace)})
            if parsed.path == "/api/delivery/history/delete":
                return self.respond_json(HTTPStatus.OK, {"delivery": self.server.delete_delivery_history(workspace, str(body.get("run_id") or ""))})
            return self.respond_error(HTTPStatus.NOT_FOUND, "Not found")
        except (OSError, ValueError, RuntimeError) as exc:
            return self.respond_error(HTTPStatus.BAD_REQUEST, str(exc))

    def read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        if not isinstance(payload, dict):
            raise ValueError("Request body must be an object")
        return payload

    def respond_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def respond_error(self, status: HTTPStatus, message: str) -> None:
        self.respond_json(status, {"error": message})

    def serve_file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            return self.respond_error(HTTPStatus.NOT_FOUND, "Not found")
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--lumen-bin", required=True)
    parser.add_argument("--lumen-home", required=True)
    parser.add_argument("--port", type=int, default=4173)
    parser.add_argument("--version", default="")
    args = parser.parse_args()

    os.environ.setdefault("LUMEN_HOME", str(Path(args.lumen_home).expanduser().resolve()))
    try:
        from feishu.config import ensure_lumen_env_loaded

        ensure_lumen_env_loaded()
    except Exception:
        pass

    workspace = Path(args.workspace).expanduser().resolve()
    server = DashboardServer(("127.0.0.1", args.port), workspace, args.project, args.lumen_bin, args.lumen_home)
    url = f"http://127.0.0.1:{server.server_port}/"
    state_path = workspace / "state" / "dashboard-server.json"
    write_json(state_path, {"pid": os.getpid(), "url": url, "started_at": utc_now(), "version": args.version})
    print(url, flush=True)
    try:
        server.serve_forever()
    finally:
        if state_path.exists() and load_json(state_path, {}).get("pid") == os.getpid():
            state_path.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
