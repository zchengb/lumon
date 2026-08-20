from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


POLICY_VERSION = "m0.4.0"


def new_receipt_id() -> str:
    return f"act-{uuid.uuid4().hex[:16]}"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def arguments_hash(arguments: dict[str, Any] | None) -> str:
    payload = json.dumps(arguments or {}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class ActionRequest:
    agent_id: str
    action: str
    project_slug: str
    actor_user_id: str
    chat_id: str
    thread_id: str
    source_message_id: str
    trace_id: str
    resource: dict[str, Any] = field(default_factory=dict)
    arguments: dict[str, Any] = field(default_factory=dict)
    explicit_authorization: bool = False


@dataclass
class ActionReceipt:
    receipt_id: str
    status: str
    action: str
    agent_id: str
    actor: str
    resource: dict[str, Any]
    trace_id: str
    executed_at: str
    authorization_result: str = ""
    policy_version: str = POLICY_VERSION
    result: dict[str, Any] = field(default_factory=dict)
    error_code: str = ""
    error: str = ""
    started_at: str = ""
    completed_at: str = ""
    chat_id: str = ""
    thread_id: str = ""
    source_message_id: str = ""
    arguments_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


JIRA_READ_ACTIONS = (
    "jira.workitem.get",
    "jira.workitem.query",
    "jira.sprint.untested.report",
)

JIRA_MUTATION_ACTIONS = (
    "jira.workitem.create",
    "jira.workitem.update",
)

JIRA_ACTIONS = JIRA_READ_ACTIONS + JIRA_MUTATION_ACTIONS


# Feishu-facing communication is an Agent-selectable capability, while the
# Host remains responsible for credentials, message identity, thread routing,
# workspace boundaries, and cleanup.  These are intentionally not mutation
# actions: sending a user-visible progress update or an explicitly requested
# attachment is part of completing the current conversation, not an
# authorization to change business data.
FEISHU_ACTIONS = (
    "feishu.say",
    "feishu.send_progress",
    "feishu.send_file",
)

# Lightweight delegation is available to every Agent.  The host still
# resolves the target, authorization, and Action Receipt through the existing
# job broker; this action is a small native seam rather than a second planner.
DELEGATION_ACTIONS = ("agent.delegate",)


DYLAN_ACTIONS = (
    "risk.read",
    "risk.resolve",
    "risk.mark_remediated",
    "risk.reconcile",
    "scan.read",
    "scan.schedule.read",
    "scan.schedule.update",
    "scan.verify.request",
    *JIRA_ACTIONS,
    *FEISHU_ACTIONS,
    *DELEGATION_ACTIONS,
)

MARK_ACTIONS = (
    "delivery.readiness",
    "delivery.status",
    "delivery.result",
    "delivery.start",
    "delivery.cancel",
    "delivery.quick_change",
    "loop.business",
    "loop.technical",
    "story.read",
    "technical_plan.read",
    "test_case.generate",
    *JIRA_ACTIONS,
    *FEISHU_ACTIONS,
    *DELEGATION_ACTIONS,
)

MILCHICK_ACTIONS = (
    "agent.list",
    "agent.health",
    "agent.job.list",
    "agent.job.show",
    "agent.job.create",
    "agent.job.cancel",
    "agent.job.retry",
    *JIRA_ACTIONS,
    "project.status",
    "workflow.status",
    "schedule.status",
    "lumen.system.health",
    "lumen.agent.status",
    "lumen.runner.status",
    *FEISHU_ACTIONS,
    *DELEGATION_ACTIONS,
)

IRVING_ACTIONS = (
    "risk.read",
    "risk.mark_remediated",
    *JIRA_ACTIONS,
    *FEISHU_ACTIONS,
    *DELEGATION_ACTIONS,
)

# This is the executor registry's action vocabulary, not a list of what each
# Agent owns.  Ownership is documented in agents/responsibilities/*.md and
# enforced as a negative responsibility blacklist by security.policy.
ALL_ACTIONS = frozenset(
    {
        *DYLAN_ACTIONS,
        *MARK_ACTIONS,
        *MILCHICK_ACTIONS,
        *IRVING_ACTIONS,
    }
)

MUTATION_ACTIONS = frozenset(
    {
        "risk.resolve",
        "risk.mark_remediated",
        "risk.reconcile",
        "scan.schedule.update",
        "scan.verify.request",
        "delivery.start",
        "delivery.cancel",
        "delivery.quick_change",
        "loop.business",
        "loop.technical",
        "test_case.generate",
        "agent.job.create",
        "agent.job.cancel",
        "agent.job.retry",
        "agent.delegate",
        *JIRA_MUTATION_ACTIONS,
    }
)
