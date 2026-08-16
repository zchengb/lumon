#!/usr/bin/env python3
"""Auto Patch configuration, Jira candidates, worktrees, and bounded state."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from delivery_workspace import (
    discover_git_repos,
    load_workspace_config,
    read_json,
    repos_container_dir,
    resolve_repo_default_branch,
    workspace_lumen_dir,
    write_json,
)
from jira_sync import parse_twg_json, refresh_twg_auth, resolve_active_sprint, run_twg, site_args, twg_ready, workspace_jira_config


DEFAULT_PATCH_STATUSES = ("To Do",)
DEFAULT_PATCH_TYPES = ("Task", "Bug")
DEFAULT_PATCH_TRIGGER_LABEL = "lumon-auto-patch"
PATCH_PHASES = (
    ("capture", "Capture"),
    ("screen", "Initial screening"),
    ("context", "Jira context"),
    ("repository", "Repository mapping"),
    ("agent", "Patch agent"),
    ("self_check", "Self-check"),
    ("publish", "Publish"),
    ("jira_notify", "Jira & Feishu"),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def patch_dir(workspace: Path) -> Path:
    return workspace_lumen_dir(workspace) / "patch"


def results_dir(workspace: Path) -> Path:
    return workspace_lumen_dir(workspace) / "results"


def logs_dir(workspace: Path) -> Path:
    return workspace_lumen_dir(workspace) / "logs" / "patch"


def history_dir(workspace: Path) -> Path:
    return workspace_lumen_dir(workspace) / "history" / "patch"


def progress_path(workspace: Path) -> Path:
    return results_dir(workspace) / "patch-progress.json"


def result_path(workspace: Path) -> Path:
    return results_dir(workspace) / "patch-result.json"


def registry_path(workspace: Path) -> Path:
    return workspace_lumen_dir(workspace) / "state" / "patch-registry.json"


def load_delivery_config(workspace: Path) -> dict[str, Any]:
    return read_json(workspace_lumen_dir(workspace) / "config" / "delivery.json", {})


def patch_config(workspace: Path) -> dict[str, Any]:
    config = load_delivery_config(workspace).get("automation", {})
    patch = config.get("scheduled_auto_patch", {}) if isinstance(config, dict) else {}
    return patch if isinstance(patch, dict) else {}


def jira_config(workspace: Path) -> dict[str, Any]:
    return workspace_jira_config(workspace)


def publish_mode(workspace: Path) -> str:
    publish = load_delivery_config(workspace).get("publish", {})
    patch = publish.get("auto_patch", {}) if isinstance(publish, dict) else {}
    mode = str(patch.get("mode", "pr") if isinstance(patch, dict) else "pr").strip().lower()
    return mode if mode in {"pr", "direct"} else "pr"


def normalize_values(value: Any, fallback: tuple[str, ...]) -> list[str]:
    values = value if isinstance(value, (list, tuple, set)) else [value]
    result: list[str] = []
    for item in values:
        for part in str(item or "").split(","):
            item_value = part.strip()
            if item_value and item_value.casefold() not in {entry.casefold() for entry in result}:
                result.append(item_value)
    return result or list(fallback)


def eligible_statuses(workspace: Path) -> list[str]:
    return normalize_values(patch_config(workspace).get("eligible_jira_statuses"), DEFAULT_PATCH_STATUSES)


def issue_types(workspace: Path) -> list[str]:
    return normalize_values(patch_config(workspace).get("issue_types"), DEFAULT_PATCH_TYPES)


def trigger_label(workspace: Path) -> str:
    """Only cards explicitly marked for Auto Patch enter the scheduled queue."""
    return str(patch_config(workspace).get("required_label") or DEFAULT_PATCH_TRIGGER_LABEL).strip()


def blocked_statuses(workspace: Path) -> list[str]:
    configured = str(patch_config(workspace).get("blocked_status", "Block")).strip() or "Block"
    statuses = [configured]
    if not configured.casefold().endswith("(migrated)"):
        statuses.append(f"{configured} (migrated)")
    return list(dict.fromkeys(statuses))


def quote_jql_values(values: list[str]) -> str:
    return ", ".join('"' + value.replace('"', '\\"') + '"' for value in values)


def candidate_jql(workspace: Path, sprint_id: str, include_blocked: bool = False, require_trigger: bool = True) -> str:
    sprint_id = str(sprint_id or "").strip()
    if not sprint_id.isdigit():
        raise ValueError("Auto Patch requires a numeric active sprint ID")
    statuses = eligible_statuses(workspace)
    if include_blocked:
        statuses = [*statuses, *blocked_statuses(workspace)]
    label = trigger_label(workspace)
    escaped_label = label.replace('"', '\\"')
    trigger = f' AND labels = "{escaped_label}"' if require_trigger and escaped_label else ""
    return f"project = {jira_config(workspace).get('project_key', '')} AND sprint = {sprint_id} AND issuetype in ({quote_jql_values(issue_types(workspace))}) AND status in ({quote_jql_values(statuses)}){trigger} ORDER BY priority DESC, updated ASC"


def unwrap_jira(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        payload = payload["data"]
    if isinstance(payload, dict) and isinstance(payload.get("issues"), list):
        return payload["issues"]
    return payload


def jira_key(item: dict[str, Any]) -> str:
    return str(item.get("key") or item.get("id") or "").strip().upper()


def jira_fields(item: dict[str, Any]) -> dict[str, Any]:
    fields = item.get("fields")
    return fields if isinstance(fields, dict) else item


def jira_summary(item: dict[str, Any]) -> str:
    fields = jira_fields(item)
    return str(fields.get("summary") or item.get("summary") or "").strip()


def jira_status(item: dict[str, Any]) -> str:
    status = jira_fields(item).get("status")
    return str(status.get("name") if isinstance(status, dict) else status or "").strip()


def jira_updated(item: dict[str, Any]) -> str:
    return str(jira_fields(item).get("updated") or item.get("updated") or "").strip()


def query_candidates(workspace: Path, include_blocked: bool = False, require_trigger: bool = True) -> list[dict[str, Any]]:
    config = jira_config(workspace)
    if not config.get("project_key"):
        raise RuntimeError("Jira project_key is not configured")
    ready, reason = twg_ready()
    if not ready:
        raise RuntimeError(reason)
    refreshed, reason = refresh_twg_auth(force=True)
    if not refreshed:
        raise RuntimeError(reason)
    sprint_id, _ = resolve_active_sprint(config)
    if not sprint_id:
        raise RuntimeError("No active sprint found for the configured Jira board")
    jql = candidate_jql(workspace, sprint_id, include_blocked, require_trigger=require_trigger)
    code, output = run_twg(["jira", "workitem", "query", "--jql", jql, "--limit", "50", "-o", "json", *site_args(config)])
    if code != 0:
        raise RuntimeError((output or "Jira candidate query failed").strip()[-1000:])
    payload = unwrap_jira(parse_twg_json(output) or [])
    return [item for item in payload if isinstance(item, dict) and jira_key(item)] if isinstance(payload, list) else []


def get_workitem(workspace: Path, key: str) -> dict[str, Any]:
    ready, reason = twg_ready()
    if not ready:
        raise RuntimeError(reason)
    code, output = run_twg(["jira", "workitem", "get", key, "--full", "--comments", "-o", "json", *site_args(jira_config(workspace))])
    if code != 0:
        raise RuntimeError((output or f"Unable to read Jira {key}").strip()[-1000:])
    payload = unwrap_jira(parse_twg_json(output) or {})
    if isinstance(payload, list):
        payload = next((item for item in payload if isinstance(item, dict)), {})
    return payload if isinstance(payload, dict) else {}


def load_registry(workspace: Path) -> dict[str, Any]:
    payload = read_json(registry_path(workspace), {})
    payload.setdefault("issues", {})
    return payload


def save_registry(workspace: Path, payload: dict[str, Any]) -> None:
    write_json(registry_path(workspace), payload)


def comment_fingerprint(comment: Any) -> str:
    return hashlib.sha256(json.dumps(comment, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def comments(item: dict[str, Any]) -> list[Any]:
    fields = jira_fields(item)
    sources = (fields.get("comment"), fields.get("comments"), item.get("comments"), item.get("comment"))
    for raw in sources:
        if isinstance(raw, dict):
            raw = raw.get("comments") or raw.get("content") or []
        if isinstance(raw, list) and raw:
            return raw
    return []


def timestamp_after(value: str, boundary: str) -> bool:
    if not boundary or not value:
        return True
    try:
        parsed_value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        parsed_boundary = datetime.fromisoformat(boundary.replace("Z", "+00:00"))
        if parsed_value.tzinfo is None:
            parsed_value = parsed_value.replace(tzinfo=timezone.utc)
        if parsed_boundary.tzinfo is None:
            parsed_boundary = parsed_boundary.replace(tzinfo=timezone.utc)
        return parsed_value.astimezone(timezone.utc) > parsed_boundary.astimezone(timezone.utc)
    except ValueError:
        return value > boundary


def has_external_reply(item: dict[str, Any], record: dict[str, Any]) -> bool:
    question_at = str(record.get("blocked_at") or "")
    question_hash = str(record.get("question_hash") or "")
    for comment in comments(item):
        if not isinstance(comment, dict):
            continue
        body = json.dumps(comment, ensure_ascii=False)
        if "Lumen Auto Patch" in body:
            continue
        created = str(comment.get("created") or comment.get("createdAt") or "")
        fingerprint = comment_fingerprint(comment)
        if fingerprint == question_hash:
            continue
        if not timestamp_after(created, question_at):
            continue
        return True
    return False


def patch_candidate_options(workspace: Path) -> list[dict[str, Any]]:
    """Return selectable Task/Bug cards from the current active sprint."""
    registry = load_registry(workspace).get("issues", {})
    registry = registry if isinstance(registry, dict) else {}
    registered = repo_registry(workspace)
    def enabled(repo: dict[str, Any]) -> bool:
        automation = repo.get("automation") if isinstance(repo.get("automation"), dict) else {}
        patch = automation.get("patch") if isinstance(automation.get("patch"), dict) else {}
        return bool(patch.get("enabled", True))

    repositories_enabled = not registered or any(enabled(repo) for repo in registered)
    options: list[dict[str, Any]] = []
    for candidate in query_candidates(workspace, include_blocked=True):
        key = jira_key(candidate)
        record = registry.get(key, {}) if isinstance(registry.get(key, {}), dict) else {}
        item = candidate
        current_status = jira_status(candidate)
        blocked = current_status.casefold() in {status.casefold() for status in blocked_statuses(workspace)}
        if blocked or record.get("status") == "blocked":
            try:
                item = get_workitem(workspace, key)
                current_status = jira_status(item)
            except RuntimeError:
                item = candidate
        updated = jira_updated(item)
        if record.get("status") in {"completed", "skipped"} and record.get("updated") == updated:
            continue
        waiting_for_reply = (
            current_status.casefold() in {status.casefold() for status in blocked_statuses(workspace)}
            or record.get("status") == "blocked"
        )
        available = repositories_enabled
        reason = ""
        if not repositories_enabled:
            available = False
            reason = "Auto Patch is disabled for every registered repository."
        elif waiting_for_reply:
            if has_external_reply(item, record):
                reason = "New Jira reply detected; ready to retry."
            else:
                available = False
                reason = "Waiting for a new external Jira reply."
        fields = jira_fields(item)
        issue_type = fields.get("issuetype")
        issue_type = issue_type.get("name") if isinstance(issue_type, dict) else issue_type
        priority = fields.get("priority")
        priority = priority.get("name") if isinstance(priority, dict) else priority
        options.append({
            "jira_key": key,
            "summary": jira_summary(item),
            "issue_type": str(issue_type or "").strip(),
            "status": current_status,
            "priority": str(priority or "").strip(),
            "updated": updated,
            "available": available,
            "reason": reason,
        })
    return options


def repo_registry(workspace: Path) -> list[dict[str, Any]]:
    config_path = workspace_lumen_dir(workspace) / "config" / "repos.json"
    payload = read_json(config_path, {"repositories": []})
    entries = payload.get("repositories") if isinstance(payload.get("repositories"), list) else []
    result = []
    for item in entries:
        if not isinstance(item, dict) or not str(item.get("name", "")).strip():
            continue
        path = Path(str(item.get("path", ""))).expanduser()
        if not path.is_absolute():
            path = workspace / path
        if path.is_dir():
            result.append({**item, "path": str(path.resolve())})
    if result:
        return result
    workspace_config = load_workspace_config(workspace)[1]
    discovered = discover_git_repos(workspace, workspace_config)
    container = repos_container_dir(workspace, workspace_config)
    return [{"name": name, "path": str(path), "default_branch": resolve_repo_default_branch(name, path, workspace)} for name, path in discovered.items() if path.is_relative_to(container) or path.parent == workspace]


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:60] or "patch"


def patch_branch(key: str, summary: str) -> str:
    return f"patch/{key}-{slugify(summary)}"


def patch_worktree_path(workspace: Path, key: str, repo_name: str) -> Path:
    return patch_dir(workspace) / key / repo_name


def prepare_worktree(workspace: Path, key: str, summary: str, repo: dict[str, Any]) -> dict[str, Any]:
    source = Path(str(repo.get("path"))).expanduser().resolve()
    name = str(repo.get("name")).strip()
    base = str(repo.get("default_branch") or "").strip()
    if not base:
        base = resolve_repo_default_branch(name, source, workspace)
    destination = patch_worktree_path(workspace, key, name).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        status = subprocess.run(["git", "-C", str(destination), "status", "--porcelain"], capture_output=True, text=True, check=False)
        if status.returncode != 0 or status.stdout.strip():
            raise RuntimeError(f"Patch worktree is unavailable or dirty: {destination}")
        return {"name": name, "source_path": str(source), "worktree_path": str(destination), "branch": patch_branch(key, summary), "default_branch": base}
    fetch = subprocess.run(["git", "-C", str(source), "fetch", "origin", base], capture_output=True, text=True, check=False)
    if fetch.returncode != 0:
        raise RuntimeError((fetch.stderr or fetch.stdout or f"Unable to fetch origin/{base}").strip())
    branch = patch_branch(key, summary)
    created = subprocess.run(["git", "-C", str(source), "worktree", "add", "-B", branch, str(destination), f"origin/{base}"], capture_output=True, text=True, check=False)
    if created.returncode != 0:
        raise RuntimeError((created.stderr or created.stdout or "Unable to create patch worktree").strip())
    return {"name": name, "source_path": str(source), "worktree_path": str(destination), "branch": branch, "default_branch": base}


def remove_worktrees(repositories: list[dict[str, Any]]) -> None:
    for repo in repositories:
        source = str(repo.get("source_path") or "")
        worktree = str(repo.get("worktree_path") or "")
        if source and worktree:
            subprocess.run(["git", "-C", source, "worktree", "remove", "--force", worktree], capture_output=True, text=True, check=False)
    for repo in repositories:
        path = Path(str(repo.get("worktree_path") or ""))
        if path.parent.is_dir() and not any(path.parent.iterdir()):
            shutil.rmtree(path.parent, ignore_errors=True)


def empty_progress() -> dict[str, Any]:
    return {"schema_version": "1.0", "run_id": "", "patch_status": "not_started", "current_phase": "", "current_step": "", "jira_key": "", "jira_summary": "", "jira_type": "", "jira_status": "", "model": "", "branch": "", "repositories": [], "started_at": "", "updated_at": "", "finished_at": "", "phases": [], "self_checks": [], "question": "", "failures": [], "jira": {}, "feishu": {}, "messages": []}


def new_progress(run_id: str, item: dict[str, Any], workspace: Path) -> dict[str, Any]:
    fields = jira_fields(item)
    payload = empty_progress()
    payload.update({"run_id": run_id, "patch_status": "in_progress", "jira_key": jira_key(item), "jira_summary": jira_summary(item), "jira_type": str(fields.get("issuetype", {}).get("name") if isinstance(fields.get("issuetype"), dict) else fields.get("issuetype") or ""), "jira_status": jira_status(item), "started_at": utc_now(), "updated_at": utc_now()})
    payload["phases"] = [{"id": phase_id, "label": label, "status": "pending", "started_at": "", "finished_at": "", "detail": ""} for phase_id, label in PATCH_PHASES]
    return payload


def save_progress(workspace: Path, payload: dict[str, Any]) -> None:
    payload["updated_at"] = utc_now()
    write_json(progress_path(workspace), payload)


def set_phase(workspace: Path, payload: dict[str, Any], phase_id: str, status: str, detail: str = "") -> None:
    now = utc_now()
    for phase in payload.get("phases", []):
        if phase.get("id") != phase_id:
            continue
        phase["status"] = status
        phase["detail"] = detail or phase.get("detail", "")
        if status == "in_progress":
            phase["started_at"] = phase.get("started_at") or now
        elif status in {"completed", "failed", "blocked", "skipped"}:
            phase["started_at"] = phase.get("started_at") or now
            phase["finished_at"] = now
        break
    payload["current_phase"] = phase_id
    payload["current_step"] = detail
    if status == "in_progress":
        payload["patch_status"] = "in_progress"
    elif status in {"failed", "blocked"}:
        payload["patch_status"] = status
    save_progress(workspace, payload)
