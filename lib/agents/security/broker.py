from __future__ import annotations

from typing import Any, Callable, Optional

from agents.security.actions import (
    JIRA_ACTIONS,
    MUTATION_ACTIONS,
    ActionReceipt,
    ActionRequest,
    arguments_hash,
    new_receipt_id,
    utc_now,
)
from agents.security.audit import emit_security_event, write_receipt
from agents.security.errors import AuthorizationDenied, CapabilityDenied, SecurityError
from agents.security.policy import is_action_allowed_for_agent, is_action_known
from agents.security.flags import trusted_dedicated_machine_enabled
from feishu.config import load_agents_config

Executor = Callable[[ActionRequest], dict[str, Any]]


class CapabilityBroker:
    def __init__(
        self,
        *,
        config: Optional[dict[str, Any]] = None,
        executors: Optional[dict[str, Executor]] = None,
        audit: bool = True,
    ) -> None:
        self.config = config if isinstance(config, dict) else load_agents_config()
        self.executors = executors if executors is not None else default_executors()
        self.audit = bool(audit)

    def _emit_security_event(self, event: str, **fields: Any) -> None:
        if self.audit:
            emit_security_event(event, **fields)

    def _write_receipt(self, receipt: ActionReceipt) -> None:
        if self.audit:
            write_receipt(receipt)

    def execute(self, request: ActionRequest) -> ActionReceipt:
        from agents.security.access_policy import authorize_agent_interaction, mutation_allowed_for_decision

        started = utc_now()
        receipt_id = new_receipt_id()
        action = str(request.action or "").strip()
        agent_id = str(request.agent_id or "").strip().lower()
        trusted_machine = trusted_dedicated_machine_enabled(self.config)
        try:
            if not action:
                raise CapabilityDenied("action is required")
            if not is_action_known(action):
                self._emit_security_event(
                    "security.action.unknown",
                    agent_id=agent_id,
                    action=action,
                    actor_user_id=request.actor_user_id,
                    chat_id=request.chat_id,
                    trace_id=request.trace_id,
                )
                raise CapabilityDenied(f"unknown action {action}")
            if not trusted_machine and not is_action_allowed_for_agent(agent_id, action):
                self._emit_security_event(
                    "security.responsibility.denied",
                    agent_id=agent_id,
                    action=action,
                    actor_user_id=request.actor_user_id,
                    chat_id=request.chat_id,
                    trace_id=request.trace_id,
                )
                raise CapabilityDenied(
                    f"action {action} is forbidden by the {agent_id} responsibility document"
                )
            chat_type = ""
            if isinstance(request.arguments, dict):
                chat_type = str(request.arguments.get("chat_type") or "").strip()
            gate_only = bool(request.entry_gate_token and request.access_decision is not None)
            decision = request.access_decision if gate_only else authorize_agent_interaction(
                agent_id=agent_id,
                meta={
                    "user_id": request.actor_user_id,
                    "chat_id": request.chat_id,
                    "chat_type": chat_type,
                    "thread_id": request.thread_id,
                    "message_id": request.source_message_id,
                },
                config=self.config,
            )
            if gate_only:
                context = getattr(decision, "context", None)
                if not decision.allowed or (
                    context is not None
                    and (
                        str(context.agent_id or "").strip().lower() != agent_id
                        or str(context.user_id or "").strip() != str(request.actor_user_id or "").strip()
                        or str(context.chat_id or "").strip() != str(request.chat_id or "").strip()
                    )
                ):
                    raise AuthorizationDenied("invalid or mismatched entry gate")
            if not decision.allowed:
                self._emit_security_event(
                    "agent.access.denied",
                    reason=decision.reason_code,
                    agent_id=agent_id,
                    action=action,
                    chat_id=request.chat_id,
                    actor_user_id=request.actor_user_id,
                    trace_id=request.trace_id,
                )
                raise AuthorizationDenied(decision.reason_code or "access denied")
            if not trusted_machine and (action.startswith("host.") or action.startswith("lumen.")):
                if action not in decision.effective_capabilities:
                    self._emit_security_event(
                        "agent.access.host_read_denied",
                        agent_id=agent_id,
                        action=action,
                        trust_zone=decision.trust_zone,
                        actor_user_id=request.actor_user_id,
                        chat_id=request.chat_id,
                    )
                    raise AuthorizationDenied(f"host capability denied in zone {decision.trust_zone}")
            if action in MUTATION_ACTIONS and not gate_only and not trusted_machine:
                if not mutation_allowed_for_decision(decision, action=action):
                    self._emit_security_event(
                        "agent.access.mutation_denied",
                        agent_id=agent_id,
                        action=action,
                        trust_zone=decision.trust_zone,
                        actor_user_id=request.actor_user_id,
                        chat_id=request.chat_id,
                    )
                    raise AuthorizationDenied(
                        f"mutation denied for zone={decision.trust_zone or '-'} action={action}"
                    )
            args = dict(request.arguments or {})
            args["_access_decision"] = {
                "allowed": decision.allowed,
                "trust_zone": decision.trust_zone,
                "host_read_allowed": decision.host_read_allowed,
                "mutation_allowed": decision.mutation_allowed,
                "effective_capabilities": sorted(decision.effective_capabilities),
                "exposure_mode": decision.exposure_mode,
            }
            enriched = ActionRequest(
                agent_id=request.agent_id,
                action=request.action,
                project_slug=request.project_slug,
                actor_user_id=request.actor_user_id,
                chat_id=request.chat_id,
                thread_id=request.thread_id,
                source_message_id=request.source_message_id,
                trace_id=request.trace_id,
                resource=dict(request.resource or {}),
                arguments=args,
                explicit_authorization=request.explicit_authorization,
                entry_gate_token=request.entry_gate_token,
                access_decision=request.access_decision,
            )
            executor = self.executors.get(action)
            if executor is None:
                raise CapabilityDenied(f"no executor registered for {action}")
            result = executor(enriched)
            if not isinstance(result, dict):
                result = {"value": result}
            completed = utc_now()
            receipt = ActionReceipt(
                receipt_id=receipt_id,
                status="succeeded",
                action=action,
                agent_id=agent_id,
                actor=request.actor_user_id,
                resource=dict(request.resource or {}),
                trace_id=request.trace_id,
                executed_at=completed,
                authorization_result="allowed",
                result=result,
                started_at=started,
                completed_at=completed,
                chat_id=request.chat_id,
                thread_id=request.thread_id,
                source_message_id=request.source_message_id,
                arguments_hash=arguments_hash(request.arguments),
            )
            self._write_receipt(receipt)
            return receipt
        except SecurityError as exc:
            completed = utc_now()
            self._emit_security_event(
                "security.action.denied",
                code=exc.code,
                message=str(exc),
                agent_id=agent_id,
                action=action,
                actor_user_id=request.actor_user_id,
                chat_id=request.chat_id,
                trace_id=request.trace_id,
            )
            receipt = ActionReceipt(
                receipt_id=receipt_id,
                status="denied",
                action=action,
                agent_id=agent_id,
                actor=request.actor_user_id,
                resource=dict(request.resource or {}),
                trace_id=request.trace_id,
                executed_at=completed,
                authorization_result="denied",
                error_code=exc.code,
                error=str(exc)[:500],
                started_at=started,
                completed_at=completed,
                chat_id=request.chat_id,
                thread_id=request.thread_id,
                source_message_id=request.source_message_id,
                arguments_hash=arguments_hash(request.arguments),
            )
            self._write_receipt(receipt)
            return receipt
        except Exception as exc:
            completed = utc_now()
            receipt = ActionReceipt(
                receipt_id=receipt_id,
                status="failed",
                action=action,
                agent_id=agent_id,
                actor=request.actor_user_id,
                resource=dict(request.resource or {}),
                trace_id=request.trace_id,
                executed_at=completed,
                authorization_result="allowed",
                error_code="EXECUTOR_ERROR",
                error=str(exc)[:500],
                started_at=started,
                completed_at=completed,
                chat_id=request.chat_id,
                thread_id=request.thread_id,
                source_message_id=request.source_message_id,
                arguments_hash=arguments_hash(request.arguments),
            )
            self._write_receipt(receipt)
            return receipt


