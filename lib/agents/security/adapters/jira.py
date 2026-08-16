from __future__ import annotations

import sys
import re
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
    if (parent / "stories").is_dir() or any((parent / name / "config" / "common.json").is_file() for name in ("lumon", "lumen", ".lumen")):
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


def _action_jira_config(request: ActionRequest) -> dict[str, Any]:
    args = request.arguments if isinstance(request.arguments, dict) else {}
    resource = request.resource if isinstance(request.resource, dict) else {}
    config = dict(_jira_config(str(request.project_slug or "").strip()))
    for key in ("project_key", "board_id", "site"):
        value = str(args.get(key) or resource.get(key) or "").strip()
        if value and not str(config.get(key) or "").strip():
            config[key] = value
    return config


def _unwrap_jira_payload(payload: Any) -> Any:
    if isinstance(payload, dict) and isinstance(payload.get("data"), (dict, list)):
        payload = payload["data"]
    if isinstance(payload, dict):
        for key in ("issues", "items", "workitems", "results"):
            if isinstance(payload.get(key), list):
                return payload[key]
        if isinstance(payload.get("issue"), dict):
            return payload["issue"]
    return payload


def _issue_fields(item: dict[str, Any]) -> dict[str, Any]:
    fields = item.get("fields")
    return fields if isinstance(fields, dict) else item


def _issue_value(item: dict[str, Any], key: str) -> str:
    fields = _issue_fields(item)
    value = fields.get(key) or item.get(key) or ""
    if isinstance(value, dict):
        value = value.get("name") or value.get("value") or value.get("key") or ""
    return str(value).strip()


def _normalized_issue(item: Any, config: dict[str, Any]) -> dict[str, str]:
    if not isinstance(item, dict):
        return {}
    key = _issue_value(item, "key") or _issue_value(item, "issueKey") or _issue_value(item, "id")
    if not key:
        return {}
    from jira_sync import jira_browse_url_from_config

    return {
        "issue_key": key,
        "summary": _issue_value(item, "summary"),
        "status": _issue_value(item, "status"),
        "issue_type": _issue_value(item, "issuetype") or _issue_value(item, "issue_type"),
        "url": jira_browse_url_from_config(key, config) or "",
    }


def _get_workitem(request: ActionRequest) -> dict[str, Any]:
    from jira_sync import parse_twg_json, run_twg, site_args, truncate_error, twg_ready

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
    config = _action_jira_config(request)
    ready, reason = twg_ready()
    if not ready:
        return {"status": "failed", "code": "TWG_UNAVAILABLE", "message": reason}
    code, output = run_twg(["jira", "workitem", "get", issue_key, "-o", "json", *site_args(config)])
    if code != 0:
        return {"status": "failed", "code": "JIRA_GET_FAILED", "issue_key": issue_key, "message": truncate_error(output or f"twg exit {code}")}
    payload = _unwrap_jira_payload(parse_twg_json(output))
    if isinstance(payload, list) and len(payload) == 1 and isinstance(payload[0], dict):
        payload = payload[0]
    if not isinstance(payload, dict):
        return {"status": "failed", "code": "JIRA_GET_PARSE", "issue_key": issue_key, "message": "TWG returned no Jira work item"}
    item = _normalized_issue(payload, config)
    return {
        "status": "completed",
        "issue_key": item.get("issue_key") or issue_key,
        "summary": item.get("summary") or "",
        "issue_status": item.get("status") or "",
        "issue_type": item.get("issue_type") or "",
        "url": item.get("url") or "",
        "workitem": payload,
    }


def _query_workitems(request: ActionRequest, *, jql: str | None = None) -> dict[str, Any]:
    from jira_sync import parse_twg_json, run_twg, site_args, truncate_error, twg_ready

    args = request.arguments if isinstance(request.arguments, dict) else {}
    query = str(jql or args.get("jql") or "").strip()
    if not query:
        raise ResourceDenied("jql required")
    config = _action_jira_config(request)
    ready, reason = twg_ready()
    if not ready:
        return {"status": "failed", "code": "TWG_UNAVAILABLE", "message": reason}
    try:
        limit = max(1, min(int(args.get("limit") or 50), 100))
    except (TypeError, ValueError):
        limit = 50
    code, output = run_twg(
        ["jira", "workitem", "query", "--jql", query, "--limit", str(limit), "-o", "json", *site_args(config)]
    )
    if code != 0:
        return {"status": "failed", "code": "JIRA_QUERY_FAILED", "jql": query, "message": truncate_error(output or f"twg exit {code}")}
    payload = _unwrap_jira_payload(parse_twg_json(output))
    raw_items = payload if isinstance(payload, list) else []
    items = [_normalized_issue(item, config) for item in raw_items]
    items = [item for item in items if item]
    return {"status": "completed", "jql": query, "count": len(items), "items": items}


def _as_text_list(value: Any) -> list[str]:
    values = value if isinstance(value, (list, tuple, set)) else str(value or "").split(",")
    return [str(item).strip() for item in values if str(item).strip()]


