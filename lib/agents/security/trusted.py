from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from agents.security.access_policy import AccessDecision, classify_authorization_intent
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
    authorization_intent: str = "none"
    access_decision: AccessDecision | None = None
    explicit_authorization: bool = False


def trusted_context_from_meta(
    *,
    agent_id: str,
    project_slug: str,
    meta: dict[str, str],
    trace_id: str,
    user_text: str = "",
    access_decision: AccessDecision | None = None,
    explicit_authorization: bool | None = None,
    authorization_intent: str | None = None,
) -> TrustedActionContext:
    requested_intent = str(authorization_intent or "").strip().lower()
    intent = requested_intent if requested_intent in {"none", "read", "mutate_explicit", "confirm_previous"} else classify_authorization_intent(user_text)
    explicit = bool(explicit_authorization) if explicit_authorization is not None else intent in {
        "mutate_explicit",
        "confirm_previous",
    }
    return TrustedActionContext(
        agent_id=str(agent_id or "").strip().lower(),
        project_slug=str(project_slug or "").strip(),
        actor_user_id=str(meta.get("user_id") or "").strip(),
        chat_id=str(meta.get("chat_id") or "").strip(),
        thread_id=str(meta.get("thread_id") or "").strip(),
        source_message_id=str(meta.get("message_id") or "").strip(),
        trace_id=str(trace_id or "").strip(),
        chat_type=str(meta.get("chat_type") or "").strip(),
        authorization_intent=intent,
        access_decision=access_decision,
        explicit_authorization=explicit,
    )


def bind_action_request(
    *,
    context: TrustedActionContext,
    action: str,
    resource: Optional[dict[str, Any]] = None,
    arguments: Optional[dict[str, Any]] = None,
) -> ActionRequest:
    args = dict(arguments or {})
    args.setdefault("chat_type", context.chat_type)
    intent = context.authorization_intent
    if context.explicit_authorization and intent == "none":
        intent = "mutate_explicit"
    args.setdefault("_authorization_intent", intent)
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
        resource = item.get("resource") if isinstance(item.get("resource"), dict) else {}
        arguments = item.get("arguments") if isinstance(item.get("arguments"), dict) else {}
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
        ):
            arguments.pop(key, None)
            resource.pop(key, None)
        request = bind_action_request(
            context=context,
            action=action,
            resource=resource,
            arguments=arguments,
        )
        receipts.append(engine.execute(request))
    return receipts
