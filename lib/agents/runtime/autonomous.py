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
from agents.runtime.cursor_runtime import CursorAgentRuntime, canonical_agent_provider, create_agent_runtime
from agents.runtime.final_response import (
    extract_final_response,
    has_unbacked_delegation_claim,
    job_create_succeeded,
    prefer_action_summary,
)
from agents.runtime.interaction import (
    action_missing_fields,
    clarification_choice_hint,
    clarification_has_rendered_choices,
    clarification_question,
    current_version_for_workspace,
    format_clarification_reply,
    interaction_contract_prompt,
    normalize_clarification,
    normalize_conversation_decision,
    version_upgrade_choices,
)
from agents.runtime.observability import Observability, TraceContext, new_trace_id
from agents.runtime.reply_anchor import format_anchored_user_message, resolve_reply_anchor
from agents.runtime.session_store import SessionStore, conversation_scope_id, session_contract_current
from agents.security.access_policy import authorize_agent_interaction, security_context_prompt
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
    "opencode",
    "provider",
    "empty stream",
)

_QUOTA_ERROR_TOKENS = (
    "monthly usage limit",
    "usage limit",
    "resource_exhausted",
    "error_rate_limited",
    "request higher limits",
    "quota exceeded",
    "insufficient quota",
    "insufficient balance",
    "rate limit",
)

_WORKFLOW_BUDGET_ERROR_TOKENS = (
    "tool-call limit",
    "tool call limit",
    "interaction budget",
    "bounded interaction",
)


