from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

from agents.dylan.context import load_context, resolve_project_slug, save_context
from agents.dylan.guard import validate_response
from agents.dylan.locales import t
from agents.dylan.model_client import get_model_client
from agents.dylan.observability import Observability, TraceContext, prompt_hash
from agents.dylan.safe_formatter import format_safe
from agents.dylan.schemas import (
    ALLOWED_INTENTS,
    INTENT_TOOLS,
    READ_ONLY_TOOLS,
    AgentPlan,
    AgentTask,
    ConversationFlags,
    ToolCall,
)
from agents.dylan.soul_loader import load_soul
from agents.dylan.tools import execute_tool
from risk.store import GlobalAgentStore, RiskStore


class AgentUnavailableError(RuntimeError):
    pass


class DylanAgentController:
    def __init__(
        self,
        *,
        flags: ConversationFlags,
        obs: Observability,
        trace: TraceContext,
        model_client: Any = None,
    ) -> None:
        self.flags = flags
        self.obs = obs
        self.trace = trace
        self.model = model_client

    def run(
        self,
        *,
        text: str,
        meta: dict[str, str],
        common: dict[str, Any] | None = None,
        known_slugs: set[str] | None = None,
        workspace: Path | None = None,
    ) -> dict[str, Any]:
        started = time.time()
        self.obs.emit(self.trace, "job.started")
        self.obs.upsert_trace(self.trace, state="planning")
        global_store = GlobalAgentStore()
        risk_store = None
        try:
            context = load_context(
                global_store,
                chat_id=str(meta.get("chat_id") or ""),
                thread_id=str(meta.get("thread_id") or ""),
                user_id=str(meta.get("user_id") or ""),
            )
            model = self.model or get_model_client(
                self.flags.model,
                workspace=workspace,
                prefer_heuristic=False,
                require_real=self.flags.model.required and self.flags.model.provider != "fake",
            )
            if self.flags.model.required and self.flags.model.provider != "fake":
                if getattr(model, "provider_name", "") == "heuristic":
                    raise AgentUnavailableError("Agent CLI/model unavailable")

            self.obs.emit(self.trace, "agent.planner.started", provider=self.flags.model.provider, model=self.flags.model.model_name)
            plan_started = time.time()
            try:
                plan = model.plan(
                    {
                        "message": text,
                        "language": context.get("original_language") or "",
                        "available_intents": sorted(ALLOWED_INTENTS),
                        "known_projects": sorted(known_slugs or set()),
                        "context": {
                            "project_slug": context.get("project_slug"),
                            "last_intent": context.get("last_intent"),
                            "last_finding_id": context.get("last_finding_id"),
                            "last_result_ids": context.get("last_result_ids") or [],
                            "pending_intent": (context.get("recent_entities") or {}).get("pending_intent")
                            if isinstance(context.get("recent_entities"), dict)
                            else None,
                        },
                        "soul": load_soul(),
                    }
                )
                self.obs.record_agent_invocation(
                    self.trace,
                    phase="planner",
                    latency_ms=int((time.time() - plan_started) * 1000),
                    parse_status="ok",
                    prompt_hash=prompt_hash(text),
                    response_hash=prompt_hash(json.dumps([asdict(t) for t in plan.tasks], default=str)),
                )
                self.obs.emit(
                    self.trace,
                    "agent.planner.succeeded",
                    latency_ms=int((time.time() - plan_started) * 1000),
                    task_count=len(plan.tasks),
                    tool_names=[c.name for task in plan.tasks for c in task.tool_calls],
                )
            except Exception as exc:
                self.obs.record_agent_invocation(
                    self.trace,
                    phase="planner",
                    latency_ms=int((time.time() - plan_started) * 1000),
                    parse_status="failed",
                    error_code="planner_failed",
                )
                self.obs.emit(self.trace, "agent.planner.failed", error=str(exc)[:300], level="ERROR")
                raise AgentUnavailableError(str(exc)) from exc

            plan = self._validate_plan(plan)
            self.obs.emit(
                self.trace,
                "agent.plan.validated",
                task_count=len(plan.tasks),
                intents=[t.intent for t in plan.tasks],
                tool_names=[c.name for task in plan.tasks for c in task.tool_calls],
            )

            if plan.needs_clarification and not plan.tasks:
                text_out = plan.clarification_question or t(plan.language or "en", "no_finding")
                return self._finish(
                    text_out,
                    action="clarification",
                    plan=plan,
                    tool_results=[],
                    started=started,
                    global_store=global_store,
                    context=context,
                    meta=meta,
                    response_mode="clarification",
                )

            project_slug, _ = resolve_project_slug(
                explicit=next((t.project_slug for t in plan.tasks if t.project_slug), None) or "",
                context=context,
                chat_id=str(meta.get("chat_id") or ""),
                store=global_store,
                default_slug=self._default_slug(known_slugs),
            )
            self.trace.project_slug = project_slug
            if workspace is None and project_slug:
                workspace = self._resolve_workspace(project_slug)

            needs_risk_store = any(task.intent.startswith("risk.") for task in plan.tasks)
            if needs_risk_store and workspace is not None:
                risk_store = RiskStore(workspace)

            # scan.run / cancel delegate
            for task in plan.tasks:
                if task.intent in {"scan.run", "scan.cancel"}:
                    return {
                        "status": "delegate",
                        "action": task.intent,
                        "params": {**task.params, "project": project_slug or task.project_slug},
                        "trace_id": self.trace.trace_id,
                        "plan": plan,
                    }

            runtime = {
                "global_store": global_store,
                "risk_store": risk_store,
                "workspace": workspace,
                "common": common or {},
                "meta": meta,
                "context": context,
                "project_slug": project_slug,
            }
            self.obs.upsert_trace(self.trace, state="executing_tools", project_slug=project_slug)
            tool_results = self._execute_tools(plan, runtime=runtime)

            self.obs.upsert_trace(self.trace, state="responding", planner_status="ok")
            self.obs.emit(self.trace, "agent.responder.started")
            resp_started = time.time()
            text_out = ""
            response_mode = "safe_formatter"
            try:
                generated = model.respond(
                    {
                        "language": plan.language,
                        "soul": load_soul(),
                        "user_message": text,
                        "tasks": [
                            {"task_id": t.task_id, "intent": t.intent, "finding_id": t.finding_id}
                            for t in plan.tasks
                        ],
                        "tool_facts": tool_results,
                        "context": {"project_slug": project_slug},
                        "rules": {"no_invention": True, "no_state_mutation_claim": True, "answer_first": True},
                    }
                )
                text_out = generated.text
                response_mode = generated.mode
                self.obs.record_agent_invocation(
                    self.trace,
                    phase="responder",
                    latency_ms=int((time.time() - resp_started) * 1000),
                    parse_status="ok",
                    response_hash=prompt_hash(text_out),
                )
                self.obs.emit(self.trace, "agent.responder.succeeded", latency_ms=int((time.time() - resp_started) * 1000))
            except Exception as exc:
                self.obs.emit(self.trace, "agent.responder.failed", error=str(exc)[:300], level="WARN")
                text_out = ""

            if not text_out:
                text_out = self._compose_multi(plan, tool_results, language=plan.language or "en")
                response_mode = "safe_formatter"

            validation = {"valid": True, "violations": []}
            if self.flags.grounding_guard_enabled:
                self.obs.upsert_trace(self.trace, state="validating")
                validation = validate_response(text_out, tool_results, project_slug=project_slug)
                if not validation.get("valid"):
                    self.obs.emit(self.trace, "grounding.rejected", violations=validation.get("violations"))
                    text_out = self._compose_multi(plan, tool_results, language=plan.language or "en")
                    validation = validate_response(text_out, tool_results, project_slug=project_slug)
                    response_mode = "safe_formatter"
                else:
                    self.obs.emit(self.trace, "grounding.passed")

            primary = plan.tasks[0].intent if plan.tasks else "unsupported"
            return self._finish(
                text_out,
                action=primary,
                plan=plan,
                tool_results=tool_results,
                started=started,
                global_store=global_store,
                context=context,
                meta=meta,
                response_mode=response_mode,
                validation=validation,
                project_slug=project_slug,
            )
        finally:
            if risk_store is not None:
                risk_store.close()
            global_store.close()

    def _validate_plan(self, plan: AgentPlan) -> AgentPlan:
        cleaned: list[AgentTask] = []
        for task in plan.tasks[: max(self.flags.agent_loop.max_tool_calls, 1)]:
            if task.intent not in ALLOWED_INTENTS:
                continue
            allowed = INTENT_TOOLS.get(task.intent)
            calls = []
            for call in task.tool_calls:
                if call.name not in READ_ONLY_TOOLS:
                    continue
                if allowed is not None and call.name not in allowed:
                    continue
                calls.append(call)
            # Deterministic policy: risk/scan intents always get default read tools.
            if not calls and allowed:
                window_days = int((task.params or {}).get("window_days") or 7)
                for name in sorted(allowed):
                    args: dict[str, Any] = {}
                    if task.project_slug:
                        args["project_slug"] = task.project_slug
                    if task.finding_id:
                        args["finding_id"] = task.finding_id
                    if name == "query_recent_findings":
                        args["window_days"] = window_days
                    calls.append(ToolCall(name=name, arguments=args))
            cleaned.append(
                AgentTask(
                    task_id=task.task_id,
                    intent=task.intent,
                    tool_calls=calls,
                    project_slug=task.project_slug,
                    finding_id=task.finding_id,
                    params=task.params,
                )
            )
        if not self.flags.agent_loop.allow_multi_task:
            cleaned = cleaned[:1]
        plan.tasks = cleaned
        return plan

    def _execute_tools(self, plan: AgentPlan, *, runtime: dict[str, Any]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        budget = self.flags.agent_loop.max_total_tool_seconds
        started = time.time()
        count = 0
        for task in plan.tasks:
            for call in task.tool_calls:
                if count >= self.flags.agent_loop.max_tool_calls:
                    break
                if time.time() - started > budget:
                    break
                count += 1
                args = dict(call.arguments)
                if runtime.get("project_slug") and "project_slug" not in args:
                    args["project_slug"] = runtime["project_slug"]
                if task.finding_id and "finding_id" not in args:
                    args["finding_id"] = task.finding_id
                self.obs.emit(self.trace, "tool.started", tool=call.name, task_id=task.task_id)
                t0 = time.time()
                result = execute_tool(call.name, args, runtime=runtime)
                latency = int((time.time() - t0) * 1000)
                data = result.get("data") if isinstance(result.get("data"), dict) else {}
                items = data.get("items") if isinstance(data.get("items"), list) else None
                self.obs.record_tool_invocation(
                    self.trace,
                    task_id=task.task_id,
                    tool_name=call.name,
                    arguments_summary=json.dumps({k: args[k] for k in list(args)[:5]}, ensure_ascii=False)[:200],
                    status=result.get("status"),
                    result_count=len(items) if items is not None else (1 if data else 0),
                    freshness=json.dumps(result.get("freshness") or {}),
                    latency_ms=latency,
                    error_code=";".join(result.get("errors") or [])[:120] or None,
                )
                event = "tool.succeeded" if result.get("status") in {"ok", "empty", "not_found"} else "tool.failed"
                self.obs.emit(self.trace, event, tool=call.name, latency_ms=latency, status=result.get("status"))
                results.append(result)
        return results

    def _compose_multi(self, plan: AgentPlan, tool_results: list[dict[str, Any]], *, language: str) -> str:
        chunks = []
        for task in plan.tasks:
            router_like = type("R", (), {"needs_clarification": False, "clarification_question": None, "params": task.params or {}})()
            chunk = format_safe(
                intent=task.intent,
                router=router_like,  # type: ignore[arg-type]
                tool_results=tool_results,
                language=language,
            )
            if chunk:
                chunks.append(chunk)
        return "\n\n".join(chunks) if chunks else t(language, "no_risk_data")

    def _finish(
        self,
        text_out: str,
        *,
        action: str,
        plan: AgentPlan,
        tool_results: list[dict[str, Any]],
        started: float,
        global_store: GlobalAgentStore,
        context: dict[str, Any],
        meta: dict[str, str],
        response_mode: str,
        validation: dict[str, Any] | None = None,
        project_slug: str = "",
    ) -> dict[str, Any]:
        last_result_ids = None
        for tool_name in ("query_top_risks", "query_unresolved_findings"):
            hit = next((r for r in tool_results if r.get("tool") == tool_name), None)
            if hit and isinstance((hit.get("data") or {}).get("items"), list):
                last_result_ids = [str(i.get("id")) for i in hit["data"]["items"] if isinstance(i, dict) and i.get("id")]
                break
        finding_id = next((t.finding_id for t in plan.tasks if t.finding_id), None) or (
            last_result_ids[0] if last_result_ids else context.get("last_finding_id")
        )
        save_context(
            global_store,
            {
                "chat_id": meta.get("chat_id"),
                "thread_id": meta.get("thread_id"),
                "user_id": meta.get("user_id"),
                "project_slug": project_slug or None,
                "last_intent": action,
                "last_finding_id": finding_id,
                "last_result_ids": last_result_ids,
                "recent_entities": {"trace_id": self.trace.trace_id},
                "original_language": plan.language,
            },
        )
        if project_slug and meta.get("chat_id"):
            global_store.set_chat_project(str(meta["chat_id"]), project_slug)
        latency_ms = int((time.time() - started) * 1000)
        self.obs.emit(self.trace, "context.saved", project_slug=project_slug)
        self.obs.upsert_trace(
            self.trace,
            state="completed",
            responder_status="ok",
            completed_at=None,
            latency_ms=latency_ms,
            project_slug=project_slug,
        )
        return {
            "status": "ok",
            "action": action,
            "text": text_out,
            "trace_id": self.trace.trace_id,
            "tool_results": tool_results,
            "validation": validation or {"valid": True, "violations": []},
            "project_slug": project_slug,
            "response_mode": response_mode,
            "latency_ms": latency_ms,
            "plan": {
                "language": plan.language,
                "confidence": plan.confidence,
                "tasks": [{"intent": t.intent, "task_id": t.task_id} for t in plan.tasks],
            },
            "flags": {"conversation_v3": True, "routing_mode": "agent_only"},
        }

    def _default_slug(self, known: set[str] | None) -> str:
        if known and len(known) == 1:
            return next(iter(known))
        try:
            import sys
            from agents.project_resolver import known_project_slugs

            scripts = Path(__file__).resolve().parents[2] / "scripts"
            if str(scripts) not in sys.path:
                sys.path.insert(0, str(scripts))
            from projects_registry import load_config, load_registry

            cfg = load_config()
            slug = str(cfg.get("default_project_slug") or "").strip()
            if slug:
                return slug
            default_id = str(cfg.get("default_project_id") or "").strip()
            if default_id:
                for project in load_registry().get("projects", []):
                    if str(project.get("id") or "") == default_id:
                        return str(project.get("slug") or "").strip()
            known_all = sorted(known_project_slugs())
            if len(known_all) == 1:
                return known_all[0]
        except Exception:
            return ""
        return ""

    def _resolve_workspace(self, slug: str) -> Path | None:
        try:
            from agents.project_resolver import resolve_project

            project = resolve_project(slug=slug)
            if project and project.get("workspace"):
                return Path(str(project["workspace"]))
        except Exception:
            return None
        return None
