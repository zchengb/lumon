from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.security.actions import ActionRequest
from agents.security.errors import CapabilityDenied, ResourceDenied


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
    if not issue_key:
        raise ResourceDenied("issue_key required")
    workspace = _docs_root(project)
    return generate_test_cases_for_issue(
        project=project,
        issue_key=issue_key,
        workspace=workspace,
        requested_by=request.actor_user_id,
        generated_by=request.agent_id,
        source_message_id=request.source_message_id,
        trace_id=request.trace_id,
    )
