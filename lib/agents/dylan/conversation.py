from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any

from agents.dylan.context import load_context, resolve_project_slug, save_context
from agents.dylan.guard import validate_response
from agents.dylan.locales import t
from agents.dylan.model_client import get_model_client
from agents.dylan.normalizer import normalize_message
from agents.dylan.responder import compose_response
from agents.dylan.router import route_message
from agents.dylan.safe_formatter import format_safe
from agents.dylan.schemas import ALLOWED_INTENTS, ConversationFlags, RouterResult
from agents.dylan.semantic_router import semantic_route
from agents.dylan.soul_loader import load_soul
from agents.dylan.tools import execute_tool
from risk.models import RiskConfig
from risk.queries import explain_finding, overdue_high, recurring, top_risks, trend
from risk.store import GlobalAgentStore, RiskStore


def _template_answer(action: str, payload: dict[str, Any]) -> str:
    if action == "risk.trend":
        if payload.get("status") != "ok":
            return "目前还没有足够的 Project Risk 历史。"
        return (
            f"当前 Project Risk 为 {payload.get('latest_score')}（{payload.get('latest_band')}），"
            f"相对上次 Δ {payload.get('delta')}，趋势 {payload.get('direction')}。"
            f" Open High={payload.get('open_high')}, Reopened={payload.get('reopened')}, "
            f"Overdue High={payload.get('overdue_high')}。"
        )
    if action == "risk.top":
        items = payload.get("items") if isinstance(payload.get("items"), list) else []
        if not items:
            return "当前没有 Open / Reopened Finding。"
        lines = ["目前真正值得注意的不是数量，而是这些高分项："]
        for item in items[:5]:
            lines.append(
                f"- [{item.get('effective_severity')}/{item.get('current_risk_band')}] "
                f"{item.get('title')} (score={item.get('current_risk_score')}, id={item.get('id')})"
            )
        return "\n".join(lines)
    if action == "risk.recurring":
        items = payload.get("items") if isinstance(payload.get("items"), list) else []
        if not items:
            return "没有观察到明显的复发 Finding。"
        lines = ["这些模式在重复出现："]
        for item in items[:5]:
            lines.append(
                f"- {item.get('title')} (recurrence={item.get('recurrence_count')}, "
                f"reopened={item.get('reopened_count')})"
            )
        return "\n".join(lines)
    if action == "risk.overdue":
        items = payload.get("items") if isinstance(payload.get("items"), list) else []
        if not items:
            return "没有超过逾期阈值的 High Finding。"
        lines = ["这些 High 已经拖得够久了："]
        for item in items[:5]:
            lines.append(f"- {item.get('title')} ({item.get('age_days')} days, id={item.get('id')})")
        return "\n".join(lines)
    if action in {"risk.explain", "risk.why_severity"}:
        if payload.get("status") != "ok":
            return "找不到对应的 Finding。"
        finding = payload.get("finding") or {}
        adjustments = payload.get("severity_adjustments") or []
        links = payload.get("links") or []
        lines = [
            f"Finding: {finding.get('title')}",
            f"Source severity={finding.get('source_severity')}, effective={finding.get('effective_severity')}",
            f"Score={finding.get('current_risk_score')} band={finding.get('current_risk_band')}",
            f"Recurrence={finding.get('recurrence_count')} reopened={finding.get('reopened_count')}",
        ]
        if adjustments:
            latest = adjustments[0]
            lines.append(
                f"Severity adjustment: {latest.get('source_severity')} → {latest.get('effective_severity')} "
                f"({latest.get('reason_codes')})"
            )
        if links:
            for link in links:
                lines.append(f"{link.get('type')}: {link.get('external_id') or ''} {link.get('url') or ''}".strip())
        else:
            lines.append("No linked Jira/PR in the risk store.")
        return "\n".join(lines)
    return "我只能基于已存储的风险证据回答。"


