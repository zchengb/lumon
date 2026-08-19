from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from agents.security.access_policy import AccessDecision
from agents.security.actions import ActionReceipt, ActionRequest
from agents.security.broker import CapabilityBroker


@dataclass(frozen=True)
class TrustedActionContext:
    agent_id: str
    project_slug: str
    actor_user_id: str
    chat_id: str
    thread_id: str
    source_message_id: str
    trace_id: str
    chat_type: str = ""
    access_decision: AccessDecision | None = None
    explicit_authorization: bool = False
    user_message: str = ""
    image_keys: str = ""
    workspace_path: str = ""


def trusted_context_from_meta(
    *,
    agent_id: str,
    project_slug: str,
    meta: dict[str, str],
    trace_id: str,
    access_decision: AccessDecision | None = None,
    explicit_authorization: bool | None = None,
) -> TrustedActionContext:
    return TrustedActionContext(
        agent_id=str(agent_id or "").strip().lower(),
        project_slug=str(project_slug or "").strip(),
        actor_user_id=str(meta.get("user_id") or "").strip(),
        chat_id=str(meta.get("chat_id") or "").strip(),
        thread_id=str(meta.get("thread_id") or "").strip(),
        source_message_id=str(meta.get("message_id") or "").strip(),
        trace_id=str(trace_id or "").strip(),
        chat_type=str(meta.get("chat_type") or "").strip(),
        access_decision=access_decision,
        explicit_authorization=bool(explicit_authorization),
        user_message=str(meta.get("_user_message") or ""),
        image_keys=str(meta.get("image_keys") or ""),
        workspace_path=str(meta.get("_workspace_path") or "").strip(),
    )


def bind_action_request(
    *,
    context: TrustedActionContext,
    action: str,
    resource: Optional[dict[str, Any]] = None,
    arguments: Optional[dict[str, Any]] = None,
) -> ActionRequest:
    args = dict(arguments or {})
    # These values are transport identity, not model inputs.  Always replace
    # them with the Host-bound context so an Agent cannot change access-zone
    # checks or route a reply outside the current conversation.
    args["chat_type"] = context.chat_type
    if context.workspace_path:
        args["_workspace_path"] = context.workspace_path
    return ActionRequest(
        agent_id=context.agent_id,
        action=str(action or "").strip(),
        project_slug=context.project_slug,
        actor_user_id=context.actor_user_id,
        chat_id=context.chat_id,
        thread_id=context.thread_id,
        source_message_id=context.source_message_id,
        trace_id=context.trace_id,
        resource=dict(resource or {}),
        arguments=args,
        explicit_authorization=bool(context.explicit_authorization),
    )


def execute_trusted_actions(
    *,
    context: TrustedActionContext,
    requests: list[dict[str, Any]],
    broker: CapabilityBroker | None = None,
) -> list[ActionReceipt]:
    engine = broker or CapabilityBroker()
    receipts: list[ActionReceipt] = []
    for item in requests:
        action = str(item.get("action") or "").strip()
        if not action:
            continue
        resource = dict(item.get("resource") if isinstance(item.get("resource"), dict) else {})
        arguments = dict(item.get("arguments") if isinstance(item.get("arguments"), dict) else {})
        if action == "test_case.generate":
            issue_key = str(arguments.get("issue_key") or arguments.get("story") or "").strip()
            if issue_key:
                resource.setdefault("issue_key", issue_key)
        for key in (
            "actor_user_id",
            "actor",
            "chat_id",
            "thread_id",
            "source_message_id",
            "trace_id",
            "explicit_authorization",
            "agent_id",
            "project_slug",
            "chat_type",
            "workspace_path",
            "_workspace_path",
        ):
            arguments.pop(key, None)
            resource.pop(key, None)
        if action in {"agent.job.create", "delivery.start", "delivery.quick_change", "test_case.generate"}:
            if context.user_message:
                arguments["user_message"] = context.user_message
            if context.image_keys:
                arguments["image_keys"] = context.image_keys
        request = bind_action_request(
            context=context,
            action=action,
            resource=resource,
            arguments=arguments,
        )
        receipts.append(engine.execute(request))
    return receipts
