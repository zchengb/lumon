from __future__ import annotations

from typing import Any, Optional

from agents.jobs.store import AgentJob, AgentJobStore, new_job_id
from agents.security.actions import ActionRequest
from agents.security.broker import CapabilityBroker
from agents.security.trusted import TrustedActionContext, bind_action_request


TERMINAL = frozenset({"completed", "failed", "cancelled"})


# Capabilities that hand the original turn to Mark as an agent instead of a
# host adapter call. Loops are conversational workspace work, so Mark decides
# the details himself, exactly like a bounded quick change.
MARK_AGENT_HANDOFF_CAPABILITIES = frozenset(
    {"delivery.quick_change", "loop.business", "loop.technical"}
)


class AgentJobBroker:
    def __init__(self, store: AgentJobStore | None = None) -> None:
        self.store = store or AgentJobStore()

    def create_parent(
        self,
        *,
        project: str,
        requested_by: str,
        delegated_by: str,
        source_message_id: str,
        chat_id: str,
        thread_id: str,
        trace_id: str,
        input_data: Optional[dict[str, Any]] = None,
    ) -> AgentJob:
        job = AgentJob(
            job_id=new_job_id("job_parent"),
            type="agent_job",
            status="running",
            project=project,
            requested_by=requested_by,
            delegated_by=delegated_by,
            source_message_id=source_message_id,
            chat_id=chat_id,
            thread_id=thread_id,
            trace_id=trace_id,
            input=dict(input_data or {}),
        )
        return self.store.save(job)

    def create_child(
        self,
        *,
        parent: AgentJob,
        target_agent: str,
        capability: str,
        input_data: Optional[dict[str, Any]] = None,
        depends_on: Optional[list[str]] = None,
    ) -> AgentJob:
        deps = list(depends_on or [])
        status = "ready" if not deps else "queued"
        if deps:
            for dep_id in deps:
                dep = self.store.get(dep_id)
                if dep is None or dep.status not in {"completed"}:
                    status = "queued"
                    break
            else:
                status = "ready"
        job = AgentJob(
            job_id=new_job_id(f"job_{target_agent}"),
            type="agent_job_child",
            status=status,
            project=parent.project,
            requested_by=parent.requested_by,
            delegated_by=parent.delegated_by,
            target_agent=target_agent,
            capability=capability,
            parent_job_id=parent.job_id,
            depends_on=deps,
            input=dict(input_data or {}),
            source_message_id=parent.source_message_id,
            chat_id=parent.chat_id,
            thread_id=parent.thread_id,
            trace_id=parent.trace_id,
        )
        return self.store.save(job)

    def refresh_dependencies(self, parent_job_id: str) -> list[AgentJob]:
        updated: list[AgentJob] = []
        for child in self.store.children(parent_job_id):
            if child.status not in {"queued", "blocked"}:
                continue
            if not child.depends_on:
                child.status = "ready"
                updated.append(self.store.save(child))
                continue
            failed = False
            waiting = False
            for dep_id in child.depends_on:
                dep = self.store.get(dep_id)
                if dep is None:
                    waiting = True
                    continue
                if dep.status == "failed":
                    failed = True
                    break
                if dep.status != "completed":
                    waiting = True
            if failed:
                child.status = "blocked"
            elif not waiting:
                child.status = "ready"
            updated.append(self.store.save(child))
        return updated

    def summarize(self, parent_job_id: str) -> dict[str, Any]:
        parent = self.store.get(parent_job_id)
        children = self.store.children(parent_job_id)
        by_status: dict[str, list[str]] = {}
        for child in children:
            by_status.setdefault(child.status, []).append(child.job_id)
        overall = parent.status if parent else "unknown"
        if parent and children:
            if any(c.status == "failed" for c in children):
                overall = "failed" if all(c.status in TERMINAL for c in children) else "running"
            elif all(c.status == "completed" for c in children):
                overall = "completed"
            elif any(c.status == "blocked" for c in children):
                overall = "blocked"
            else:
                overall = "running"
            if parent.status != overall:
                parent.status = overall
                self.store.save(parent)
        next_dep = ""
        for child in children:
            if child.status in {"queued", "blocked", "ready", "running"}:
                next_dep = child.capability or child.target_agent
                break
        return {
            "parent_job_id": parent_job_id,
            "overall_state": overall,
            "completed": by_status.get("completed", []),
            "running": by_status.get("running", []) + by_status.get("ready", []),
            "blocked": by_status.get("blocked", []) + by_status.get("queued", []),
            "failed": by_status.get("failed", []),
            "next_dependency": next_dep,
            "owner": parent.delegated_by if parent else "",
            "children": [c.to_dict() for c in children],
        }

    def execute_ready_child(
        self,
        child: AgentJob,
        *,
        broker: CapabilityBroker | None = None,
    ) -> AgentJob:
        if child.status not in {"ready", "queued"} and not child.depends_on:
            if child.status != "ready":
                return child
        self.refresh_dependencies(child.parent_job_id)
        current = self.store.get(child.job_id) or child
        if current.status != "ready":
            return current
        current.status = "running"
        self.store.save(current)
        handoff = self._execute_mark_handoff(current)
        if handoff is not None:
            receipt_payload = handoff
            succeeded = handoff.get("status") == "succeeded"
            error = str(handoff.get("error") or "agent_handoff_failed")
        else:
            context = TrustedActionContext(
                agent_id=current.target_agent,
                project_slug=current.project,
                actor_user_id=current.requested_by,
                chat_id=current.chat_id,
                thread_id=current.thread_id,
                source_message_id=current.source_message_id,
                trace_id=current.trace_id,
                explicit_authorization=True,
            )
            request = bind_action_request(
                context=context,
                action=current.capability,
                resource=dict(current.input),
                arguments=dict(current.input),
            )
            receipt = (broker or CapabilityBroker()).execute(request)
            receipt_payload = receipt.to_dict()
            nested = receipt.result if isinstance(receipt.result, dict) else {}
            nested_failed = str(nested.get("status") or "").lower() == "failed"
            succeeded = receipt.status == "succeeded" and not nested_failed
            error = (
                str(nested.get("code") or nested.get("message") or "action_failed")
                if nested_failed
                else receipt.error or receipt.error_code or receipt.status
            )
        current.result = receipt_payload
        if succeeded:
            current.status = "completed"
            current.error = ""
            self._handoff_reply(current, receipt_payload)
        else:
            current.status = "failed"
            current.error = error
            self._handoff_reply(current, receipt_payload, failed=True)
        self.store.save(current)
        if current.parent_job_id:
            self.refresh_dependencies(current.parent_job_id)
            self.summarize(current.parent_job_id)
        return current

    def _execute_mark_handoff(self, child: AgentJob) -> dict[str, Any] | None:
        """Give Mark the original turn; do not make Milchick discover its files."""
        if str(child.target_agent or "").strip().lower() != "mark":
            return None
        if child.capability not in MARK_AGENT_HANDOFF_CAPABILITIES:
            return None
        raw_message = str(child.input.get("user_message") or "")
        if not raw_message.strip():
            return None

        from agents.bridge import handle_agent_message

        handoff_text = (
            "[LUMEN HANDOFF]\n"
            "This task is handed to you. Read the original user input and any attached image, "
            "inspect the workspace yourself, and decide and execute the smallest safe next step.\n\n"
            "[ORIGINAL USER INPUT]\n"
            f"{raw_message}"
        )
        if child.capability == "loop.business":
            handoff_text += (
                "\n\nStart the Business Loop for this request "
                "(topic/story artifacts only; no application source changes)."
            )
        elif child.capability == "loop.technical":
            handoff_text += (
                "\n\nStart the Technical Loop for this request "
                "(one business-ready Story → technical-plan.md; no application source changes)."
            )
        meta = {
            "message_id": child.source_message_id,
            "chat_id": child.chat_id,
            "thread_id": child.thread_id,
            "chat_type": str(child.input.get("chat_type") or "group"),
            "user_id": child.requested_by,
            "_project_slug": child.project,
            "image_keys": str(child.input.get("image_keys") or ""),
            "_nested_handoff": "1",
            "_suppress_reply": "1",
            "_new_agent_turn": "1",
        }
        try:
            result = handle_agent_message(agent_id="mark", text=handoff_text, meta=meta)
        except Exception as exc:
            return {
                "status": "failed",
                "action": "agent.handoff",
                "error": str(exc)[:300],
                "result": {"summary": "Mark could not take over this task."},
            }
        status = str(result.get("status") or "").strip().lower()
        succeeded = status in {"ok", "delegate"}
        summary = str(result.get("text") or "").strip()
        if not summary:
            summary = "Mark has taken over this task." if succeeded else "Mark could not take over this task."
        payload = {
            "status": "succeeded" if succeeded else "failed",
            "action": "agent.handoff",
            "result": {"summary": summary, "agent_result": result},
        }
        if not succeeded:
            payload["error"] = str(result.get("detail") or status or "agent_handoff_failed")
        return payload

    def _handoff_reply(self, child: AgentJob, receipt: dict[str, Any], *, failed: bool = False) -> None:
        if not child.source_message_id or not child.target_agent:
            return
        result = receipt.get("result") if isinstance(receipt.get("result"), dict) else {}
        text = str(result.get("summary") or "").strip()
        if failed:
            text = text or f"{child.target_agent.title()} could not finish `{child.capability}`: {child.error}"
        if not text:
            return
        try:
            from feishu.messenger import FeishuMessenger

            FeishuMessenger(child.target_agent).safe_reply_text(
                child.source_message_id,
                text,
                reply_in_thread=bool(child.thread_id)
                or str(child.chat_id or "").startswith("oc_"),
            )
        except Exception:
            pass


