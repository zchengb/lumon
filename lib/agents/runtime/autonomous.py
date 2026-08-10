from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Optional

from agents.definitions import AgentDefinition
from agents.dylan.schemas import ConversationFlags
from agents.project_resolver import known_project_slugs, load_chat_project_map, resolve_project
from agents.runner import default_runner
from agents.runtime.cursor_runtime import CursorAgentRuntime
from agents.runtime.final_response import extract_final_response, prefer_action_summary
from agents.runtime.interaction import (
    action_missing_fields,
    clarification_choice_hint,
    clarification_question,
    current_version_for_workspace,
    format_clarification_reply,
    interaction_contract_prompt,
    normalize_clarification,
    should_supersede_pending,
    version_upgrade_choices,
)
from agents.runtime.loop_intent import classify_loop_intent, loop_confirmation_text, loop_gateway_prompt
from agents.runtime.observability import Observability, TraceContext, new_trace_id
from agents.runtime.reply_anchor import format_anchored_user_message, resolve_reply_anchor
from agents.runtime.session_store import SessionStore, conversation_scope_id, session_contract_current
from agents.security.access_policy import authorize_agent_interaction, classify_authorization_intent, security_context_prompt
from agents.security.flags import workspace_isolation_v2_enabled
from agents.security.trusted import execute_trusted_actions, trusted_context_from_meta
from feishu.messenger import FeishuMessenger


class AutonomousUnavailableError(RuntimeError):
    pass


_RESUME_RETRY_TOKENS = (
    "resume",
    "session",
    "not found",
    "invalid",
    "no result event",
    "stream-json",
    "failed to reach",
    "cursor api",
    "empty stream",
)


def _user_facing_agent_error(error: str, trace_id: str) -> str:
    lower = (error or "").lower()
    if "sandbox_unavailable" in lower or "security_error" in lower:
        return (
            "I can't run that turn because the secure Cursor sandbox is unavailable. "
            "Conversation agents stay offline until security-check passes.\n"
            f"Trace ID: {trace_id}"
        )
    if any(tok in lower for tok in ("failed to reach", "cursor api", "proxy", "https_proxy")):
        return (
            "I couldn't reach the Cursor Agent service just now, so I couldn't finish that turn.\n"
            f"Trace ID: {trace_id}"
        )
    if "no result event" in lower or "stream-json" in lower or "empty stream" in lower:
        return (
            "My workspace agent run ended without a usable answer. Retrying after `/new` usually helps.\n"
            f"Trace ID: {trace_id}"
        )
    if "timed_out" in lower or "timeout" in lower:
        return (
            "That investigation took too long and was stopped before I could answer.\n"
            f"Trace ID: {trace_id}"
        )
    return (
        "I couldn't finish this turn cleanly.\n"
        f"Trace ID: {trace_id}"
    )


_IMAGE_SUFFIXES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
}


def _feishu_image_keys(meta: dict[str, str]) -> list[str]:
    raw = meta.get("image_keys")
    if isinstance(raw, list):
        values = raw
    else:
        try:
            values = json.loads(str(raw or "[]"))
        except Exception:
            values = []
    if not isinstance(values, list):
        return []
    return list(dict.fromkeys(str(value or "").strip() for value in values if str(value or "").strip()))[:4]


def _prepare_feishu_image_context(
    *,
    meta: dict[str, str],
    messenger: FeishuMessenger,
) -> tuple[str, Path | None]:
    keys = _feishu_image_keys(meta)
    message_id = str(meta.get("message_id") or "").strip()
    if not keys or not message_id:
        return "", None
    temp_dir = Path(tempfile.mkdtemp(prefix="lumen-feishu-"))
    paths: list[Path] = []
    for index, image_key in enumerate(keys, start=1):
        resource = messenger.safe_get_message_resource(message_id, image_key, resource_type="image")
        if not resource:
            continue
        body, content_type = resource
        if not body:
            continue
        suffix = _IMAGE_SUFFIXES.get(str(content_type or "").strip().lower(), ".img")
        path = temp_dir / f"image-{index}{suffix}"
        path.write_bytes(body)
        paths.append(path)
    if not paths:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return (
            "[FEISHU IMAGE ATTACHMENT]\n"
            "The user attached an image, but Lumen could not download it. "
            "Do not claim to have inspected it; ask the user to resend it or check the bot's Feishu message-resource permission.",
            None,
        )
    lines = [
        "[FEISHU IMAGE ATTACHMENT]",
        "The user attached the following image(s). Open and inspect them before answering; do not treat the attachment marker as the image content:",
    ]
    lines.extend(f"- {path}" for path in paths)
    return "\n".join(lines), temp_dir


