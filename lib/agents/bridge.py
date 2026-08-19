from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from agents.actions.scan import load_recent_run, save_recent_run, scan_lock_exists
from agents.definitions import ensure_definitions_loaded, get_definition
from agents.dylan.schemas import ConversationFlags
from agents.models import TriggerContext
from agents.parser import parse_dylan_text
from agents.project_resolver import known_project_slugs, load_chat_project_map, resolve_project
from agents.runtime.reply_anchor import remember_outbound
from feishu.cards import ack_card, progress_card, scan_summary_card
from feishu.config import load_agents_config
from feishu.messenger import (
    FeishuMessenger,
    extract_message_id,
    has_pdf_file_citation,
    is_pdf_output_request,
    should_reply_in_thread,
)
from workflows.scan_adapter import ScanAdapter


def _load_workspace_common(workspace: str) -> dict[str, Any]:
    common_path = Path(workspace) / "config" / "common.json"
    if not Path(workspace).is_dir() or not common_path.is_file():
        return {}
    try:
        data = json.loads(common_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _conversation_enabled(config: dict[str, Any], common: dict[str, Any], agent_id: str) -> bool:
    return ConversationFlags.from_common(common, config, agent_id=agent_id).enabled


def _audit_text(value: Any, maximum: int = 4000) -> str:
    return str(value or "").strip()[:maximum]


def _resume_waiting_loop(*, agent: str, meta: dict[str, str]) -> tuple[Any, dict[str, str]]:
    if agent != "mark" or not str(meta.get("chat_id") or "").strip():
        return None, meta
    from agents.jobs.store import AgentJobStore

    store = AgentJobStore()
    try:
        job = store.find_waiting_loop(
            agent_id=agent,
            chat_id=str(meta.get("chat_id") or ""),
            thread_id=str(meta.get("thread_id") or ""),
            parent_id=str(meta.get("parent_id") or ""),
            root_id=str(meta.get("root_id") or ""),
        )
        if job is None:
            return None, meta
        job.status = "running"
        job.result["last_user_message_id"] = str(meta.get("message_id") or "")
        store.save(job)
        updated = dict(meta)
        updated["_project_slug"] = job.project
        updated["_loop_job_id"] = job.job_id
        updated["_loop_capability"] = job.capability
        # Group replies do not always contain root_id. Use the original request
        # as the stable session scope so the pending provider session resumes.
        if not updated.get("root_id"):
            updated["root_id"] = job.source_message_id
        if not updated.get("thread_id") and job.thread_id:
            updated["thread_id"] = job.thread_id
        return job, updated
    finally:
        store.close()


def _finish_waiting_loop(job: Any, result: dict[str, Any]) -> None:
    if job is None:
        return
    from agents.jobs.broker import AgentJobBroker
    from agents.jobs.store import AgentJobStore

    store = AgentJobStore()
    try:
        current = store.get(job.job_id) or job
        broker = AgentJobBroker(store)
        current.result["resume_result"] = result
        result_status = str(result.get("status") or "").strip().lower()
        if result_status not in {"ok", "delegate"}:
            retryable = bool(result.get("retryable"))
            current.status = "waiting_user" if retryable else "failed"
            current.error = str(result.get("detail") or result.get("text") or "loop_resume_failed")[:500]
            if retryable:
                current.result["resume_retryable"] = True
                current.result["result"] = {
                    "summary": str(result.get("text") or "Mark 尚未完成這一輪調查；請在此 thread 回覆「繼續調查」重試。"),
                    "resume_retryable": True,
                }
        elif result.get("pending_clarification"):
            current.status = "waiting_user"
            current.error = ""
            outbound_id = str(result.get("outbound_message_id") or "").strip()
            if outbound_id:
                current.result["question_message_id"] = outbound_id
        else:
            complete, state = broker._loop_complete(current)
            current.result["loop_state"] = state
            current.status = "completed" if complete else "waiting_user"
            current.error = "" if complete else "loop_artifact_not_complete"
            if not complete:
                question = broker._loop_question(current, state)
                nested = current.result.get("result") if isinstance(current.result.get("result"), dict) else {}
                nested["question"] = question
                outbound_id = str(result.get("outbound_message_id") or "").strip()
                if not outbound_id:
                    question_receipt = {"result": {"question": nested["question"]}}
                    broker._handoff_reply(current, question_receipt)
                    outbound_id = str(question_receipt.get("result", {}).get("outbound_message_id") or "").strip()
                if outbound_id:
                    nested["outbound_message_id"] = outbound_id
                    current.result["question_message_id"] = outbound_id
                current.result["result"] = nested
        store.save(current)
        if current.parent_job_id:
            broker.summarize(current.parent_job_id)
    finally:
        store.close()


def _persist_agent_run(run: dict[str, Any], *, meta: dict[str, str], slug: str, action: str, agent_id: str) -> None:
    try:
        from risk.store import GlobalAgentStore

        gs = GlobalAgentStore()
        scan = run.get("scan") if isinstance(run.get("scan"), dict) else {}
        findings = scan.get("findings") if isinstance(scan.get("findings"), list) else []
        gs.save_agent_run(
            {
                "run_id": run.get("run_id"),
                "agent_id": agent_id,
                "project_slug": slug,
                "chat_id": meta.get("chat_id"),
                "thread_id": meta.get("thread_id"),
                "user_id": meta.get("user_id"),
                "action": action,
                "status": run.get("status"),
                "started_at": scan.get("started_at"),
                "completed_at": scan.get("finished_at"),
                "result_path": run.get("result_path"),
                "summary": {
                    "finding_count": len(findings),
                    "high": sum(1 for f in findings if isinstance(f, dict) and str(f.get("severity")) == "High"),
                    "medium": sum(1 for f in findings if isinstance(f, dict) and str(f.get("severity")) == "Medium"),
                },
                "error": run.get("detail") if run.get("status") not in {"completed", "success"} else None,
            }
        )
        if meta.get("chat_id"):
            gs.set_chat_project(str(meta["chat_id"]), slug)
            gs.upsert_conversation_context(
                {
                    "chat_id": meta.get("chat_id"),
                    "thread_id": meta.get("thread_id"),
                    "user_id": meta.get("user_id"),
                    "project_slug": slug,
                    "last_intent": action,
                    "last_run_id": run.get("run_id"),
                    "recent_entities": {"window_days": run.get("window_days")},
                }
            )
        gs.close()
    except Exception:
        pass


def _run_autonomous_worker(
    *,
    agent: str,
    definition: Any,
    text: str,
    meta: dict[str, str],
    probe_common: dict[str, Any],
    config: dict[str, Any],
    flags: ConversationFlags,
    messenger: FeishuMessenger,
    message_id: str,
    chat_id: str,
) -> dict[str, Any]:
    from agents.runtime.observability import Observability, TraceContext, new_trace_id
    from agents.runtime.reaction import ReactionThinkingSession
    from agents.runtime.jobs_pool import run_conversation_job

    trace = TraceContext(
        trace_id=new_trace_id(),
        message_id=message_id,
        chat_id=chat_id,
        thread_id=str(meta.get("thread_id") or ""),
        user_id=str(meta.get("user_id") or ""),
        provider=flags.model.provider,
        model=flags.model.model_name,
        agent_id=agent,
        role=str(getattr(definition, "role", "") or ""),
        workflow=str(getattr(definition, "workflow", "") or ""),
    )

    def _worker() -> dict[str, Any]:
        obs = Observability(agent_id=agent)
        reaction = ReactionThinkingSession(
            messenger=messenger,
            source_message_id=message_id,
            emoji_type=flags.reaction.emoji_type,
            trace=trace,
            obs=obs,
            enabled=flags.reaction.enabled and bool(message_id),
            remove_on_success=flags.reaction.remove_on_success,
            remove_on_failure=flags.reaction.remove_on_failure,
        )
        success = False
        result: dict[str, Any] = {}
        suppress_reply = str(meta.get("_suppress_reply") or "") == "1"
        try:
            obs.emit(trace, "message.received")
            obs.emit(trace, "conversation.request", text=_audit_text(text))
            obs.upsert_trace(trace, state="queued")
            if flags.reaction.add_immediately:
                reaction.start()
            obs.emit(trace, "job.started")
            if flags.autonomous:
                from agents.runtime.autonomous import handle_autonomous_conversation

                result = handle_autonomous_conversation(
                    definition=definition,
                    text=text,
                    meta=meta,
                    common=probe_common,
                    agents_config=config,
                    obs=obs,
                    trace=trace,
                )
            else:
                from agents.dylan.conversation import handle_conversation

                result = handle_conversation(
                    text=text,
                    meta=meta,
                    common=probe_common,
                    agents_config=config,
                    known_slugs=known_project_slugs(),
                    obs=obs,
                    trace=trace,
                )
            if result.get("status") == "delegate":
                obs.emit(
                    trace,
                    "conversation.completed",
                    status="delegated",
                    action=result.get("action"),
                    text=_audit_text(result.get("text")),
                )
                success = True
                return result
            reply_text = str(result.get("text") or "暂无数据。")
            allow_pdf = is_pdf_output_request(text) or has_pdf_file_citation(reply_text)
            if suppress_reply:
                obs.emit(trace, "reply.suppressed")
            else:
                obs.emit(trace, "reply.started")
                reply_in_thread = should_reply_in_thread(meta)
                if message_id:
                    sent = None
                    for attempt in range(4):
                        sent = messenger.safe_reply_text(
                            message_id,
                            reply_text,
                            reply_in_thread=reply_in_thread,
                            allow_pdf=allow_pdf,
                        )
                        if sent is not None:
                            break
                        time.sleep(min(2 ** attempt, 8))
                    if sent is None:
                        obs.emit(trace, "reply.failed", level="ERROR")
                        obs.upsert_trace(trace, reply_status="failed", state="failed", error_code="reply_failed")
                        raise RuntimeError("final reply failed")
                    try:
                        outbound_id = extract_message_id(sent)
                        remember_outbound(
                            message_id=outbound_id,
                            text=reply_text,
                            chat_id=chat_id,
                            agent_id=agent,
                            reply_to=message_id,
                            thread_id=str(meta.get("thread_id") or ""),
                        )
                        result["outbound_message_id"] = outbound_id
                    except Exception:
                        pass
                obs.emit(trace, "reply.succeeded")
            obs.upsert_trace(trace, reply_status="succeeded", state="completed")
            receipts = result.get("action_receipts") if isinstance(result.get("action_receipts"), list) else []
            obs.emit(
                trace,
                "conversation.completed",
                status="completed",
                action=result.get("action"),
                text=_audit_text(reply_text),
                response_mode=result.get("final_response_mode") or result.get("response_mode"),
                clarification=bool(result.get("pending_clarification")),
                action_receipts=[
                    {"action": item.get("action"), "status": item.get("status")}
                    for item in receipts
                    if isinstance(item, dict)
                ],
            )
            obs.emit(trace, "job.completed", latency_ms=result.get("latency_ms"))
            success = True
            return result
        except Exception as exc:
            try:
                obs.emit(trace, "job.failed", error=str(exc)[:300], level="ERROR")
                obs.emit(trace, "conversation.completed", status="failed", error=str(exc)[:300])
                obs.upsert_trace(trace, state="failed", error_code="worker_error")
            except Exception:
                pass
            if message_id and not suppress_reply and result.get("status") not in {"ok", "delegate", "error"}:
                messenger.safe_reply_text(
                    message_id,
                    f"I couldn't finish this turn.\nTrace ID: {trace.trace_id}",
                    reply_in_thread=should_reply_in_thread(meta),
                )
            raise
        finally:
            try:
                reaction.finish(success=success)
            except Exception:
                pass
            try:
                obs.close()
            except Exception:
                pass

    if str(meta.get("_nested_handoff") or "") == "1":
        return _worker()
    queued = run_conversation_job(
        message_id=message_id or f"local-{chat_id}-{meta.get('thread_id')}-{meta.get('user_id')}",
        chat_id=chat_id,
        thread_id=str(meta.get("thread_id") or ""),
        user_id=str(meta.get("user_id") or ""),
        worker=_worker,
    )
    if queued.get("status") == "duplicate":
        return {"status": "duplicate", "detail": "message already processed", "trace_id": trace.trace_id}
    result = queued.get("result") if isinstance(queued.get("result"), dict) else {"status": "queued", "trace_id": trace.trace_id}
    return result


def handle_agent_message(*, agent_id: str, text: str, meta: dict[str, str]) -> dict[str, Any]:
    agent = str(agent_id or "").strip().lower()
    ensure_definitions_loaded()
    definition = get_definition(agent)
    if definition is None:
        return {"status": "ignored", "detail": f"agent {agent} not enabled"}

    config = load_agents_config()
    chat_id = str(meta.get("chat_id") or "").strip()
    user_id = str(meta.get("user_id") or "").strip()
    from agents.security.access_policy import authorize_agent_interaction

    decision = authorize_agent_interaction(agent_id=agent, meta=meta, config=config)
    if not decision.allowed:
        messenger = FeishuMessenger(agent)
        message_id = str(meta.get("message_id") or "").strip()
        detail = decision.reason_code or "access denied"
        if message_id:
            if detail == "DM_ONLY":
                reply = "I only take private DMs for this role."
            elif detail == "AGENT_ACCESS_UNCONFIGURED":
                reply = "This agent isn't configured for access yet (default deny)."
            else:
                reply = (
                    "You're not authorized to talk to this agent here. "
                    f"Your Feishu open_id for this bot is `{user_id or '-'}`. "
                    "Admins are shared across bots via Feishu union_id once identities are linked."
                )
            messenger.safe_reply_text(message_id, reply, reply_in_thread=should_reply_in_thread(meta))
        return {"status": "denied", "detail": detail, "trust_zone": decision.trust_zone}
    meta = dict(meta)
    waiting_job, meta = _resume_waiting_loop(agent=agent, meta=meta)
    if waiting_job is not None:
        meta["_loop_capability"] = waiting_job.capability
    meta["_trust_zone"] = str(decision.trust_zone or "")
    meta["_exposure_mode"] = str(decision.exposure_mode or "")
    meta["_policy_version"] = str(decision.policy_version or "")
    meta["_host_read_allowed"] = "1" if decision.host_read_allowed else "0"
    meta["_mutation_allowed"] = "1" if decision.mutation_allowed else "0"

    messenger = FeishuMessenger(agent)
    message_id = str(meta.get("message_id") or "").strip()
    in_thread = should_reply_in_thread(meta)
    known = known_project_slugs()

    mapped = resolve_project(
        slug=str(meta.get("_project_slug") or ""),
        chat_id=chat_id,
        mapping=load_chat_project_map(),
    )
    probe_common = _load_workspace_common(str(mapped.get("workspace") or "")) if mapped else {}
    flags = ConversationFlags.from_common(probe_common, config, agent_id=agent)

    if _conversation_enabled(config, probe_common, agent):
        if flags.autonomous or (agent == "dylan" and flags.agent_only):
            try:
                result = _run_autonomous_worker(
                    agent=agent,
                    definition=definition,
                    text=text,
                    meta=meta,
                    probe_common=probe_common,
                    config=config,
                    flags=flags,
                    messenger=messenger,
                    message_id=message_id,
                    chat_id=chat_id,
                )
            except Exception as exc:
                if waiting_job is not None:
                    _finish_waiting_loop(
                        waiting_job,
                        {"status": "error", "detail": str(exc)[:500]},
                    )
                raise
            if result.get("status") == "delegate" and agent == "dylan":
                action_name = str(result.get("action") or "")
                params = result.get("params") if isinstance(result.get("params"), dict) else {}
                if action_name == "scan.cancel":
                    recent = load_recent_run() or {}
                    workspace = str(recent.get("workspace") or "").strip()
                    if workspace and scan_lock_exists(workspace):
                        reply = f"Scan {recent.get('run_id')} 仍在运行；V1 请在本机结束对应进程后重试。"
                    else:
                        reply = "没有正在运行的 Scan。"
                    if message_id:
                        messenger.safe_reply_text(message_id, reply, reply_in_thread=in_thread)
                    return {"status": "ok", "action": action_name, "trace_id": result.get("trace_id")}
                from agents.parser import ParsedAction

                action = ParsedAction(name="scan.run", confidence=0.9, source="conversation_v3", params=params)
            else:
                if waiting_job is not None:
                    _finish_waiting_loop(waiting_job, result)
                return result
        elif agent == "dylan":
            from agents.dylan.conversation import handle_conversation
            from agents.dylan.thinking import ThinkingSession

            thinking = None
            if flags.typing.enabled and message_id:
                thinking = ThinkingSession(
                    messenger=messenger,
                    source_message_id=message_id,
                    language="zh-Hans",
                    config=flags.typing,
                    reply_in_thread=in_thread,
                )
                thinking.schedule_start()

            result = handle_conversation(
                text=text,
                meta=meta,
                common=probe_common,
                agents_config=config,
                known_slugs=known,
            )
            typing_meta = result.get("typing") if isinstance(result.get("typing"), dict) else {}
            if thinking is not None:
                if typing_meta.get("language"):
                    thinking.language = str(typing_meta["language"])
                if result.get("fast_path") or not typing_meta.get("enabled", True):
                    thinking._cancel_timers()
                    thinking.completed = True
                    if message_id and result.get("status") != "delegate":
                        messenger.safe_reply_text(message_id, str(result.get("text") or "暂无数据。"), reply_in_thread=in_thread)
                elif result.get("status") == "delegate":
                    thinking._cancel_timers()
                    thinking.completed = True
                else:
                    thinking.complete(str(result.get("text") or "暂无数据。"))
                    return result
            if result.get("status") == "delegate":
                action_name = str(result.get("action") or "")
                params = result.get("params") if isinstance(result.get("params"), dict) else {}
                if action_name == "scan.cancel":
                    recent = load_recent_run() or {}
                    workspace = str(recent.get("workspace") or "").strip()
                    if workspace and scan_lock_exists(workspace):
                        reply = f"Scan {recent.get('run_id')} 仍在运行；V1 请在本机结束对应进程后重试。"
                    else:
                        reply = "没有正在运行的 Scan。"
                    if message_id:
                        messenger.safe_reply_text(message_id, reply, reply_in_thread=in_thread)
                    return {"status": "ok", "action": action_name}
                from agents.parser import ParsedAction

                action = ParsedAction(name="scan.run", confidence=0.9, source="conversation_v2", params=params)
            else:
                if thinking is None and message_id:
                    messenger.safe_reply_text(message_id, str(result.get("text") or "暂无数据。"), reply_in_thread=in_thread)
                return result
        else:
            result = {"status": "ignored", "detail": f"conversation disabled for {agent}"}
            if waiting_job is not None:
                _finish_waiting_loop(waiting_job, result)
            return result
    elif agent != "dylan":
        result = {"status": "ignored", "detail": f"conversation disabled for {agent}"}
        if waiting_job is not None:
            _finish_waiting_loop(waiting_job, result)
        return result
    else:
        action = parse_dylan_text(text, known)

        if action.name.startswith("risk."):
            project = resolve_project(
                slug=str(action.params.get("project") or ""),
                chat_id=chat_id,
                mapping=load_chat_project_map(),
            )
            if project is None:
                if message_id:
                    messenger.safe_reply_text(message_id, "无法解析项目。请写明 slug，例如：mbpass 最近最大的风险是什么？", reply_in_thread=in_thread)
                return {"status": "error", "detail": "project not resolved"}
            workspace = str(project.get("workspace") or "")
            common = _load_workspace_common(workspace)
            project_meta = common.setdefault("project", {})
            if isinstance(project_meta, dict) and not project_meta.get("slug"):
                project_meta["slug"] = str(project.get("slug") or "")
            from agents.dylan.conversation import answer_risk_query

            result = answer_risk_query(
                workspace=Path(workspace),
                common=common,
                action=action.name,
                params={**action.params, "project": str(project.get("slug") or "")},
            )
            if message_id:
                messenger.safe_reply_text(message_id, str(result.get("text") or "暂无风险数据。"), reply_in_thread=in_thread)
            try:
                from risk.store import GlobalAgentStore

                gs = GlobalAgentStore()
                gs.set_chat_project(chat_id, str(project.get("slug") or ""))
                gs.close()
            except Exception:
                pass
            return result

        if action.name == "scan.help":
            if message_id:
                messenger.safe_reply_text(
                    message_id,
                    "我是 Dylan（Engineering Risk Analyst）。\n"
                    "可以：扫描 mbpass 最近七天\n"
                    "或问：最近最大的风险是什么？风险在上升还是下降？哪些问题反复出现？",
                    reply_in_thread=in_thread,
                )
            return {"status": "help", "action": action.name}

        if action.name == "scan.status":
            recent = load_recent_run() or {}
            detail = (
                f"最近 Run: {recent.get('run_id', '无')}\n"
                f"状态: {recent.get('status', 'unknown')}\n"
                f"项目: {recent.get('project', '-')}"
            )
            if message_id:
                messenger.safe_reply_text(message_id, detail, reply_in_thread=in_thread)
            return {"status": "ok", "action": action.name, "recent": recent}

        if action.name == "scan.cancel":
            recent = load_recent_run() or {}
            workspace = str(recent.get("workspace") or "").strip()
            if workspace and scan_lock_exists(workspace):
                reply = f"Scan {recent.get('run_id')} 仍在运行；V1 请在本机结束对应进程后重试。"
            else:
                reply = "没有正在运行的 Scan。"
            if message_id:
                messenger.safe_reply_text(message_id, reply, reply_in_thread=in_thread)
            return {"status": "ok", "action": action.name}

    if agent != "dylan":
        return {"status": "ignored", "detail": f"scan actions not available for {agent}"}

    mapping = load_chat_project_map()
    project = resolve_project(
        slug=str(action.params.get("project") or ""),
        chat_id=chat_id,
        mapping=mapping,
    )
    if project is None:
        if message_id:
            messenger.safe_reply_text(message_id, "无法解析项目。请写明 slug，例如：扫描 mbpass", reply_in_thread=in_thread)
        return {"status": "error", "detail": "project not resolved"}

    slug = str(project.get("slug") or "")
    workspace = str(project.get("workspace") or "")
    if message_id:
        try:
            messenger.reply_card(message_id, ack_card(action.name, slug), reply_in_thread=in_thread)
        except Exception:
            messenger.safe_reply_text(message_id, f"已收到，开始扫描 {slug}", reply_in_thread=in_thread)

    if workspace and scan_lock_exists(workspace):
        if message_id:
            messenger.safe_reply_text(message_id, f"{slug} 已有 Scan 在运行，请稍后再试。", reply_in_thread=in_thread)
        return {"status": "blocked", "detail": "scan lock exists"}

    trigger = TriggerContext(
        source="feishu",
        app_id=str(meta.get("app_id") or ""),
        agent_id=agent,
        user_id=str(meta.get("user_id") or ""),
        chat_id=chat_id,
        thread_id=str(meta.get("thread_id") or ""),
        message_id=message_id,
        chat_type=str(meta.get("chat_type") or ""),
    )
    adapter = ScanAdapter()
    run = adapter.start(
        project_slug=slug,
        window_days=action.params.get("window_days"),
        trigger=trigger,
        dry_run=False,
    )
    save_recent_run({
        "run_id": run.get("run_id"),
        "status": run.get("status"),
        "project": slug,
        "workspace": workspace,
        "result_path": run.get("result_path"),
    })
    _persist_agent_run(run, meta=meta, slug=slug, action="scan.run", agent_id=agent)
    if message_id:
        if run.get("status") == "completed":
            scan = run.get("scan") if isinstance(run.get("scan"), dict) else {}
            try:
                messenger.reply_card(message_id, scan_summary_card(str(run.get("run_id")), scan), reply_in_thread=in_thread)
            except Exception:
                messenger.safe_reply_text(message_id, f"Scan 完成: {run.get('run_id')}", reply_in_thread=in_thread)
        else:
            try:
                messenger.reply_card(
                    message_id,
                    progress_card(str(run.get("run_id")), str(run.get("status")), str(run.get("detail") or "")),
                    reply_in_thread=in_thread,
                )
            except Exception:
                messenger.safe_reply_text(
                    message_id,
                    f"Scan {run.get('status')}: {run.get('detail') or run.get('run_id')}",
                    reply_in_thread=in_thread,
                )
    return {"status": "ok", "action": action.name, "run": run}
