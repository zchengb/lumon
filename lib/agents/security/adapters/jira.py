from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from agents.security.actions import ActionRequest
from agents.security.errors import CapabilityDenied, ResourceDenied

_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def _workspace_root(project_slug: str) -> Path | None:
    from agents.project_resolver import resolve_project

    project = resolve_project(slug=project_slug)
    if not project or not project.get("workspace"):
        return None
    workspace = Path(str(project["workspace"])).expanduser().resolve()
    parent = workspace.parent
    if (parent / "stories").is_dir() or (parent / "lumen" / "config" / "common.json").is_file():
        return parent
    if (workspace / "stories").is_dir() or (workspace / "config" / "common.json").is_file():
        return workspace
    for child in workspace.iterdir() if workspace.is_dir() else []:
        if child.is_dir() and ((child / "stories").is_dir() or (child / "config" / "common.json").is_file()):
            return child
    return workspace


def _jira_config(project_slug: str) -> dict[str, Any]:
    from jira_sync import workspace_jira_config

    root = _workspace_root(project_slug)
    if root is None:
        return {}
    cfg = workspace_jira_config(root)
    return cfg if isinstance(cfg, dict) else {}


def _labels_arg(value: Any) -> str:
    if isinstance(value, list):
        return ",".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def _create_workitem(request: ActionRequest) -> dict[str, Any]:
    from jira_sync import jira_browse_url_from_config, parse_issue_key, run_twg, site_args, truncate_error, twg_ready

    args = request.arguments if isinstance(request.arguments, dict) else {}
    resource = request.resource if isinstance(request.resource, dict) else {}
    summary = str(args.get("summary") or resource.get("summary") or "").strip()
    if not summary:
        raise ResourceDenied("summary required")
    description = str(args.get("description") or resource.get("description") or "").strip()
    target_version = str(args.get("target_version") or resource.get("target_version") or "").strip()
    if target_version and "target version" not in description.casefold():
        description = f"{description}\n\nTarget version: {target_version}".strip()
    cfg = _jira_config(str(request.project_slug or "").strip())
    project_key = str(
        args.get("project_key") or args.get("space") or resource.get("project_key") or cfg.get("project_key") or ""
    ).strip()
    if not project_key:
        raise ResourceDenied("project_key required (set notifications.jira.project_key)")
    issue_type = str(args.get("issue_type") or args.get("type") or cfg.get("issue_type") or "Bug").strip() or "Bug"
    ready, reason = twg_ready()
    if not ready:
        return {"status": "failed", "code": "TWG_UNAVAILABLE", "message": reason}
    command = [
        "jira",
        "workitem",
        "create",
        "--space",
        project_key,
        "--type",
        issue_type,
        "--summary",
        summary,
        "-o",
        "json",
    ]
    if description:
        command.extend(["--description", description, "--description-format", "markdown"])
    priority = str(args.get("priority") or resource.get("priority") or "").strip()
    if priority:
        command.extend(["--priority", priority])
    labels = _labels_arg(args.get("labels") or resource.get("labels"))
    if labels:
        command.extend(["--labels", labels])
    parent = str(args.get("parent") or resource.get("parent") or "").strip()
    if parent:
        command.extend(["--parent", parent])
    command.extend(site_args(cfg))
    code, output = run_twg(command)
    if code != 0:
        return {"status": "failed", "code": "JIRA_CREATE_FAILED", "message": truncate_error(output or f"twg exit {code}")}
    key, url = parse_issue_key(output)
    if not key:
        return {"status": "failed", "code": "JIRA_CREATE_PARSE", "message": truncate_error(output or "no issue key")}
    url = url or jira_browse_url_from_config(key, cfg) or ""
    return {
        "status": "completed",
        "issue_key": key,
        "url": url,
        "summary": summary,
        "issue_type": issue_type,
        "project_key": project_key,
        "target_version": target_version,
    }


def _update_workitem(request: ActionRequest) -> dict[str, Any]:
    from jira_sync import jira_browse_url_from_config, run_twg, site_args, truncate_error, twg_ready

    args = request.arguments if isinstance(request.arguments, dict) else {}
    resource = request.resource if isinstance(request.resource, dict) else {}
    issue_key = str(
        args.get("issue_key")
        or args.get("id")
        or args.get("key")
        or resource.get("issue_key")
        or resource.get("id")
        or resource.get("key")
        or ""
    ).strip()
    if not issue_key:
        raise ResourceDenied("issue_key required")
    cfg = _jira_config(str(request.project_slug or "").strip())
    ready, reason = twg_ready()
    if not ready:
        return {"status": "failed", "code": "TWG_UNAVAILABLE", "message": reason}
    command = ["jira", "workitem", "update", "--id", issue_key, "-o", "json"]
    changed = False
    summary = str(args.get("summary") or "").strip()
    if summary:
        command.extend(["--summary", summary])
        changed = True
    description = str(args.get("description") or "").strip()
    if description:
        command.extend(["--description", description, "--description-format", "markdown"])
        changed = True
    priority = str(args.get("priority") or "").strip()
    if priority:
        command.extend(["--priority", priority])
        changed = True
    labels = _labels_arg(args.get("labels"))
    if labels:
        command.extend(["--labels", labels])
        changed = True
    add_labels = _labels_arg(args.get("add_labels"))
    if add_labels:
        command.extend(["--add-labels", add_labels])
        changed = True
    comment = str(args.get("comment") or "").strip()
    if comment:
        command.extend(["--comment", comment, "--comment-format", "markdown"])
        changed = True
    status = str(args.get("status") or "").strip()
    if status:
        command.extend(["--status", status])
        changed = True
    if not changed:
        raise ResourceDenied("no update fields provided")
    command.extend(site_args(cfg))
    code, output = run_twg(command)
    if code != 0:
        return {
            "status": "failed",
            "code": "JIRA_UPDATE_FAILED",
            "issue_key": issue_key,
            "message": truncate_error(output or f"twg exit {code}"),
        }
    url = jira_browse_url_from_config(issue_key, cfg) or ""
    return {
        "status": "completed",
        "issue_key": issue_key,
        "url": url,
        "summary": summary,
    }


def execute_jira_action(request: ActionRequest) -> dict[str, Any]:
    action = str(request.action or "").strip()
    if action == "jira.workitem.create":
        return _create_workitem(request)
    if action == "jira.workitem.update":
        return _update_workitem(request)
    raise CapabilityDenied(f"unsupported jira action: {action}")