def _enrich_clarification(clarification: dict[str, Any], workspace: Path) -> dict[str, Any]:
    action = str(clarification.get("action") or "").strip()
    if action not in {"delivery.quick_change", "jira.workitem.create"}:
        return clarification
    missing = clarification.get("missing") if isinstance(clarification.get("missing"), list) else []
    values: dict[str, Any] = {}
    for key in ("resource", "arguments"):
        item = clarification.get(key)
        if isinstance(item, dict):
            values.update(item)
    request = " ".join(
        str(values.get(key) or "")
        for key in ("summary", "description", "request", "task", "change", "change_type")
    ).casefold()
    change_type = str(values.get("change_type") or "").casefold()
    is_version_question = "target_version" in missing or change_type in {"version", "version_bump", "upgrade_version"} or bool(
        re.search(r"\b(version|upgrade|bump)\b|版本|升级|更新版本", request)
    )
    if not is_version_question:
        return clarification
    enriched = dict(clarification)
    choices = enriched.get("choices") if isinstance(enriched.get("choices"), list) else []
    values.update({"request": request})
    current_version = current_version_for_workspace(workspace, values)
    if not choices:
        choices = version_upgrade_choices(current_version)
    enriched["choices"] = choices[:4]
    if current_version:
        enriched["current_version"] = current_version
    return enriched


def _loop_gateway_result(
    *,
    action: str,
    text: str,
    pending: dict[str, Any] | None,
    trace: TraceContext,
    session: dict[str, Any],
    project_slug: str,
    workspace: Path,
    agent_id: str,
    bootstrap: bool,
) -> dict[str, Any]:
    return {
        "status": "ok",
        "action": action,
        "text": text,
        "final_response_mode": "loop_confirmation",
        "final_response_valid": True,
        "action_receipts": [],
        "pending_clarification": pending,
        "trace_id": trace.trace_id,
        "session_id": session["session_id"],
        "provider_session_id": session.get("provider_session_id") or "",
        "project_slug": project_slug,
        "workspace": str(workspace),
        "agent_id": agent_id,
        "latency_ms": 0,
        "tool_events": [],
        "bootstrap": bootstrap,
        "typing": {"enabled": False},
        "flags": {"conversation_v4": True, "mode": "loop_gateway"},
    }