def answer_risk_query(
    *,
    workspace: Path,
    common: dict[str, Any],
    action: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    config = RiskConfig.from_common(common)
    store = RiskStore(workspace)
    try:
        project_slug = str(params.get("project") or "").strip()
        if not project_slug:
            project = common.get("project") if isinstance(common.get("project"), dict) else {}
            project_slug = str(project.get("slug") or project.get("display_name") or workspace.parent.name).strip()
            if " " in project_slug:
                project_slug = project_slug.lower().replace(" ", "-")
        payload: dict[str, Any]
        if action == "risk.trend":
            payload = trend(store, project_slug)
        elif action == "risk.top":
            payload = {"items": top_risks(store, project_slug)}
        elif action == "risk.recurring":
            payload = {"items": recurring(store, project_slug)}
        elif action == "risk.overdue":
            payload = {"items": overdue_high(store, project_slug, config)}
        elif action in {"risk.explain", "risk.why_severity"}:
            payload = explain_finding(store, str(params.get("finding_id") or ""))
        else:
            payload = {"status": "unsupported"}
        text = _template_answer(action, payload)
        return {"status": "ok", "action": action, "text": text, "payload": payload}
    finally:
        store.close()


def _default_project_slug() -> str:
    try:
        from agents.project_resolver import known_project_slugs
        import sys
        from pathlib import Path

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
        known = sorted(known_project_slugs())
        if len(known) == 1:
            return known[0]
    except Exception:
        return ""
    return ""


def _resolve_workspace(project_slug: str) -> Path | None:
    if not project_slug:
        return None
    try:
        from agents.project_resolver import resolve_project

        project = resolve_project(slug=project_slug)
        if project and project.get("workspace"):
            return Path(str(project["workspace"]))
    except Exception:
        return None
    return None


def _is_fast_path(router: RouterResult) -> bool:
    return router.intent in {
        "conversation.greeting",
        "conversation.thanks",
        "conversation.agent_identity",
        "conversation.agent_relationship",
        "conversation.capabilities",
        "scan.cancel",
    } and router.source.startswith(("rule:", "heuristic:greeting", "heuristic:identity", "heuristic:relationship"))


def handle_conversation(
    *,
    text: str,
    meta: dict[str, str],
    common: dict[str, Any] | None = None,
    agents_config: dict[str, Any] | None = None,
    known_slugs: set[str] | None = None,
    model_client: Any = None,
    obs: Any = None,
    trace: Any = None,
) -> dict[str, Any]:
    started = time.time()
    flags = ConversationFlags.from_common(common, agents_config)
    if flags.agent_only:
        from agents.dylan.agent_controller import AgentUnavailableError, DylanAgentController
        from agents.dylan.observability import Observability, TraceContext, new_trace_id

        owned_obs = obs is None
        obs_obj = obs or Observability()
        trace_obj = trace or TraceContext(
            trace_id=new_trace_id(),
            message_id=str(meta.get("message_id") or ""),
            chat_id=str(meta.get("chat_id") or ""),
            thread_id=str(meta.get("thread_id") or ""),
            user_id=str(meta.get("user_id") or ""),
            provider=flags.model.provider,
            model=flags.model.model_name,
        )
        try:
            obs_obj.emit(trace_obj, "message.received")
            controller = DylanAgentController(
                flags=flags,
                obs=obs_obj,
                trace=trace_obj,
                model_client=model_client,
            )
            workspace = None
            mapped_slug = ""
            try:
                from agents.project_resolver import resolve_project
                from agents.project_resolver import load_chat_project_map

                mapped = resolve_project(chat_id=str(meta.get("chat_id") or ""), mapping=load_chat_project_map())
                if mapped and mapped.get("workspace"):
                    workspace = Path(str(mapped["workspace"]))
                    mapped_slug = str(mapped.get("slug") or "")
            except Exception:
                workspace = None
            if workspace is None:
                workspace = _resolve_workspace(_default_project_slug())
            result = controller.run(
                text=text,
                meta=meta,
                common=common,
                known_slugs=known_slugs,
                workspace=workspace,
            )
            if mapped_slug and not result.get("project_slug"):
                result["project_slug"] = mapped_slug
            result["typing"] = {"enabled": False}
            result.setdefault("flags", {})["conversation_v3"] = True
            return result
        except AgentUnavailableError as exc:
            obs_obj.emit(trace_obj, "job.failed", error=str(exc)[:300], level="ERROR")
            obs_obj.upsert_trace(trace_obj, state="failed", error_code="agent_unavailable", planner_status="failed")
            language = "en"
            if any("\u4e00" <= ch <= "\u9fff" for ch in text):
                language = "zh-Hant" if any(tok in text for tok in ("麼", "們", "這", "個")) else "zh-Hans"
            detail = str(exc).lower()
            key = "agent_auth_required" if ("authentication required" in detail or "agent login" in detail or "cursor_api_key" in detail) else "agent_unavailable"
            msg = t(language, key)
            return {
                "status": "error",
                "action": "agent.unavailable",
                "text": f"{msg}\nTrace ID: {trace_obj.trace_id}",
                "trace_id": trace_obj.trace_id,
                "error": str(exc)[:300],
                "typing": {"enabled": False},
                "flags": {"conversation_v3": True, "routing_mode": "agent_only"},
            }
        finally:
            if owned_obs:
                obs_obj.close()

    message = normalize_message(text, known_slugs)
    global_store = GlobalAgentStore()
    risk_store = None
    try:
        context = load_context(
            global_store,
            chat_id=str(meta.get("chat_id") or ""),
            thread_id=str(meta.get("thread_id") or ""),
            user_id=str(meta.get("user_id") or ""),
        )
        # Preserve pending clarification fields from recent_entities if present.
        pending = context.get("recent_entities") if isinstance(context.get("recent_entities"), dict) else {}
        if pending.get("pending_intent"):
            context["pending_intent"] = pending.get("pending_intent")

        deterministic = route_message(message, context=context, known_slugs=known_slugs)
        use_semantic = True
        if deterministic.source.startswith("rule:") and deterministic.confidence >= 0.9:
            if deterministic.intent in {"scan.run", "scan.cancel", "conversation.greeting"} or message.finding_id or message.run_id:
                use_semantic = False
        if use_semantic:
            model = get_model_client(flags.model, workspace=_resolve_workspace(_default_project_slug()), prefer_heuristic=not flags.llm_router_enabled)
            router = semantic_route(
                {
                    "message": message.original_text,
                    "language": message.language,
                    "available_intents": sorted(ALLOWED_INTENTS),
                    "context": {
                        "project_slug": context.get("project_slug"),
                        "last_intent": context.get("last_intent"),
                        "last_finding_id": context.get("last_finding_id"),
                        "last_result_ids": context.get("last_result_ids") or [],
                        "pending_intent": context.get("pending_intent"),
                    },
                    "known_projects": sorted(known_slugs or set()),
                },
                model_client=model,
                llm_enabled=flags.llm_router_enabled,
            )
            if router.confidence < 0.82 and deterministic.confidence >= router.confidence and deterministic.intent != "scan.help":
                if deterministic.intent != "unsupported":
                    router = deterministic
        else:
            router = deterministic

        project_needed = router.intent.startswith("risk.") or router.intent in {"scan.run", "scan.status", "scan.summary"}
        project_slug, project_source = resolve_project_slug(
            explicit=str(router.params.get("project") or router.project_slug or message.project_slug or ""),
            context=context,
            chat_id=str(meta.get("chat_id") or ""),
            store=global_store,
            default_slug=_default_project_slug(),
        )
        if project_needed and not project_slug and router.intent.startswith("risk."):
            router.needs_clarification = True
            router.clarification_question = t(message.language, "no_project")
            router.intent = "clarification.project"

        workspace = _resolve_workspace(project_slug) if project_slug else None
        common_data = common if isinstance(common, dict) else {}
        if workspace is not None:
            common_path = workspace / "config" / "common.json"
            if common_path.is_file():
                try:
                    import json

                    loaded = json.loads(common_path.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        common_data = loaded
                except Exception:
                    pass
            if router.intent.startswith("risk."):
                risk_store = RiskStore(workspace)

        if router.intent in {"scan.run", "scan.cancel"}:
            return {
                "status": "delegate",
                "action": router.intent,
                "params": {**router.params, "project": project_slug or router.params.get("project")},
                "router": router,
                "message": message,
                "flags": flags,
                "fast_path": True,
            }

        runtime = {
            "global_store": global_store,
            "risk_store": risk_store,
            "workspace": workspace,
            "common": common_data,
            "meta": meta,
            "context": context,
            "project_slug": project_slug,
        }
        tool_results = []
        for call in router.tool_calls:
            args = dict(call.arguments)
            if project_slug and "project_slug" not in args:
                args["project_slug"] = project_slug
            if router.finding_id and "finding_id" not in args:
                args["finding_id"] = router.finding_id
            tool_results.append(execute_tool(call.name, args, runtime=runtime))

        response_mode = "deterministic"
        text_out = ""
        if flags.llm_response_enabled and not router.needs_clarification:
            try:
                model = get_model_client(flags.model, workspace=workspace or _resolve_workspace(_default_project_slug()))
                generated = model.respond(
                    {
                        "intent": router.intent,
                        "language": message.language,
                        "soul": load_soul(),
                        "user_message": message.original_text,
                        "context": {"project_slug": project_slug, **{k: context.get(k) for k in ("last_intent", "last_finding_id")}},
                        "tool_facts": tool_results,
                        "rules": {"no_invention": True, "no_state_mutation_claim": True, "answer_first": True},
                    }
                )
                text_out = generated.text
                response_mode = generated.mode
            except Exception:
                text_out = ""
                response_mode = "model_failed"

        if not text_out:
            composed = compose_response(
                intent=router.intent,
                router=router,
                tool_results=tool_results,
                language=message.language,
                context=context,
            )
            text_out = str(composed.get("text") or "")
            response_mode = str(composed.get("mode") or "deterministic")

        validation = {"valid": True, "violations": []}
        if flags.grounding_guard_enabled and router.intent.startswith(("risk.", "scan.", "conversation.follow_up")):
            validation = validate_response(text_out, tool_results, project_slug=project_slug)
            if not validation.get("valid"):
                text_out = format_safe(
                    intent=router.intent,
                    router=router,
                    tool_results=tool_results,
                    language=message.language,
                    context=context,
                )
                validation = validate_response(text_out, tool_results, project_slug=project_slug)
                response_mode = "safe_formatter"

        last_result_ids = None
        for tool_name in ("query_top_risks", "query_unresolved_findings"):
            hit = next((r for r in tool_results if r.get("tool") == tool_name), None)
            if hit and isinstance((hit.get("data") or {}).get("items"), list):
                last_result_ids = [str(i.get("id")) for i in hit["data"]["items"] if isinstance(i, dict) and i.get("id")]
                break
        finding_id = router.finding_id or (
            (last_result_ids[0] if last_result_ids else None) or context.get("last_finding_id")
        )
        run_data = next((r.get("data") for r in tool_results if r.get("tool") == "get_recent_scan_status"), None)
        last_run_id = run_data.get("run_id") if isinstance(run_data, dict) else None

        recent_entities = {
            "project_source": project_source,
            "window_days": router.params.get("window_days"),
        }
        if router.needs_clarification and router.intent.startswith("clarification."):
            recent_entities["pending_intent"] = router.params.get("pending_intent") or context.get("last_intent") or "risk.finding_links"
        elif router.intent == "risk.finding_links" and router.needs_clarification:
            recent_entities["pending_intent"] = "risk.finding_links"

        context_payload = {
            "chat_id": meta.get("chat_id"),
            "thread_id": meta.get("thread_id"),
            "user_id": meta.get("user_id"),
            "project_slug": project_slug or None,
            "last_intent": router.intent,
            "last_run_id": last_run_id,
            "last_finding_id": finding_id,
            "recent_entities": recent_entities,
            "original_language": message.language,
        }
        if last_result_ids is not None:
            context_payload["last_result_ids"] = last_result_ids
        save_context(global_store, context_payload)
        if project_slug and meta.get("chat_id"):
            global_store.set_chat_project(str(meta["chat_id"]), project_slug)

        latency_ms = int((time.time() - started) * 1000)
        try:
            global_store.log_conversation(
                {
                    "message_id": meta.get("message_id"),
                    "chat_id": meta.get("chat_id"),
                    "thread_id": meta.get("thread_id"),
                    "user_id": meta.get("user_id"),
                    "agent_id": "dylan",
                    "original_text_hash": hashlib.sha256(message.original_text.encode("utf-8")).hexdigest()[:16],
                    "normalized_text": message.normalized_text[:200],
                    "resolved_project": project_slug,
                    "router_source": router.source,
                    "intent": router.intent,
                    "confidence": router.confidence,
                    "tool_calls": [{"name": c.name, "arguments": c.arguments} for c in router.tool_calls],
                    "response_mode": response_mode,
                    "validation_result": validation,
                    "latency_ms": latency_ms,
                }
            )
        except Exception:
            pass

        return {
            "status": "ok",
            "action": router.intent,
            "text": text_out,
            "router": {
                "intent": router.intent,
                "confidence": router.confidence,
                "source": router.source,
                "needs_clarification": router.needs_clarification,
            },
            "tool_results": tool_results,
            "validation": validation,
            "project_slug": project_slug,
            "fast_path": _is_fast_path(router),
            "flags": {
                "conversation_v2": flags.enabled,
                "llm_router": flags.llm_router_enabled,
                "llm_response": flags.llm_response_enabled,
                "grounding_guard": flags.grounding_guard_enabled,
                "typing": flags.typing.enabled,
            },
            "typing": {
                "enabled": flags.typing.enabled and not _is_fast_path(router),
                "config": flags.typing,
                "language": message.language,
            },
            "latency_ms": latency_ms,
            "response_mode": response_mode,
        }
    finally:
        if risk_store is not None:
            risk_store.close()
        global_store.close()
