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
    root_id: str = ""
    chat_type: str = ""
    access_decision: AccessDecision | None = None
    explicit_authorization: bool = False
    user_message: str = ""
    image_keys: str = ""
    workspace_path: str = ""
    # Conversation identity is separate from the acting Agent identity.  A
    # relay may change the target Agent, but it never changes the originating
    # human authority or the bounded relay chain.
    origin_user_id: str = ""
    source_agent_id: str = ""
    target_agent_id: str = ""
    relay_id: str = ""
    relay_hop: int = 0
    relay_visited: str = ""
    thread_native_handoff: str = ""


def trusted_context_from_meta(
    *,
    agent_id: str,
    project_slug: str,
    meta: dict[str, str],
    trace_id: str,
    access_decision: AccessDecision | None = None,
    explicit_authorization: bool | None = None,
) -> TrustedActionContext:
    try:
        relay_hop = max(0, int(str(meta.get("_relay_hop") or "0") or 0))
    except (TypeError, ValueError):
        relay_hop = 0
    return TrustedActionContext(
        agent_id=str(agent_id or "").strip().lower(),
        project_slug=str(project_slug or "").strip(),
        actor_user_id=str(meta.get("user_id") or "").strip(),
        chat_id=str(meta.get("chat_id") or "").strip(),
        thread_id=str(meta.get("thread_id") or "").strip(),
        root_id=str(meta.get("root_id") or meta.get("parent_id") or "").strip(),
        source_message_id=str(meta.get("message_id") or "").strip(),
        trace_id=str(trace_id or "").strip(),
        chat_type=str(meta.get("chat_type") or "").strip(),
        access_decision=access_decision,
        explicit_authorization=bool(explicit_authorization),
        user_message=str(meta.get("_user_message") or ""),
        image_keys=str(meta.get("image_keys") or ""),
        workspace_path=str(meta.get("_workspace_path") or "").strip(),
        origin_user_id=str(meta.get("_origin_user_id") or meta.get("user_id") or "").strip(),
        source_agent_id=str(meta.get("_source_agent") or "").strip().lower(),
        target_agent_id=str(meta.get("_target_agent") or agent_id or "").strip().lower(),
        relay_id=str(meta.get("_relay_id") or "").strip(),
        relay_hop=relay_hop,
        relay_visited=str(meta.get("_relay_visited") or "").strip(),
        thread_native_handoff=str(meta.get("_thread_native_handoff") or "").strip(),
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
    if context.root_id:
        args["_root_id"] = context.root_id
    if context.workspace_path:
        args["_workspace_path"] = context.workspace_path
    if context.origin_user_id:
        args["_origin_user_id"] = context.origin_user_id
    if context.source_agent_id:
        args["_source_agent"] = context.source_agent_id
    if context.target_agent_id:
        args["_target_agent"] = context.target_agent_id
    if context.relay_id:
        args["_relay_id"] = context.relay_id
        args["_relay_hop"] = str(context.relay_hop)
        args["_relay_visited"] = context.relay_visited
    if context.thread_native_handoff:
        args["_thread_native_handoff"] = context.thread_native_handoff
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
            "_root_id",
            "source_message_id",
            "trace_id",
            "explicit_authorization",
            "agent_id",
            "project_slug",
            "chat_type",
            "workspace_path",
            "_workspace_path",
            "_origin_user_id",
            "_source_agent",
            "_target_agent",
            "_relay_id",
            "_relay_hop",
            "_relay_visited",
            "_thread_native_handoff",
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