def _job_create_handoff_text(target: str, capability: str, child: AgentJob) -> str:
    who = (target or "").strip().title() or "the agent"
    phrases = {
        "test_case.generate": "test case generation",
        "scan.run": "code scan",
        "loop.business": "Business Loop",
        "loop.technical": "Technical Loop",
    }
    phrase = phrases.get(capability, (capability or "work").replace(".", " ").replace("_", " "))
    issue = ""
    if isinstance(child.input, dict):
        issue = str(child.input.get("issue_key") or child.input.get("story") or "").strip()
    subject = f"{phrase} for {issue}" if issue else phrase
    status = str(child.status or "").strip().lower()
    if status == "completed":
        return f"{who} finished {subject}."
    if status == "failed":
        return f"{who} failed {subject}."
    if status in {"queued", "blocked", "pending"}:
        return f"{subject[:1].upper() + subject[1:]} is queued with {who}."
    if status in {"running", "in_progress"}:
        return f"{subject[:1].upper() + subject[1:]} is running with {who}."
    return f"I’m handing this to {who}."


def execute_job_action(request: ActionRequest) -> dict[str, Any]:
    broker = AgentJobBroker()
    action = request.action
    args = request.arguments or {}
    resource = request.resource or {}

    if action == "agent.job.create":
        parent = broker.create_parent(
            project=request.project_slug,
            requested_by=request.actor_user_id,
            delegated_by=request.agent_id,
            source_message_id=request.source_message_id,
            chat_id=request.chat_id,
            thread_id=request.thread_id,
            trace_id=request.trace_id,
            input_data=args,
        )
        target = str(args.get("target_agent") or resource.get("target_agent") or "mark").strip().lower()
        capability = str(args.get("capability") or resource.get("capability") or "").strip()
        if not capability:
            raise ValueError("capability required")
        child = broker.create_child(
            parent=parent,
            target_agent=target,
            capability=capability,
            input_data={
                "issue_key": args.get("issue_key") or resource.get("issue_key") or "",
                "story": args.get("story") or resource.get("story") or "",
                "project": request.project_slug,
                **{k: v for k, v in args.items() if k not in {"target_agent", "capability", "depends_on"}},
            },
            depends_on=list(args.get("depends_on") or []),
        )
        if child.status == "ready" and bool(args.get("execute", True)):
            child = broker.execute_ready_child(child)
        summary = broker.summarize(parent.job_id)
        return {
            "parent": parent.to_dict(),
            "child": child.to_dict(),
            "summary": summary,
            "handoff_text": _job_create_handoff_text(target, capability, child),
            "result_delivered": child.status in {"completed", "failed"},
        }

    if action == "agent.job.list":
        jobs = broker.store.list_jobs(project=request.project_slug, limit=int(args.get("limit") or 20))
        return {"jobs": [j.to_dict() for j in jobs]}

    if action == "agent.job.show":
        job_id = str(args.get("job_id") or resource.get("job_id") or "").strip()
        job = broker.store.get(job_id)
        if not job:
            return {"status": "missing", "job_id": job_id}
        payload = job.to_dict()
        if not job.parent_job_id:
            payload["summary"] = broker.summarize(job.job_id)
        else:
            payload["summary"] = broker.summarize(job.parent_job_id)
        return payload

    if action == "agent.job.cancel":
        job_id = str(args.get("job_id") or resource.get("job_id") or "").strip()
        job = broker.store.get(job_id)
        if not job:
            return {"status": "missing", "job_id": job_id}
        job.status = "cancelled"
        broker.store.save(job)
        return job.to_dict()

    if action == "agent.job.retry":
        job_id = str(args.get("job_id") or resource.get("job_id") or "").strip()
        job = broker.store.get(job_id)
        if not job:
            return {"status": "missing", "job_id": job_id}
        job.status = "ready"
        job.error = ""
        broker.store.save(job)
        job = broker.execute_ready_child(job)
        return job.to_dict()

    if action in {"agent.list", "agent.health"}:
        from agents.definitions import list_definitions

        agents = []
        for definition in list_definitions():
            agents.append(
                {
                    "id": definition.id,
                    "display_name": definition.display_name,
                    "role": definition.role,
                    "health": "registered",
                }
            )
        return {"agents": agents}

    if action in {"project.status", "workflow.status", "schedule.status"}:
        return {
            "project": request.project_slug,
            "status": "available",
            "note": "M1.0 returns lightweight operational status only",
        }

    raise ValueError(f"unsupported job action: {action}")