def _jql_quote(value: str) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _untested_report(request: ActionRequest) -> dict[str, Any]:
    from jira_sync import resolve_active_sprint, truncate_error, twg_ready

    args = request.arguments if isinstance(request.arguments, dict) else {}
    config = _action_jira_config(request)
    project_key = str(config.get("project_key") or "").strip()
    if not project_key:
        return {"status": "failed", "code": "JIRA_CONFIG_MISSING", "message": "project_key required"}
    ready, reason = twg_ready()
    if not ready:
        return {"status": "failed", "code": "TWG_UNAVAILABLE", "message": reason}

    criterion = str(args.get("standard") or args.get("criterion") or "A").strip().upper()
    criterion = {"1": "A", "2": "B", "3": "C", "4": "D"}.get(criterion[:1], criterion)
    criterion = criterion[:1] if criterion[:1] in {"A", "B", "C", "D"} else criterion
    if criterion == "A":
        statuses = _as_text_list(args.get("statuses")) or ["Ready for QA", "待测", "待測", "待测试", "待測試"]
        status_clause = "status in (" + ", ".join(_jql_quote(item) for item in statuses) + ")"
    elif criterion == "B":
        statuses = _as_text_list(args.get("exclude_statuses")) or ["Done", "Verified"]
        status_clause = "status not in (" + ", ".join(_jql_quote(item) for item in statuses) + ")"
    elif criterion == "C":
        field = str(args.get("test_case_field") or "").strip()
        if not field or not re.fullmatch(r"[A-Za-z0-9_]+", field):
            return {
                "status": "failed",
                "code": "JIRA_REPORT_FIELD_REQUIRED",
                "message": "standard C requires a configured Jira test_case_field",
            }
        status_clause = f'"{field}" is EMPTY'
    elif criterion == "D":
        statuses = _as_text_list(args.get("statuses") or args.get("status_names"))
        if not statuses:
            return {"status": "failed", "code": "JIRA_REPORT_STATUS_REQUIRED", "message": "standard D requires statuses"}
        status_clause = "status in (" + ", ".join(_jql_quote(item) for item in statuses) + ")"
    else:
        return {"status": "failed", "code": "JIRA_REPORT_STANDARD_INVALID", "message": "standard must be A, B, C, or D"}

    try:
        sprint_id, sprint_name = resolve_active_sprint(config)
    except Exception as exc:
        return {"status": "failed", "code": "JIRA_SPRINT_LOOKUP_FAILED", "message": truncate_error(str(exc))}
    if not sprint_id:
        return {"status": "failed", "code": "JIRA_NO_ACTIVE_SPRINT", "message": "No active sprint found"}

    query = f"project = {project_key} AND sprint = {sprint_id} AND {status_clause} ORDER BY updated DESC"
    result = _query_workitems(request, jql=query)
    if result.get("status") != "completed":
        return {**result, "criterion": criterion, "sprint_id": sprint_id, "sprint_name": sprint_name or ""}
    items = result.get("items") if isinstance(result.get("items"), list) else []
    return {
        "status": "completed",
        "criterion": criterion,
        "project_key": project_key,
        "sprint_id": sprint_id,
        "sprint_name": sprint_name or "",
        "count": len(items),
        "items": items,
        "summary": f"Found {len(items)} Jira work items in the active sprint matching standard {criterion}.",
    }


def _create_workitem(request: ActionRequest) -> dict[str, Any]:
    from jira_sync import (
        assign_to_active_sprint_enabled,
        assign_workitem_to_sprint,
        jira_browse_url_from_config,
        parse_issue_key,
        resolve_active_sprint,
        run_twg,
        site_args,
        truncate_error,
        twg_ready,
    )

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

    sprint_id = None
    sprint_name = None
    if assign_to_active_sprint_enabled(cfg):
        try:
            sprint_id, sprint_name = resolve_active_sprint(cfg)
        except Exception as exc:
            return {
                "status": "failed",
                "code": "JIRA_SPRINT_LOOKUP_FAILED",
                "message": truncate_error(str(exc)),
            }
        if not sprint_id:
            return {
                "status": "failed",
                "code": "JIRA_NO_ACTIVE_SPRINT",
                "message": "No active sprint found for the configured Jira board",
            }

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
    if sprint_id:
        try:
            assign_workitem_to_sprint(key, sprint_id, cfg)
        except Exception as exc:
            return {
                "status": "failed",
                "code": "JIRA_SPRINT_ASSIGN_FAILED",
                "issue_key": key,
                "url": url,
                "summary": summary,
                "message": f"Created {key}, but could not assign it to active sprint {sprint_name or sprint_id}: {truncate_error(str(exc))}",
            }
    return {
        "status": "completed",
        "issue_key": key,
        "url": url,
        "summary": summary,
        "issue_type": issue_type,
        "project_key": project_key,
        "target_version": target_version,
        "sprint_id": sprint_id or "",
        "sprint_name": sprint_name or "",
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
    if action == "jira.workitem.get":
        return _get_workitem(request)
    if action == "jira.workitem.query":
        return _query_workitems(request)
    if action == "jira.sprint.untested.report":
        return _untested_report(request)
    if action == "jira.workitem.create":
        return _create_workitem(request)
    if action == "jira.workitem.update":
        return _update_workitem(request)
    raise CapabilityDenied(f"unsupported jira action: {action}")
