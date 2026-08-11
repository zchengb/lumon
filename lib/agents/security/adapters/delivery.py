from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.security.actions import ActionRequest
from agents.security.errors import CapabilityDenied, ResourceDenied


def _docs_root(project_slug: str) -> Path:
    from agents.project_resolver import resolve_project

    project = resolve_project(slug=project_slug)
    if not project or not project.get("workspace"):
        raise ResourceDenied(f"project workspace missing: {project_slug}")
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


def execute_delivery_action(request: ActionRequest) -> dict[str, Any]:
    from agents.mark.delivery_adapter import DeliveryActionAdapter

    adapter = DeliveryActionAdapter()
    project = str(request.project_slug or request.arguments.get("project") or "").strip()
    story = str(request.resource.get("story") or request.arguments.get("story") or "").strip()
    run_id = str(request.resource.get("run_id") or request.arguments.get("run_id") or "").strip()
    args = dict(request.arguments or {})
    resource = dict(request.resource or {})
    docs = _docs_root(project) if project else Path.cwd()
    action = request.action

    if action in {"story.read", "technical_plan.read"}:
        if not story:
            raise ResourceDenied("story required")
        story_dir = docs / "stories" / story
        plan = story_dir / "technical-plan.md"
        meta = story_dir / "metadata.json"
        return {
            "story": story,
            "exists": story_dir.is_dir(),
            "technical_plan": plan.read_text(encoding="utf-8")[:4000] if plan.is_file() else "",
            "metadata": meta.read_text(encoding="utf-8")[:2000] if meta.is_file() else "",
        }

    if action == "delivery.readiness":
        if not story:
            raise ResourceDenied("story required")
        return adapter.readiness(workspace=docs, story=story)

    if action == "delivery.status":
        return adapter.status(workspace=docs, story=story, run_id=run_id)

    if action == "delivery.result":
        return adapter.result(workspace=docs, run_id=run_id)

    if action == "delivery.start":
        if not story:
            raise ResourceDenied("story required")
        return adapter.start(
            workspace=docs,
            story=story,
            actor=request.actor_user_id,
            source_message_id=request.source_message_id,
            trace_id=request.trace_id,
            chat_id=request.chat_id,
            thread_id=request.thread_id,
            project_slug=project,
            user_message=str(args.get("user_message") or resource.get("user_message") or ""),
        )

    if action == "delivery.cancel":
        return adapter.cancel(workspace=docs, run_id=run_id, actor=request.actor_user_id)

    if action == "delivery.quick_change":
        repository = str(resource.get("repository") or args.get("repository") or args.get("repo") or "").strip()
        target_files = resource.get("target_files") or args.get("target_files") or resource.get("target_file") or args.get("target_file") or []
        requested_change = str(
            resource.get("request") or args.get("request") or args.get("task") or args.get("change") or ""
        ).strip()
        return adapter.quick_change(
            workspace=docs,
            repository=repository,
            target_files=target_files,
            request=requested_change,
            target_version=str(resource.get("target_version") or args.get("target_version") or "").strip(),
            change_type=str(resource.get("change_type") or args.get("change_type") or "small_change").strip(),
            actor=request.actor_user_id,
            source_message_id=request.source_message_id,
            trace_id=request.trace_id,
            chat_id=request.chat_id,
            thread_id=request.thread_id,
            project_slug=project,
            user_message=str(args.get("user_message") or resource.get("user_message") or ""),
        )

    raise CapabilityDenied(f"unsupported delivery action: {action}")