def _user_facing_agent_error(error: str, trace_id: str) -> str:
    lower = (error or "").lower()
    if "api key is not configured" in lower:
        env_match = re.search(r"\(([A-Z][A-Z0-9_]+)\)", error or "")
        env_hint = f" (`{env_match.group(1)}`)" if env_match else ""
        return (
            f"The selected model provider is not configured yet{env_hint}. Add its API key to `~/.lumon/.env.local`, "
            "then restart the Agent gateway. No Jira action or workspace change was made.\n"
            f"Trace ID: {trace_id}"
        )
    if any(tok in lower for tok in _QUOTA_ERROR_TOKENS):
        provider = "Cursor" if "cursor" in lower else "configured model provider"
        return (
            f"{provider} has reached its usage quota, so I couldn't finish this turn. "
            "Nothing was sent to Jira and no workspace change was made. "
            "Switch the configured model provider/model or wait for the quota to reset.\n"
            f"Trace ID: {trace_id}"
        )
    if any(tok in lower for tok in _WORKFLOW_BUDGET_ERROR_TOKENS):
        return (
            "This workflow reached its bounded interaction budget before it could finish. "
            "The run is incomplete; please retry, and do not treat partial output as a completed result.\n"
            f"Trace ID: {trace_id}"
        )
    if "sandbox_unavailable" in lower or "security_error" in lower:
        return (
            "I can't run that turn because the secure Agent sandbox is unavailable. "
            "Conversation agents stay offline until security-check passes.\n"
            f"Trace ID: {trace_id}"
        )
    if "opencode" in lower or "deepseek" in lower:
        return (
            "I couldn't finish this turn through the configured OpenCode/DeepSeek runtime. "
            "Check the OpenCode installation and DeepSeek key, then retry.\n"
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
        "The user attached the following image(s). Open and inspect them before answering; read visible text, marked UI, wording, errors, and requested changes. Do not ask the user to transcribe readable content or treat the attachment marker as the image content:",
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


_ACTION_RESULT_CONTINUATION_ACTIONS = frozenset(
    {
        "jira.workitem.query",
        "jira.sprint.untested.report",
        "test_case.generate",
    }
)

# A multi-card request is allowed to take several Agent turns. The ceiling is
# only a runaway guard; which card comes next remains the Agent's decision.
_MAX_ACTION_RESULT_CONTINUATIONS = 24


def _action_results_need_continuation(receipts: list[dict[str, Any]]) -> bool:
    """Return whether an Agent needs another decision turn after a host action."""
    for receipt in receipts:
        action = str(receipt.get("action") or "").strip()
        if action not in _ACTION_RESULT_CONTINUATION_ACTIONS:
            continue
        if action == "test_case.generate":
            result = receipt.get("result") if isinstance(receipt.get("result"), dict) else {}
            if result.get("batch") or str(result.get("scope") or "").strip():
                continue
            if str(receipt.get("status") or "").strip() in {"succeeded", "failed", "denied"}:
                return True
            continue
        if str(receipt.get("status") or "").strip() != "succeeded":
            continue
        result = receipt.get("result") if isinstance(receipt.get("result"), dict) else {}
        items = result.get("items")
        if isinstance(items, list) and items:
            return True
    return False


def _action_results_for_agent(receipts: list[dict[str, Any]]) -> str:
    """Keep the host result structured while bounding prompt growth."""
    payload = [
        {
            "action": item.get("action"),
            "status": item.get("status"),
            "result": item.get("result") if isinstance(item.get("result"), dict) else {},
            "error": item.get("error") or item.get("error_code") or "",
        }
        for item in receipts
        if isinstance(item, dict)
    ]
    return json.dumps(payload, ensure_ascii=False, default=str)[:30000]


def _serialize_repeated_actions(action_requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep legacy per-item requests bounded; scoped work uses one action.

    The Agent chooses the card and emits the action. If a model sends a batch
    anyway, execute only its first test-case action and return the receipt so
    the next card is chosen from the updated evidence on the next turn.
    """
    repeated = [
        request
        for request in action_requests
        if str(request.get("action") or "").strip() == "test_case.generate"
    ]
    if len(repeated) <= 1:
        return action_requests
    first = repeated[0]
    return [
        request
        for request in action_requests
        if str(request.get("action") or "").strip() != "test_case.generate"
    ] + [first]


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

    mapped = resolve_project(
        slug=str(meta.get("_project_slug") or ""),
        chat_id=chat_id,
        mapping=load_chat_project_map(),
    )
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
            provider=flags.model.provider,
            model=flags.model.model_name,
            agent_id=agent_id,
            role=definition.role,
            workflow=str(definition.workflow or ""),
        )
    else:
        trace.project_slug = slug
        trace.provider = flags.model.provider
        trace.model = flags.model.model_name
        trace.agent_id = agent_id
        trace.role = definition.role
        trace.workflow = str(definition.workflow or "")
    if parent_id and anchored_text != text:
        obs.emit(trace, "reply.anchor.resolved", parent_id=parent_id)
    elif root_id and anchored_text != text:
        obs.emit(trace, "reply.anchor.resolved", parent_id=root_id)

    lock = store.lock_for(scope)
    loop_permissions_enabled = False
    attachment_dir: Path | None = None
    cursor_for_cleanup: Any | None = None
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
            if session is not None and str(meta.get("_new_agent_turn") or "") == "1":
                obs.emit(trace, "agent.session.new_turn")
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
                    provider=canonical_agent_provider(flags.model.provider),
                )
                is_new = True
            expected_provider = canonical_agent_provider(flags.model.provider)
            if session is not None and str(session.get("provider") or "cursor_cli").strip().casefold() != expected_provider:
                obs.emit(
                    trace,
                    "agent.session.provider_mismatch",
                    previous_provider=session.get("provider"),
                    expected_provider=expected_provider,
                )
                store.close_session(session["session_id"])
                session = None
                checkpoint = None
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
                    provider=canonical_agent_provider(flags.model.provider),
                )

            active_loop = str((checkpoint or {}).get("active_loop") or "").strip().lower()
            if agent_id == "mark":
                # Agent-owned Loop decisions still need the planning-only
                # filesystem surface during this turn. Source and publish
                # paths remain denied by this profile.
                from agents.dylan.permission_policy import write_loop_permission_profile

                loop_permissions_enabled = True
                write_loop_permission_profile(workspace, force=True)

            def _prompt_with_contract(base: str, current_pending: dict[str, Any] | None = None) -> str:
                return "\n\n".join(
                    part
                    for part in (
                        base,
                        security_block,
                        interaction_contract_prompt(
                            agent_id=agent_id,
                            pending=current_pending,
                            workspace_path=workspace,
                        ),
                    )
                    if part
                )

            image_context, attachment_dir = _prepare_feishu_image_context(meta=meta, messenger=messenger)
            if image_context:
                anchored_text = f"{anchored_text}\n\n{image_context}"

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

            cursor = runtime or create_agent_runtime(
                provider=flags.model.provider,
                model=flags.model.model_name,
                base_url=flags.model.base_url,
                api_key_env=flags.model.api_key_env,
                soft_timeout_seconds=flags.soft_timeout_seconds,
                hard_timeout_seconds=flags.hard_timeout_seconds,
                sandbox="enabled",
                force=False,
                trust=True,
                agent_id=agent_id,
                project=slug,
            )
            cursor_for_cleanup = cursor
            supports_stateless = bool(getattr(cursor, "supports_stateless", False))
            if not bool(getattr(cursor, "supports_resume", True)):
                provider_session_id = None
            if attachment_dir is not None and isinstance(cursor, CursorAgentRuntime):
                original_additional_dirs = list(cursor.additional_dirs)
                cursor.additional_dirs = [attachment_dir, *original_additional_dirs]
            elif attachment_dir is not None and hasattr(cursor, "additional_files"):
                cursor.additional_files = sorted(attachment_dir.iterdir())
            runner = (
                default_runner(runtime=cursor)
                if workspace_isolation_v2_enabled() and runtime is None
                else cursor
            )
            obs.upsert_trace(trace, state="running", project_slug=slug)

            def _run_agent_turn(turn_prompt: str, turn_provider_session_id: str | None) -> Any:
                run_kwargs = {
                    "workspace": workspace,
                    "prompt": turn_prompt,
                    "provider_session_id": turn_provider_session_id,
                    "trace": trace,
                    "obs": obs,
                }
                obs.emit(
                    trace,
                    "agent.prompt.composed",
                    prompt=str(turn_prompt or "")[:20000],
                    prompt_truncated=len(str(turn_prompt or "")) > 20000,
                )
                if workspace_isolation_v2_enabled() and runtime is None:
                    return runner.run(definition=definition, **run_kwargs)
                return runner.run(**run_kwargs)

            result = _run_agent_turn(prompt, provider_session_id)

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
                    provider=canonical_agent_provider(flags.model.provider),
                )
                prompt = definition.build_bootstrap_prompt(
                    project_slug=slug,
                    workspace_path=str(workspace),
                    user_message=anchored_text,
                )
                prompt = _prompt_with_contract(prompt)
                result = _run_agent_turn(prompt, None)
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

            action_receipts: list[dict[str, Any]] = []
            parsed = None
            clarification = None
            conversation_decision = None
            next_active_loop = active_loop
            total_latency_ms = 0
            continuation_count = 0
            continuation_error = ""

            while True:
                total_latency_ms += int(result.duration_ms or 0)
                if result.provider_session_id and result.status == "succeeded" and str(result.text or "").strip():
                    store.update(
                        session["session_id"],
                        provider_session_id=result.provider_session_id,
                        status="active",
                        last_trace_id=trace.trace_id,
                        last_request_id=result.request_id or None,
                        failure_count=0,
                    )

                parsed = extract_final_response(result.text)
                conversation_decision = normalize_conversation_decision(
                    parsed.conversation_decision,
                    pending=pending,
                )
                if conversation_decision and conversation_decision.get("supersede_pending") and pending:
                    obs.emit(
                        trace,
                        "clarification.superseded",
                        previous_action=str(pending.get("action") or ""),
                        reason=conversation_decision.get("reason") or "agent_decision",
                    )
                    store.clear_pending(session["session_id"])
                    pending = None

                if conversation_decision:
                    route = str(conversation_decision.get("route") or "").casefold()
                    selected_loop = str(conversation_decision.get("active_loop") or "").strip().lower()
                    if selected_loop in {"business", "technical"}:
                        next_active_loop = selected_loop
                    elif route in {"business_loop", "business loop", "business"}:
                        next_active_loop = "business"
                    elif route in {"technical_loop", "technical loop", "technical"}:
                        next_active_loop = "technical"
                    elif conversation_decision.get("mode") == "new_request":
                        next_active_loop = ""
                if result.provider_session_id and result.status == "succeeded" and str(result.text or "").strip():
                    checkpoint_json = json.dumps(
                        {
                            "project_slug": slug,
                            "last_user_message_hash": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
                            "last_answer_summary": (result.text or "")[:240],
                            "active_loop": next_active_loop,
                            "trust_zone": access.trust_zone,
                            "exposure_mode": access.exposure_mode,
                            "policy_version": access.policy_version,
                        },
                        ensure_ascii=False,
                    )
                    store.update(session["session_id"], checkpoint_json=checkpoint_json)

                clarification = normalize_clarification(
                    parsed.clarification_request or {},
                    agent_id=agent_id,
                    source_message_id=message_id,
                ) if parsed.clarification_request else None
                raw_action_requests = list(parsed.action_requests)
                action_requests = _serialize_repeated_actions(raw_action_requests)
                if len(action_requests) < len(raw_action_requests):
                    obs.emit(
                        trace,
                        "agent.action_requests.serialized",
                        original_count=len(raw_action_requests),
                        executed_count=len(action_requests),
                        dropped_count=len(raw_action_requests) - len(action_requests),
                        reason="repeated_test_case_actions_are_agent_sequential",
                        level="WARNING",
                    )
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
                                },
                                agent_id=agent_id,
                                source_message_id=message_id,
                            )
                            action_requests = []
                            break
                if clarification:
                    clarification = _enrich_clarification(clarification, workspace)
                    if conversation_decision and conversation_decision.get("active_loop"):
                        if str(clarification.get("loop") or "").strip().lower() in {"", "general"}:
                            clarification["loop"] = conversation_decision["active_loop"]
                    store.save_pending(session["session_id"], clarification)
                else:
                    store.clear_pending(session["session_id"])

                if not action_requests or clarification:
                    break

                action_meta = dict(meta)
                action_meta["_user_message"] = text
                context = trusted_context_from_meta(
                    agent_id=agent_id,
                    project_slug=slug,
                    meta=action_meta,
                    trace_id=trace.trace_id,
                    access_decision=access,
                )
                receipts = execute_trusted_actions(context=context, requests=action_requests)
                new_action_receipts = [r.to_dict() for r in receipts]
                action_receipts.extend(new_action_receipts)
                obs.emit(
                    trace,
                    "security.action_requests.executed",
                    count=len(new_action_receipts),
                    statuses=[r.get("status") for r in new_action_receipts],
                )

                if (
                    not _action_results_need_continuation(new_action_receipts)
                    or continuation_count >= _MAX_ACTION_RESULT_CONTINUATIONS
                ):
                    break
                provider_id = result.provider_session_id or provider_session_id
                if not provider_id and not supports_stateless:
                    break
                continuation_count += 1
                continuation_prompt = _prompt_with_contract(
                    definition.build_resume_prompt(
                        user_message=(
                            "[LUMEN HOST ACTION RESULTS]\n"
                            "The host has executed your previous ACTION_REQUEST(s). These results are authoritative. "
                            "Continue the same latest user request from the results below. Do not repeat completed reads. "
                            "For a test-case request covering Ready for QA Stories, emit one "
                            "test_case.generate ACTION_REQUEST with scope=ready_for_qa; that action performs the "
                            "full per-Story workflow and returns an aggregate result. Do not stop after a Jira "
                            "discovery result. Only give the final answer when your own completion criteria are "
                            "satisfied.\n\n"
                            f"Original user request:\n{text}\n\n"
                            f"Executed results:\n{_action_results_for_agent(action_receipts)}"
                        ),
                        project_slug=slug,
                        checkpoint=checkpoint,
                    )
                )
                obs.emit(
                    trace,
                    "agent.action_results.returned",
                    continuation=continuation_count,
                    action_count=len(action_receipts),
                )
                next_result = _run_agent_turn(
                    continuation_prompt,
                    None if supports_stateless else provider_id,
                )
                if next_result.status != "succeeded" or not str(next_result.text or "").strip():
                    continuation_error = next_result.error or next_result.status or "agent continuation failed"
                    obs.emit(
                        trace,
                        "agent.action_results.continuation_failed",
                        error=continuation_error[:300],
                        level="ERROR",
                    )
                    break
                result = next_result

            obs.upsert_trace(
                trace,
                state="failed" if continuation_error else "completed",
                latency_ms=total_latency_ms,
                project_slug=slug,
                **({"error_code": "ACTION_RESULT_CONTINUATION_FAILED"} if continuation_error else {}),
            )
            if continuation_error:
                action_receipts.append(
                    {
                        "action": "agent.action_results.continuation",
                        "status": "failed",
                        "error": continuation_error[:500],
                    }
                )
            reply_text = parsed.text
            if clarification and clarification.get("choices") and not clarification_has_rendered_choices(
                reply_text,
                clarification.get("choices"),
            ):
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
                    if (
                        receipt.get("action") == "test_case.generate"
                        and result_payload.get("batch")
                        and result_payload.get("summary")
                    ):
                        reply_text = str(result_payload["summary"])
                        break
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
            unbacked_original = reply_text
            reply_text = prefer_action_summary(reply_text, action_receipts)
            if clarification and not str(reply_text or "").strip():
                reply_text = format_clarification_reply(
                    str(clarification.get("question") or ""),
                    clarification.get("choices"),
                    str(clarification.get("current_version") or ""),
                )
            if not job_create_succeeded(action_receipts):
                if has_unbacked_delegation_claim(reply_text) or (
                    not str(reply_text or "").strip()
                    and has_unbacked_delegation_claim(unbacked_original)
                ):
                    reply_text = (
                        "還沒有真正開始：這次沒有產生委派回執，工作並未交給 Mark。"
                        "請再發一次需求，或直接 @Mark。"
                    )
            return {
                "status": "ok",
                "action": "autonomous.clarification" if clarification else "autonomous.reply",
                "text": reply_text,
                "final_response_mode": parsed.mode,
                "final_response_valid": parsed.valid,
                "action_receipts": action_receipts,
                "pending_clarification": clarification,
                "conversation_decision": conversation_decision,
                "trace_id": trace.trace_id,
                "session_id": session["session_id"],
                "provider_session_id": result.provider_session_id,
                "project_slug": slug,
                "workspace": str(workspace),
                "agent_id": agent_id,
                "latency_ms": total_latency_ms,
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