def handle_autonomous_conversation(
    *,
    definition: AgentDefinition,
    text: str,
    meta: dict[str, str],
    common: dict[str, Any] | None = None,
    agents_config: dict[str, Any] | None = None,
    runtime: CursorAgentRuntime | None = None,
    obs: Observability | None = None,
    trace: TraceContext | None = None,
) -> dict[str, Any]:
    agent_id = str(definition.id or "").strip().lower()
    flags = ConversationFlags.from_common(common, agents_config, agent_id=agent_id)
    if not flags.autonomous:
        raise AutonomousUnavailableError("autonomous_workspace mode disabled")

    chat_id = str(meta.get("chat_id") or "")
    thread_id = str(meta.get("thread_id") or "")
    user_id = str(meta.get("user_id") or "")
    message_id = str(meta.get("message_id") or "")
    stripped = text.strip()
    reset = stripped.lower() in {"/new", "新开话题", "重新开始", "new session"}
    access = authorize_agent_interaction(agent_id=agent_id, meta=meta, config=agents_config)
    if not access.allowed:
        return {
            "status": "denied",
            "action": "access.denied",
            "text": "You're not authorized to talk to this agent here.",
            "detail": access.reason_code,
            "trust_zone": access.trust_zone,
        }
    security_block = security_context_prompt(access)

    mapped = resolve_project(chat_id=chat_id, mapping=load_chat_project_map())
    project_slug = str((mapped or {}).get("slug") or "")
    if not project_slug:
        known = sorted(known_project_slugs())
        project_slug = known[0] if len(known) == 1 else ""
    slug, workspace = definition.resolve_workspace(project_slug, chat_id)
    definition.ensure_workspace_contract(workspace=workspace, project_slug=slug)

    try:
        from risk.store import GlobalAgentStore

        gs = GlobalAgentStore()
        try:
            if chat_id and user_id:
                gs.upsert_conversation_context(
                    {
                        "chat_id": chat_id,
                        "thread_id": thread_id,
                        "user_id": user_id,
                        "project_slug": slug,
                        "last_intent": f"{agent_id}.message",
                    }
                )
            if chat_id and slug:
                gs.set_chat_project(chat_id, slug)
        finally:
            gs.close()
    except Exception:
        pass

    scope = conversation_scope_id(
        agent_id=agent_id,
        chat_id=chat_id,
        thread_id=thread_id,
        root_id=str(meta.get("root_id") or meta.get("parent_id") or ""),
        message_id=message_id,
        chat_type=str(meta.get("chat_type") or ""),
        project_slug=slug,
        user_id=user_id,
        scope=flags.session_scope,
    )

    owned_obs = obs is None
    obs = obs or Observability(agent_id=agent_id)
    store = SessionStore(obs.store)
    parent_id = str(meta.get("parent_id") or "").strip()
    root_id = str(meta.get("root_id") or "").strip()
    anchored_text = text
    messenger = FeishuMessenger(agent_id)
    if parent_id or root_id:
        anchor = resolve_reply_anchor(
            messenger=messenger,
            parent_id=parent_id,
            root_id=root_id,
            agent_id=agent_id,
        )
        if anchor:
            anchored_text = format_anchored_user_message(
                user_message=text,
                parent_id=parent_id or root_id,
                anchor_text=anchor,
            )
    if trace is None:
        trace = TraceContext(
            trace_id=new_trace_id(),
            message_id=message_id,
            chat_id=chat_id,
            thread_id=thread_id,
            user_id=user_id,
            project_slug=slug,
            provider="cursor_cli",
            model=flags.model.model_name,
            agent_id=agent_id,
            role=definition.role,
            workflow=str(definition.workflow or ""),
        )
    else:
        trace.project_slug = slug
        trace.provider = "cursor_cli"
        trace.model = flags.model.model_name
        trace.agent_id = agent_id
        trace.role = definition.role
        trace.workflow = str(definition.workflow or "")
    if parent_id and anchored_text != text:
        obs.emit(trace, "reply.anchor.resolved", parent_id=parent_id)
    elif root_id and anchored_text != text:
        obs.emit(trace, "reply.anchor.resolved", parent_id=root_id)

    if agent_id == "milchick":
        from agents.milchick.jira_shortcut import try_milchick_jira_create

        shortcut_context = trusted_context_from_meta(
            agent_id=agent_id,
            project_slug=slug,
            meta=meta,
            trace_id=trace.trace_id,
            user_text=text,
            access_decision=access,
        )
        shortcut = try_milchick_jira_create(
            user_text=text,
            anchored_text=anchored_text,
            context=shortcut_context,
            workspace=workspace,
        )
        if shortcut:
            obs.emit(trace, "agent.jira.shortcut", status=shortcut.get("status"))
            obs.upsert_trace(trace, state="completed" if shortcut.get("status") == "ok" else "failed", project_slug=slug)
            shortcut["trace_id"] = trace.trace_id
            shortcut["agent_id"] = agent_id
            shortcut["project_slug"] = slug
            shortcut["session_id"] = ""
            return shortcut

    lock = store.lock_for(scope)
    loop_permissions_enabled = False
    attachment_dir: Path | None = None
    cursor_for_cleanup: CursorAgentRuntime | None = None
    original_additional_dirs: list[Path] | None = None
    with lock:
        try:
            obs.emit(trace, "agent.message.received")
            obs.upsert_trace(trace, state="queued", project_slug=slug)
            session = store.get_active(agent_id=agent_id, conversation_scope_id=scope)
            if reset and session:
                store.close_session(session["session_id"])
                session = None
            if session and not session_contract_current(
                session,
                soul_version=definition.soul_version,
                protocol_version=definition.protocol_version,
            ):
                obs.emit(
                    trace,
                    "agent.session.contract_mismatch",
                    soul_version=session.get("soul_version"),
                    protocol_version=session.get("protocol_version"),
                    expected_soul=definition.soul_version,
                    expected_protocol=definition.protocol_version,
                )
                store.close_session(session["session_id"])
                session = None
            checkpoint: dict[str, Any] | None = None
            if session and session.get("checkpoint_json"):
                try:
                    prior = json.loads(session["checkpoint_json"])
                except Exception:
                    prior = None
                if isinstance(prior, dict):
                    checkpoint = prior
                    prior_zone = str(prior.get("trust_zone") or "")
                    prior_exposure = str(prior.get("exposure_mode") or "")
                    if prior_zone and prior_zone != str(access.trust_zone or ""):
                        obs.emit(trace, "agent.session.trust_zone_mismatch", prior=prior_zone, current=access.trust_zone)
                        store.close_session(session["session_id"])
                        session = None
                        checkpoint = None
                    elif prior_exposure and prior_exposure != str(access.exposure_mode or ""):
                        store.close_session(session["session_id"])
                        session = None
                        checkpoint = None

            is_new = session is None
            pending: dict[str, Any] | None = None
            if session is not None and not is_new and str(Path(session["workspace_path"]).resolve()) != str(workspace):
                store.close_session(session["session_id"])
                checkpoint = None
                session = store.create(
                    agent_id=agent_id,
                    chat_id=chat_id,
                    conversation_scope_id=scope,
                    workspace_path=str(workspace),
                    project_slug=slug,
                    user_id=user_id,
                    soul_version=definition.soul_version,
                    protocol_version=definition.protocol_version,
                )
                is_new = True
            if session is not None and not is_new:
                pending = store.get_pending(session)
            elif is_new:
                session = session or store.create(
                    agent_id=agent_id,
                    chat_id=chat_id,
                    conversation_scope_id=scope,
                    workspace_path=str(workspace),
                    project_slug=slug,
                    user_id=user_id,
                    soul_version=definition.soul_version,
                    protocol_version=definition.protocol_version,
                )

            if pending and should_supersede_pending(text, pending):
                previous_action = str(pending.get("action") or "")
                old_session_id = str(session.get("session_id") or "")
                old_provider_session_id = str(session.get("provider_session_id") or "")
                if old_provider_session_id:
                    store.invalidate_provider(old_session_id)
                store.close_session(old_session_id)
                session = store.create(
                    agent_id=agent_id,
                    chat_id=chat_id,
                    conversation_scope_id=scope,
                    workspace_path=str(workspace),
                    project_slug=slug,
                    user_id=user_id,
                    soul_version=definition.soul_version,
                    protocol_version=definition.protocol_version,
                )
                checkpoint = None
                pending = None
                is_new = True
                obs.emit(
                    trace,
                    "clarification.superseded",
                    previous_action=previous_action,
                    previous_session_id=old_session_id,
                )
            active_loop = str((checkpoint or {}).get("active_loop") or "").strip().lower()
            loop_intent = (
                classify_loop_intent(text, active_loop=active_loop, pending=pending)
                if agent_id == "mark"
                else classify_loop_intent("")
            )
            if agent_id == "mark" and loop_intent.decision in {"direct", "continue"}:
                from agents.dylan.permission_policy import write_loop_permission_profile

                loop_permissions_enabled = True
                write_loop_permission_profile(workspace, force=True)

            def _prompt_with_contract(base: str, current_pending: dict[str, Any] | None = None) -> str:
                gateway = loop_gateway_prompt(loop_intent, active_loop=active_loop)
                return "\n\n".join(
                    part
                    for part in (
                        base,
                        security_block,
                        interaction_contract_prompt(agent_id=agent_id, pending=current_pending),
                        gateway,
                    )
                    if part
                )

            image_context, attachment_dir = _prepare_feishu_image_context(meta=meta, messenger=messenger)
            if image_context:
                anchored_text = f"{anchored_text}\n\n{image_context}"

            if loop_intent.decision == "confirm":
                chinese = bool(re.search(r"[\u4e00-\u9fff]", text))
                loop_pending = normalize_clarification(
                    {
                        "action": "loop.start",
                        "mode": "loop_confirmation",
                        "loop": loop_intent.loop,
                        "question": loop_confirmation_text(loop_intent, chinese=chinese),
                        "missing": ["loop"],
                        "choices": [
                            {
                                "value": loop_intent.loop,
                                "label": f"Start {loop_intent.loop.title()} Loop" if not chinese else f"开始 {loop_intent.loop.title()} Loop",
                                "description": "Enter the workflow and keep the conversation in this Feishu thread"
                                if not chinese
                                else "进入对应流程，并继续在当前飞书线程中沟通",
                                "recommended": True,
                            },
                            {
                                "value": "decline",
                                "label": "Keep normal conversation" if not chinese else "先不启动",
                                "description": "Do not create or update Loop artifacts" if not chinese else "不创建或修改 Loop 文档",
                                "recommended": False,
                            },
                        ],
                        "impact": "Starting a Loop creates or updates its planning artifacts; it does not authorize code delivery.",
                        "why": loop_intent.reason,
                        "recommended": f"Start {loop_intent.loop.title()} Loop" if not chinese else f"开始 {loop_intent.loop.title()} Loop",
                        "stop_condition": "Stop asking for entry confirmation after the user chooses an option.",
                    },
                    agent_id=agent_id,
                    source_message_id=message_id,
                )
                if loop_pending is not None:
                    store.save_pending(session["session_id"], loop_pending)
                obs.emit(trace, "loop.gateway.confirmation", loop=loop_intent.loop, confidence=loop_intent.confidence)
                obs.upsert_trace(trace, state="completed", project_slug=slug)
                return _loop_gateway_result(
                    action="autonomous.loop_confirmation",
                    text=loop_confirmation_text(loop_intent, chinese=chinese),
                    pending=loop_pending,
                    trace=trace,
                    session=session,
                    project_slug=slug,
                    workspace=workspace,
                    agent_id=agent_id,
                    bootstrap=is_new,
                )

            if loop_intent.decision == "decline" and pending:
                store.clear_pending(session["session_id"])
                chinese = bool(re.search(r"[\u4e00-\u9fff]", text))
                declined = (
                    "好的，我先不启动这个 Loop，继续按普通对话处理。"
                    if chinese
                    else "Understood. I won't start the Loop; we can keep this as a normal conversation."
                )
                obs.emit(trace, "loop.gateway.declined", loop=pending.get("loop") or "")
                obs.upsert_trace(trace, state="completed", project_slug=slug)
                return _loop_gateway_result(
                    action="autonomous.loop_declined",
                    text=declined,
                    pending=None,
                    trace=trace,
                    session=session,
                    project_slug=slug,
                    workspace=workspace,
                    agent_id=agent_id,
                    bootstrap=is_new,
                )

            if is_new:
                prompt = definition.build_bootstrap_prompt(
                    project_slug=slug,
                    workspace_path=str(workspace),
                    user_message=anchored_text,
                )
                prompt = _prompt_with_contract(prompt)
                provider_session_id = None
            else:
                choice_hint = clarification_choice_hint(text, pending)
                if choice_hint:
                    anchored_text = f"{anchored_text}\n\n{choice_hint}"
                prompt = definition.build_resume_prompt(
                    user_message=anchored_text,
                    project_slug=slug,
                    checkpoint=checkpoint,
                )
                prompt = _prompt_with_contract(prompt, pending)
                provider_session_id = session.get("provider_session_id") or None

            cursor = runtime or CursorAgentRuntime(
                model=flags.model.model_name,
                soft_timeout_seconds=flags.soft_timeout_seconds,
                hard_timeout_seconds=flags.hard_timeout_seconds,
                sandbox="enabled",
                force=False,
                trust=True,
                agent_id=agent_id,
                project=slug,
            )
            cursor_for_cleanup = cursor
            if attachment_dir is not None and isinstance(cursor, CursorAgentRuntime):
                original_additional_dirs = list(cursor.additional_dirs)
                cursor.additional_dirs = [attachment_dir, *original_additional_dirs]
            runner = (
                default_runner(runtime=cursor)
                if workspace_isolation_v2_enabled() and runtime is None
                else cursor
            )
            obs.upsert_trace(trace, state="running", project_slug=slug)
            run_kwargs = {
                "workspace": workspace,
                "prompt": prompt,
                "provider_session_id": provider_session_id,
                "trace": trace,
                "obs": obs,
            }
            if workspace_isolation_v2_enabled() and runtime is None:
                result = runner.run(definition=definition, **run_kwargs)
            else:
                result = runner.run(**run_kwargs)

            if (
                provider_session_id
                and (
                    (
                        result.status == "failed"
                        and any(tok in (result.error or "").lower() for tok in _RESUME_RETRY_TOKENS)
                    )
                    or (result.status == "succeeded" and not str(result.text or "").strip())
                )
            ):
                obs.emit(
                    trace,
                    "agent.session.invalidated",
                    provider_session_id=provider_session_id,
                    reason="resume_retry",
                )
                store.invalidate_provider(session["session_id"])
                store.close_session(session["session_id"])
                session = store.create(
                    agent_id=agent_id,
                    chat_id=chat_id,
                    conversation_scope_id=scope,
                    workspace_path=str(workspace),
                    project_slug=slug,
                    user_id=user_id,
                    soul_version=definition.soul_version,
                    protocol_version=definition.protocol_version,
                )
                prompt = definition.build_bootstrap_prompt(
                    project_slug=slug,
                    workspace_path=str(workspace),
                    user_message=anchored_text,
                )
                prompt = _prompt_with_contract(prompt)
                run_kwargs = {
                    "workspace": workspace,
                    "prompt": prompt,
                    "provider_session_id": None,
                    "trace": trace,
                    "obs": obs,
                }
                if workspace_isolation_v2_enabled() and runtime is None:
                    result = runner.run(definition=definition, **run_kwargs)
                else:
                    result = runner.run(**run_kwargs)
                is_new = True
                provider_session_id = None

            if result.provider_session_id and result.status == "succeeded" and str(result.text or "").strip():
                store.update(
                    session["session_id"],
                    provider_session_id=result.provider_session_id,
                    status="active",
                    last_trace_id=trace.trace_id,
                    last_request_id=result.request_id or None,
                    failure_count=0,
                    checkpoint_json=json.dumps(
                        {
                            "project_slug": slug,
                            "last_user_message_hash": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
                            "last_answer_summary": (result.text or "")[:240],
                            "active_loop": loop_intent.loop if loop_intent.decision in {"direct", "continue"} else active_loop,
                            "trust_zone": access.trust_zone,
                            "exposure_mode": access.exposure_mode,
                            "policy_version": access.policy_version,
                        },
                        ensure_ascii=False,
                    ),
                )
            elif result.status == "succeeded" and not str(result.text or "").strip() and result.provider_session_id:
                store.invalidate_provider(session["session_id"])
                store.update(
                    session["session_id"],
                    status="active",
                    last_trace_id=trace.trace_id,
                    failure_count=int(session.get("failure_count") or 0) + 1,
                )
            elif result.status != "succeeded":
                store.update(
                    session["session_id"],
                    status="active",
                    last_trace_id=trace.trace_id,
                    failure_count=int(session.get("failure_count") or 0) + 1,
                )

            if result.status != "succeeded" or not result.text:
                obs.upsert_trace(trace, state="failed", error_code=result.status or "agent_failed")
                return {
                    "status": "error",
                    "action": "autonomous.failed",
                    "text": _user_facing_agent_error(result.error or result.status, trace.trace_id),
                    "trace_id": trace.trace_id,
                    "session_id": session["session_id"],
                    "provider_session_id": result.provider_session_id,
                    "agent_id": agent_id,
                    "tool_events": [e.__dict__ for e in result.tool_events],
                    "typing": {"enabled": False},
                    "flags": {"conversation_v4": True, "mode": "autonomous_workspace"},
                }

            obs.upsert_trace(trace, state="completed", latency_ms=result.duration_ms, project_slug=slug)
            parsed = extract_final_response(result.text)
            clarification = normalize_clarification(
                parsed.clarification_request or {},
                agent_id=agent_id,
                source_message_id=message_id,
            ) if parsed.clarification_request else None
            if clarification and not clarification.get("authorization_intent"):
                clarification["authorization_intent"] = classify_authorization_intent(text)
            action_requests = list(parsed.action_requests)
            if clarification is None and action_requests:
                for request in action_requests:
                    missing = action_missing_fields(
                        str(request.get("action") or ""),
                        resource=request.get("resource") if isinstance(request.get("resource"), dict) else {},
                        arguments=request.get("arguments") if isinstance(request.get("arguments"), dict) else {},
                    )
                    if missing:
                        clarification = normalize_clarification(
                            {
                                "action": str(request.get("action") or ""),
                                "question": clarification_question(str(request.get("action") or ""), missing),
                                "missing": missing,
                                "resource": request.get("resource") or {},
                                "arguments": request.get("arguments") or {},
                                "authorization_intent": classify_authorization_intent(text),
                            },
                            agent_id=agent_id,
                            source_message_id=message_id,
                        )
                        action_requests = []
                        break
            if clarification:
                clarification = _enrich_clarification(clarification, workspace)
                if loop_intent.loop and loop_intent.decision in {"direct", "continue"}:
                    if str(clarification.get("loop") or "").strip().lower() in {"", "general"}:
                        clarification["loop"] = loop_intent.loop
                store.save_pending(session["session_id"], clarification)
            else:
                store.clear_pending(session["session_id"])
            action_receipts: list[dict[str, Any]] = []
            if action_requests and not clarification:
                pending_action = str(pending.get("action") or "").strip() if pending else ""
                pending_mutation_continuation = bool(
                    pending
                    and pending_action
                    and pending.get("authorization_intent") in {"mutate_explicit", "confirm_previous"}
                    and any(str(item.get("action") or "").strip() == pending_action for item in action_requests)
                )
                context = trusted_context_from_meta(
                    agent_id=agent_id,
                    project_slug=slug,
                    meta=meta,
                    trace_id=trace.trace_id,
                    user_text=text,
                    access_decision=access,
                    authorization_intent=(
                        str(pending.get("authorization_intent") or "").strip()
                        if pending_mutation_continuation
                        else None
                    ),
                    explicit_authorization=True if pending_mutation_continuation else None,
                )
                receipts = execute_trusted_actions(context=context, requests=action_requests)
                action_receipts = [r.to_dict() for r in receipts]
                obs.emit(
                    trace,
                    "security.action_requests.executed",
                    count=len(action_receipts),
                    statuses=[r.get("status") for r in action_receipts],
                )
            reply_text = parsed.text
            if clarification and clarification.get("choices") and "suggested options" not in reply_text.casefold():
                reply_text = format_clarification_reply(
                    reply_text or str(clarification.get("question") or ""),
                    clarification.get("choices"),
                    str(clarification.get("current_version") or ""),
                )
            if access.trust_zone == "SHARED" and any(
                tok in (reply_text or "").lower()
                for tok in ("disk space", "hostname", "/applications", "serial number", "free_gb")
            ):
                reply_text = "Host-level information isn't available in shared conversations."
            if action_receipts:
                for receipt in action_receipts:
                    result_payload = receipt.get("result") if isinstance(receipt.get("result"), dict) else {}
                    if receipt.get("status") == "succeeded" and result_payload.get("summary"):
                        if not parsed.valid:
                            reply_text = str(result_payload["summary"])
                        break
                    if receipt.get("status") == "succeeded" and result_payload.get("handoff_text") and not parsed.valid:
                        reply_text = str(result_payload["handoff_text"])
                        if not result_payload.get("result_delivered"):
                            child = result_payload.get("child") if isinstance(result_payload.get("child"), dict) else {}
                            if child.get("result") and isinstance(child.get("result"), dict):
                                nested = child["result"].get("result") if isinstance(child["result"].get("result"), dict) else {}
                                if nested.get("summary"):
                                    reply_text = f"{result_payload['handoff_text']}\n\n{nested['summary']}"
                        break
                reply_text = prefer_action_summary(reply_text, action_receipts)
            return {
                "status": "ok",
                "action": "autonomous.clarification" if clarification else "autonomous.reply",
                "text": reply_text,
                "final_response_mode": parsed.mode,
                "final_response_valid": parsed.valid,
                "action_receipts": action_receipts,
                "pending_clarification": clarification,
                "trace_id": trace.trace_id,
                "session_id": session["session_id"],
                "provider_session_id": result.provider_session_id,
                "project_slug": slug,
                "workspace": str(workspace),
                "agent_id": agent_id,
                "latency_ms": result.duration_ms,
                "tool_events": [e.__dict__ for e in result.tool_events],
                "bootstrap": is_new,
                "typing": {"enabled": False},
                "flags": {"conversation_v4": True, "mode": "autonomous_workspace"},
            }
        finally:
            if cursor_for_cleanup is not None and original_additional_dirs is not None:
                cursor_for_cleanup.additional_dirs = original_additional_dirs
            if attachment_dir is not None:
                shutil.rmtree(attachment_dir, ignore_errors=True)
            if loop_permissions_enabled:
                try:
                    from agents.dylan.permission_policy import write_permission_profile

                    write_permission_profile(workspace, force=True)
                except Exception as exc:
                    obs.emit(trace, "loop.gateway.permission_restore_failed", error=str(exc)[:300], level="ERROR")
            if owned_obs:
                obs.close()
