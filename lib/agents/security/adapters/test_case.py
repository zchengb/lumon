from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.security.actions import ActionRequest
from agents.security.errors import CapabilityDenied, ResourceDenied
from skills.test_case.localization import infer_test_case_language


def _docs_root(project_slug: str) -> Path | None:
    from agents.project_resolver import resolve_project

    project = resolve_project(slug=project_slug)
    if not project or not project.get("workspace"):
        return None
    workspace = Path(str(project["workspace"])).expanduser().resolve()
    parent = workspace.parent
    if (parent / "stories").is_dir():
        return parent
    if (workspace / "stories").is_dir():
        return workspace
    for child in workspace.iterdir() if workspace.is_dir() else []:
        if child.is_dir() and (child / "stories").is_dir():
            return child
    return workspace


def _format_batch_summary(per_issue: list[dict[str, Any]], completed: int, language: str) -> str:
    total = len(per_issue)
    if language == "en":
        lines = [f"Generated test cases for {completed}/{total} Ready for QA Stories."]
        done, failed = "completed", "failed"
    elif language == "zh-Hans":
        lines = [f"已为 {completed}/{total} 张 Ready for QA Story 生成测试用例。"]
        done, failed = "已完成", "失败"
    else:
        lines = [f"已為 {completed}/{total} 張 Ready for QA Story 生成測試用例。"]
        done, failed = "已完成", "失敗"
    for item in per_issue:
        key = str(item.get("issue_key") or "").strip()
        summary = " ".join(str(item.get("summary") or "").split())
        label = " — ".join(part for part in (key, summary) if part)
        if item["status"] in {"completed", "succeeded", "success"}:
            link = str(item.get("sheet_url") or "").strip()
            suffix = f" — {link}" if link else ""
            lines.append(f"- {label}: {done}{suffix}" if language == "en" else f"- {label}：{done}{suffix}")
        else:
            detail = str(item.get("message") or item.get("code") or "generation failed").strip()
            lines.append(f"- {label}: {failed} — {detail}" if language == "en" else f"- {label}：{failed} — {detail}")
    return "\n".join(lines)


def execute_test_case_action(request: ActionRequest) -> dict[str, Any]:
    from skills.test_case.skill import generate_test_cases_for_issue

    if request.action != "test_case.generate":
        raise CapabilityDenied(f"unsupported test_case action: {request.action}")
    project = str(request.project_slug or request.arguments.get("project") or "").strip()
    issue_key = str(
        request.resource.get("issue_key")
        or request.resource.get("story")
        or request.arguments.get("issue_key")
        or request.arguments.get("story")
        or ""
    ).strip()
    if not project:
        raise ResourceDenied("project required")
    workspace = _docs_root(project)
    args = request.arguments if isinstance(request.arguments, dict) else {}
    user_message = str(args.get("user_message") or request.resource.get("user_message") or "").strip()
    response_language = infer_test_case_language(user_message)
    scope = str(args.get("scope") or request.resource.get("scope") or "").strip().casefold().replace(" ", "_")
    if not issue_key and scope not in {"ready_for_qa", "ready_for_test"}:
        raise ResourceDenied("issue_key or scope=ready_for_qa required")
    if not issue_key:
        from agents.security.adapters.jira import _action_jira_config, _jql_quote, _query_workitems

        config = _action_jira_config(request)
        project_key = str(config.get("project_key") or "").strip()
        if not project_key:
            return {"status": "failed", "code": "JIRA_CONFIG_MISSING", "message": "project_key required"}
        statuses = args.get("statuses") or ["Ready for QA", "待测", "待測", "待测试", "待測試"]
        if not isinstance(statuses, (list, tuple, set)):
            statuses = [statuses]
        status_clause = "status in (" + ", ".join(_jql_quote(str(item).strip()) for item in statuses if str(item).strip()) + ")"
        discovery = _query_workitems(
            request,
            jql=f'project = {project_key} AND issuetype = "Story" AND {status_clause} ORDER BY updated DESC',
        )
        if discovery.get("status") != "completed":
            return discovery
        items = discovery.get("items") if isinstance(discovery.get("items"), list) else []
        per_issue: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            key = str(item.get("issue_key") or "").strip()
            if not key:
                continue
            try:
                generated = generate_test_cases_for_issue(
                    project=project,
                    issue_key=key,
                    workspace=workspace,
                    requested_by=request.actor_user_id,
                    generated_by=request.agent_id,
                    response_language=response_language,
                    source_message_id=request.source_message_id,
                    trace_id=request.trace_id,
                )
            except Exception as exc:
                generated = {"status": "failed", "code": "TEST_CASE_EXECUTION_FAILED", "message": str(exc)[:500]}
            status = str(generated.get("status") or "failed").strip().lower()
            per_issue.append(
                {
                    "issue_key": key,
                    "summary": str(item.get("summary") or "").strip(),
                    "status": status,
                    "generated": generated.get("generated", 0),
                    "created": generated.get("created", 0),
                    "sheet_url": generated.get("sheet_url", ""),
                    "code": generated.get("code", ""),
                    "message": generated.get("message", ""),
                }
            )
        completed = sum(1 for item in per_issue if item["status"] in {"completed", "succeeded", "success"})
        failed = len(per_issue) - completed
        overall = "completed" if failed == 0 else "partial" if completed else "failed"
        return {
            "status": overall,
            "scope": "ready_for_qa",
            "batch": True,
            "count": len(per_issue),
            "completed": completed,
            "failed": failed,
            "items": per_issue,
            "response_language": response_language,
            "summary": _format_batch_summary(per_issue, completed, response_language),
        }
    return generate_test_cases_for_issue(
        project=project,
        issue_key=issue_key,
        workspace=workspace,
        requested_by=request.actor_user_id,
        generated_by=request.agent_id,
        response_language=response_language,
        source_message_id=request.source_message_id,
        trace_id=request.trace_id,
    )