def default_executors() -> dict[str, Executor]:
    from agents.security.adapters.delivery import execute_delivery_action
    from agents.security.adapters.feishu import execute_feishu_action
    from agents.security.adapters.risk import execute_risk_action
    from agents.security.adapters.schedule import execute_schedule_action

    mapping: dict[str, Executor] = {}
    for action in (
        "risk.read",
        "risk.resolve",
        "risk.mark_remediated",
        "risk.reconcile",
        "scan.verify.request",
        "scan.read",
    ):
        mapping[action] = execute_risk_action
    for action in ("scan.schedule.read", "scan.schedule.update"):
        mapping[action] = execute_schedule_action
    for action in (
        "delivery.readiness",
        "delivery.status",
        "delivery.result",
        "delivery.start",
        "delivery.cancel",
        "delivery.quick_change",
        "story.read",
        "technical_plan.read",
        "loop.business",
        "loop.technical",
    ):
        mapping[action] = execute_delivery_action
    from agents.security.adapters.test_case import execute_test_case_action
    from agents.jobs.broker import execute_job_action

    mapping["test_case.generate"] = execute_test_case_action
    from agents.security.adapters.jira import execute_jira_action

    for action in JIRA_ACTIONS:
        mapping[action] = execute_jira_action
    from agents.security.adapters.host_read import execute_host_read_action

    for action in (
        "host.disk.summary",
        "host.runtime.summary",
        "host.applications.summary",
        "lumen.system.health",
        "lumen.agent.status",
        "lumen.runner.status",
    ):
        mapping[action] = execute_host_read_action
    for action in (
        "agent.list",
        "agent.health",
        "agent.job.list",
        "agent.job.show",
        "agent.job.create",
        "agent.job.cancel",
        "agent.job.retry",
        "agent.delegate",
        "project.status",
        "workflow.status",
        "schedule.status",
    ):
        mapping[action] = execute_job_action
    for action in ("feishu.say", "feishu.send_progress", "feishu.send_file"):
        mapping[action] = execute_feishu_action
    return mapping
