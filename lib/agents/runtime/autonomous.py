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
from agents.runtime.loop_intent import classify_loop_intent, is_combined_plan_request, loop_gateway_prompt
from agents.runtime.harness import infer_task_mode
from agents.runtime.observability import Observability, TraceContext, new_trace_id
from agents.runtime.reply_anchor import format_anchored_user_message, resolve_reply_anchor
from agents.runtime.session_store import SessionStore, conversation_scope_id, session_contract_current
from agents.conversation.config import thread_native_config
from agents.conversation.thread_context import ThreadContextLoader
from feishu.agent_mentions import parse_agent_mentions
from agents.security.access_policy import authorize_agent_interaction, security_context_prompt
from agents.security.actions import FEISHU_ACTIONS
from agents.security.flags import workspace_isolation_v2_enabled
from agents.security.tools import write_host_tool_manifest
from agents.security.trusted import execute_trusted_actions, trusted_context_from_meta
from feishu.messenger import FeishuMessenger, cleanup_generated_plan_pdfs, is_pdf_output_request


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
    "codex",
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
    if "codex_account_mismatch" in lower:
        return (
            "The selected Codex account is not the configured Kuoyio account, so I couldn't run this turn. "
            "Sign in to Codex with the configured account and retry. No Jira action or workspace change was made.\n"
            f"Trace ID: {trace_id}"
        )
    if "codex" in lower:
        return (
            "I couldn't finish this turn through the configured Codex runtime. "
            "Check the Codex CLI login and workspace connection, then retry.\n"
            f"Trace ID: {trace_id}"
        )
    if "opencode" in lower or "deepseek" in lower:
        return (
            "I couldn't finish this turn through the configured OpenCode model runtime. "
            "Check the OpenCode installation and configured model endpoint, then retry.\n"
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
        *FEISHU_ACTIONS,
    }
)

_LOOP_READ_CONTINUATION_ACTIONS = frozenset(
    {
        "jira.workitem.get",
        "story.read",
        "technical_plan.read",
        "delivery.readiness",
        "delivery.status",
        "delivery.result",
    }
)

# A multi-card request is allowed to take several Agent turns. The ceiling is
# only a runaway guard; which card comes next remains the Agent's decision.
_MAX_ACTION_RESULT_CONTINUATIONS = 24

_TEST_CASE_COMMAND_RE = re.compile(
    r"(?:重新|再)?(?:生成|產生|產出|创建|創建|建立|generate|create|regenerate|retry)"
    r".{0,160}?(?:测试用例|測試用例|test[\s_-]*cases?)",
    re.IGNORECASE | re.DOTALL,
)
_JIRA_KEY_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b", re.IGNORECASE)


def _explicit_test_case_action(text: str) -> dict[str, Any] | None:
    """Infer only an unambiguous user-requested test-case action.

    This is a routing guard, not a second action system: execution still goes
    through ``execute_trusted_actions`` and the normal capability policy.
    """
    raw = str(text or "").strip()
    if not _TEST_CASE_COMMAND_RE.search(raw):
        return None
    keys = list(dict.fromkeys(match.upper() for match in _JIRA_KEY_RE.findall(raw)))
    if len(keys) == 1:
        return {"action": "test_case.generate", "arguments": {"issue_key": keys[0]}}
    if not keys and re.search(r"ready\s+for\s+qa|待测|待測|待测试|待測試", raw, re.IGNORECASE):
        return {"action": "test_case.generate", "arguments": {"scope": "ready_for_qa"}}
    return None


def _action_results_need_continuation(
    receipts: list[dict[str, Any]],
    *,
    continue_loop_reads: bool = False,
) -> bool:
    """Return whether an Agent needs another decision turn after a host action."""
    for receipt in receipts:
        action = str(receipt.get("action") or "").strip()
        if action in _LOOP_READ_CONTINUATION_ACTIONS:
            if not continue_loop_reads:
                continue
            if str(receipt.get("status") or "").strip() in {"succeeded", "failed", "denied"}:
                return True
            continue
        if action not in _ACTION_RESULT_CONTINUATION_ACTIONS:
            continue
        if action in FEISHU_ACTIONS:
            # Feishu actions are deliberately conversational: after a visible
            # progress update or file receipt, the same provider session gets
            # another turn to decide whether to continue, ask, or finalize.
            if str(receipt.get("status") or "").strip() in {"succeeded", "failed", "denied"}:
                return True
            continue
        if action == "test_case.generate":
            result = receipt.get("result") if isinstance(receipt.get("result"), dict) else {}
            # The trusted receipt only means the adapter ran. The nested
            # result is the business outcome; failed generation is terminal
            # for this turn and must not be submitted again by continuation.
            if str(result.get("status") or "").strip().casefold() in {"failed", "error", "denied", "blocked"}:
                continue
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


def _session_checkpoint_context(checkpoint: dict[str, Any] | None) -> str:
    """Return a bounded, provider-neutral handoff for stateless/recovered turns."""
    if not isinstance(checkpoint, dict):
        return ""
    summary = str(checkpoint.get("last_answer_summary") or "").strip()
    active_loop = str(checkpoint.get("active_loop") or "").strip()
    project_slug = str(checkpoint.get("project_slug") or "").strip()
    if not summary and not active_loop and not project_slug:
        return ""
    lines = [
        "[LUMON SESSION CHECKPOINT]",
        "This is host-maintained continuity context, not a new user request. Use it only to preserve context and prefer the latest user message if anything conflicts.",
    ]
    if project_slug:
        lines.append(f"- project: {project_slug}")
    if active_loop:
        lines.append(f"- active loop: {active_loop}")
    if summary:
        lines.append(f"- latest answer summary: {summary[:240]}")
    return "\n".join(lines)


def _provider_switch_handoff(
    *,
    previous_provider: str,
    expected_provider: str,
    checkpoint: dict[str, Any] | None,
) -> str:
    """Bridge a logical conversation without ever sharing native provider IDs."""
    lines = [
        "[LUMON PROVIDER SWITCH HANDOFF]",
        "The AI provider changed during this conversation. Continue the same logical request from the latest user message.",
        f"- previous provider: {previous_provider}",
        f"- current provider: {expected_provider}",
        "Native session IDs are provider-scoped: do not try to resume the previous provider's ID here. The host created a fresh native session for the current provider.",
    ]
    checkpoint_context = _session_checkpoint_context(checkpoint)
    if checkpoint_context:
        lines.extend(("", checkpoint_context))
    return "\n".join(lines)


def _append_session_context(prompt: str, checkpoint: dict[str, Any] | None) -> str:
    context = _session_checkpoint_context(checkpoint)
    return f"{prompt}\n\n{context}" if context else prompt


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
    if is_pdf_output_request(text):
        # A PDF requested in the conversation is a transfer artifact.  Remove
        # stale artifacts before the provider sees the workspace so it cannot
        # incorrectly answer that an older PDF is already the current result.
        cleanup_generated_plan_pdfs(workspace)

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
    thread_context_block = ""
    thread_context_last_message_id = ""
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
            provider_switch_handoff = ""
            provider_switch_pending: dict[str, Any] | None = None
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
                previous_provider = canonical_agent_provider(str(session.get("provider") or "cursor_cli"))
                obs.emit(
                    trace,
                    "agent.session.provider_mismatch",
                    previous_provider=previous_provider,
                    expected_provider=expected_provider,
                )
                provider_switch_handoff = _provider_switch_handoff(
                    previous_provider=previous_provider,
                    expected_provider=expected_provider,
                    checkpoint=checkpoint,
                )
                provider_switch_pending = store.get_pending(session)
                store.close_session(session["session_id"])
                session = None
                is_new = True
            inferred_test_case_action = _explicit_test_case_action(text) if agent_id == "milchick" else None
            if inferred_test_case_action and session is not None:
                stale_pending = store.get_pending(session)
                obs.emit(
                    trace,
                    "agent.session.new_request_boundary",
                    reason="explicit_test_case_request",
                    previous_action=str((stale_pending or {}).get("action") or ""),
                )
                store.clear_pending(session["session_id"])
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
                if provider_switch_pending:
                    store.save_pending(session["session_id"], provider_switch_pending)
                    pending = provider_switch_pending
                if checkpoint:
                    # Keep the handoff available if the first turn on the new
                    # provider fails before it can write a fresh checkpoint.
                    store.save_checkpoint(session["session_id"], checkpoint)

            collaboration = thread_native_config(common, meta)
            obs.emit(
                trace,
                "agent.thread.session.created" if is_new else "agent.thread.session.resumed",
                conversation_scope_id=scope,
                provider=canonical_agent_provider(flags.model.provider),
                thread_id=thread_id or root_id,
            )
            if collaboration.enabled:
                context_loader = ThreadContextLoader()
                try:
                    shared_context = context_loader.load(
                        meta,
                        # A new provider session receives the complete shared
                        # transcript.  A resumed provider session only receives
                        # messages after its persisted transcript cursor.
                        checkpoint=None if is_new else checkpoint,
                        max_chars=collaboration.context_max_chars,
                        exclude_message_id=message_id,
                    )
                    thread_context_block = context_loader.prompt_block(shared_context)
                    thread_context_last_message_id = shared_context.last_message_id
                    obs.emit(
                        trace,
                        "thread.context.loaded",
                        message_count=len(shared_context.messages),
                        full=shared_context.full,
                        last_message_id=shared_context.last_message_id,
                        context_chars=len(shared_context.text),
                    )
                finally:
                    context_loader.close()

            active_loop = str((checkpoint or {}).get("active_loop") or "").strip().lower()
            combined_plan_request = agent_id == "mark" and is_combined_plan_request(text)
            plan_sequence = bool(
                agent_id == "mark"
                and (
                    str((checkpoint or {}).get("plan_sequence") or "").strip().lower()
                    == "story_then_technical"
                    or is_combined_plan_request(str((checkpoint or {}).get("last_answer_summary") or ""))
                    or combined_plan_request
                )
            )
            plan_stage = str((checkpoint or {}).get("plan_stage") or "").strip().lower()
            if plan_sequence and plan_stage not in {"story", "business", "technical"}:
                plan_stage = "story"
            if agent_id == "mark":
                # Agent-owned Loop decisions still need the planning-only
                # filesystem surface during this turn. Source and publish
                # paths remain denied by this profile.
                from agents.dylan.permission_policy import write_loop_permission_profile

                loop_permissions_enabled = True
                write_loop_permission_profile(workspace, force=True)

            task_mode = infer_task_mode(text, pending)

            def _prepend_thread_context(prompt: str) -> str:
                if not thread_context_block:
                    return prompt
                return f"{thread_context_block}\n\n{prompt}"

            def _prompt_with_contract(base: str, current_pending: dict[str, Any] | None = None) -> str:
                thread_native_prompt = ""
                if collaboration.enabled:
                    if agent_id == "milchick":
                        thread_native_prompt = (
                            "[LUMON THREAD-NATIVE COLLABORATION]\n"
                            "This workspace uses visible Feishu thread collaboration. For a simple conversational handoff "
                            "to Mark, make the handoff visible with an exact @Mark mention and keep the original request in "
                            "the same message. Do not create a waiting_user Job or claim that a hidden AgentJob is running. "
                            "The Host may translate a legacy delegation request into this visible handoff for compatibility.\n"
                        )
                    elif str(meta.get("_conversation_relay") or "") == "1":
                        thread_native_prompt = (
                            "[LUMON THREAD-NATIVE COLLABORATION]\n"
                            "You were mentioned by a coworker Agent in the same Feishu thread. Treat the visible message and "
                            "the shared transcript as a normal coworker request. Preserve the original human authority; do not "
                            "create another hidden handoff or waiting Job just to continue this conversation.\n"
                        )
                managed_loop = ""
                loop_capability = str(meta.get("_loop_capability") or "").strip().lower()
                if agent_id == "mark" and loop_capability in {"loop.business", "loop.technical"}:
                    loop_name = "Business Loop" if loop_capability == "loop.business" else "Technical Loop"
                    managed_loop = (
                        "[LUMEN MANAGED LOOP]\n"
                        f"You are executing {loop_name} under a host-tracked Loop job.\n"
                        "A read action is intermediate; after the host returns its receipt, continue investigating. "
                        "Never expose internal tool calls, planning notes, or repeated progress updates as the Feishu answer. "
                        "Never finish with only a Jira title/status.\n"
                        "Every turn must report: current stage, evidence completed, blocker or question, and next step.\n"
                        "If a decision or prerequisite is missing, emit CLARIFICATION_REQUEST and ask the user in this Feishu thread; "
                        "if the latest message answered the previous question, continue without asking for a generic 'continue'.\n"
                        "Only finish when the Loop artifact contract is satisfied; the host verifies the artifact before marking the job completed.\n"
                    )
                    if loop_capability == "loop.technical":
                        managed_loop += (
                            "Technical Loop prerequisite is strict: verify that the Story artifact exists and its metadata "
                            "has businessStatus=ready before drafting or presenting technical-plan.md. If it is not ready, "
                            "do not produce a Technical Plan or attachment; explain in ordinary Feishu text that the Story/Business "
                            "Loop must finish first and keep the job waiting for that prerequisite.\n"
                        )
                plan_sequence_prompt = ""
                if plan_sequence:
                    plan_sequence_prompt = (
                        "[LUMEN PLAN SEQUENCE]\n"
                        "This conversation contains a combined Story Plan + Technical Plan request. It is one staged workflow: "
                        "complete the Story/Business Plan first, then continue to the Technical Plan in the same thread/session.\n"
                        "The first response and all intermediate progress or clarification must be ordinary Feishu text. "
                        "Do not auto-generate or attach a PDF, and do not present a Technical Plan as final while the Story is not business-ready.\n"
                        "Only after story.md exists and metadata businessStatus=ready may the Technical Loop begin. "
                        "When the two stages are complete, present the final result as text unless the user explicitly asks for a file.\n"
                        "For an explicit PDF request, always generate the current PDF even if an older output/pdf artifact exists; "
                        "the host removes the transferred PDF afterward.\n"
                    )
                loop_gateway = ""
                if combined_plan_request:
                    loop_gateway = loop_gateway_prompt(
                        classify_loop_intent(text, active_loop=active_loop, pending=current_pending),
                        active_loop=active_loop,
                    )
                return "\n\n".join(
                    part
                    for part in (
                        base,
                        loop_gateway,
                        plan_sequence_prompt,
                        thread_native_prompt,
                        managed_loop,
                        security_block,
                        interaction_contract_prompt(
                            agent_id=agent_id,
                            pending=current_pending,
                            workspace_path=workspace,
                            task_mode=task_mode,
                        ),
                    )
                    if part
                )

            image_context, attachment_dir = _prepare_feishu_image_context(meta=meta, messenger=messenger)
            if image_context:
                anchored_text = f"{anchored_text}\n\n{image_context}"

            write_host_tool_manifest(workspace)
            if is_new:
                prompt = definition.build_bootstrap_prompt(
                    project_slug=slug,
                    workspace_path=str(workspace),
                    user_message=anchored_text,
                )
                if provider_switch_handoff:
                    prompt = f"{provider_switch_handoff}\n\n{prompt}"
                prompt = _prompt_with_contract(prompt, pending)
                prompt = _prepend_thread_context(prompt)
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
                prompt = _append_session_context(prompt, checkpoint)
                prompt = _prompt_with_contract(prompt, pending)
                prompt = _prepend_thread_context(prompt)
                provider_session_id = session.get("provider_session_id") or None

            cursor = runtime or create_agent_runtime(
                provider=flags.model.provider,
                model=flags.model.model_name,
                base_url=flags.model.base_url,
                api_key_env=flags.model.api_key_env,
                reasoning_effort=flags.model.reasoning_effort,
                account_email=flags.model.account_email,
                soft_timeout_seconds=flags.soft_timeout_seconds,
                hard_timeout_seconds=flags.hard_timeout_seconds,
                sandbox="enabled",
                force=False,
                trust=True,
                agent_id=agent_id,
                project=slug,
                harness_mode=flags.harness_mode,
                task_mode=task_mode,
            )
            if hasattr(cursor, "jira_read_actions"):
                cursor.jira_read_actions = frozenset(
                    action
                    for action in ("jira.workitem.get", "jira.workitem.query")
                    if action in access.effective_capabilities
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

            def _run_provider_turn(turn_prompt: str, turn_provider_session_id: str | None) -> Any:
                turn_result = _run_agent_turn(turn_prompt, turn_provider_session_id)
                # Stateless APIs may expose request IDs, but those are not
                # resumable conversation IDs. Never persist or return them as
                # provider session state.
                if not bool(getattr(cursor, "supports_resume", True)):
                    turn_result.provider_session_id = ""
                return turn_result

            result = _run_provider_turn(prompt, provider_session_id)

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
                prompt = _append_session_context(prompt, checkpoint)
                prompt = _prompt_with_contract(prompt, pending)
                prompt = _prepend_thread_context(prompt)
                result = _run_provider_turn(prompt, None)
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
                error_text = _user_facing_agent_error(result.error or result.status, trace.trace_id)
                if agent_id == "mark" and result.status == "timed_out":
                    error_text = (
                        "這一輪 Technical Loop 調查超過時間限制，尚未形成完整計畫；"
                        "我沒有把中間進度當成結論。請在此 thread 回覆「繼續調查」，Mark 會從現有會話續接。\n"
                        f"Trace ID: {trace.trace_id}"
                    )
                return {
                    "status": "error",
                    "action": "autonomous.failed",
                    "text": error_text,
                    "retryable": result.status == "timed_out",
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
                    if plan_sequence and next_active_loop == "business":
                        plan_stage = "business"
                    elif plan_sequence and next_active_loop == "technical" and plan_stage == "business":
                        plan_stage = "technical"
                    if plan_sequence and next_active_loop == "technical" and plan_stage != "technical":
                        # The model may repeat the Technical route from a
                        # prior turn, but the Story stage has not been
                        # selected in this session yet. Keep the same
                        # provider session while correcting the checkpoint;
                        # the plan-sequence prompt tells the model why.
                        next_active_loop = "business"
                        obs.emit(
                            trace,
                            "agent.plan_sequence.story_first_enforced",
                            requested_loop="technical",
                            active_loop="business",
                        )
                if plan_sequence and plan_stage == "story" and next_active_loop not in {"business", "technical"}:
                    # A provider that omits a route must not leave a combined
                    # request without a tracked first stage. The user can
                    # still continue in the same provider session.
                    next_active_loop = "business"
                    obs.emit(
                        trace,
                        "agent.plan_sequence.story_stage_defaulted",
                        active_loop="business",
                    )
                if result.status == "succeeded" and str(result.text or "").strip():
                    checkpoint_json = json.dumps(
                        {
                            "project_slug": slug,
                            "last_user_message_hash": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
                            "last_answer_summary": (result.text or "")[:240],
                            "active_loop": next_active_loop,
                            "plan_sequence": "story_then_technical" if plan_sequence else "",
                            "plan_stage": plan_stage if plan_sequence else "",
                            "trust_zone": access.trust_zone,
                            "exposure_mode": access.exposure_mode,
                            "policy_version": access.policy_version,
                            "thread_last_seen_message_id": message_id or thread_context_last_message_id,
                            "thread_last_seen_at": shared_context.last_message_at if collaboration.enabled else "",
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
                if (
                    inferred_test_case_action
                    and continuation_count == 0
                    and not raw_action_requests
                    and (
                        clarification is None
                        or str(clarification.get("action") or "").strip() == "test_case.generate"
                    )
                ):
                    # A clear, user-authored Jira test-case request must not
                    # disappear just because the model omitted its envelope.
                    clarification = None
                    raw_action_requests = [inferred_test_case_action]
                    obs.emit(
                        trace,
                        "agent.action_request.inferred",
                        action="test_case.generate",
                        reason="explicit_test_case_request_without_model_action",
                    )
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
                action_meta["_workspace_path"] = str(workspace)
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
                    not _action_results_need_continuation(
                        new_action_receipts,
                        continue_loop_reads=agent_id == "mark" and bool(meta.get("_loop_capability")),
                    )
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
                continuation_prompt = _append_session_context(continuation_prompt, checkpoint)
                obs.emit(
                    trace,
                    "agent.action_results.returned",
                    continuation=continuation_count,
                    action_count=len(action_receipts),
                )
                next_result = _run_provider_turn(
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
            if clarification and clarification.get("choices"):
                rendered_question = str(clarification.get("question") or "").strip()
                # Always give the formatter the canonical structured question.
                # The model's final text may only contain a compact answer hint
                # such as "1A, 2A" and is not sufficient to reconstruct the
                # grouped choices on its own.
                if (
                    rendered_question
                    and rendered_question not in str(reply_text or "")
                ) or not clarification_has_rendered_choices(
                    reply_text,
                    clarification.get("choices"),
                ):
                    reply_text = format_clarification_reply(
                        reply_text or rendered_question,
                        clarification.get("choices"),
                        str(clarification.get("current_version") or ""),
                        full_question=rendered_question,
                    )
            if access.trust_zone == "SHARED" and any(
                tok in (reply_text or "").lower()
                for tok in ("disk space", "hostname", "/applications", "serial number", "free_gb")
            ):
                reply_text = "Host-level information isn't available in shared conversations."
            if action_receipts:
                native_handoff = next(
                    (
                        item.get("result")
                        for item in action_receipts
                        if isinstance(item, dict)
                        and item.get("status") == "succeeded"
                        and isinstance(item.get("result"), dict)
                        and item.get("result", {}).get("thread_native")
                    ),
                    None,
                )
                if isinstance(native_handoff, dict) and native_handoff.get("handoff_text"):
                    # The visible handoff is the source Agent's user-facing
                    # answer.  reply_agent_text records it and wakes Mark;
                    # never replace it with an internal Job summary.
                    reply_text = str(native_handoff["handoff_text"])
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
                                if nested.get("summary") and not nested.get("outbound_message_id"):
                                    reply_text = f"{result_payload['handoff_text']}\n\n{nested['summary']}"
                        break
            unbacked_original = reply_text
            reply_text = prefer_action_summary(
                reply_text,
                action_receipts,
                preserve_substantive=bool(meta.get("_loop_capability")) and agent_id == "mark",
            )
            if not str(reply_text or "").strip():
                if any(
                    receipt.get("action") == "feishu.send_file" and receipt.get("status") == "succeeded"
                    for receipt in action_receipts
                ):
                    reply_text = "文件已附在当前 Feishu 消息中。"
                elif any(
                    receipt.get("action") == "feishu.send_progress" and receipt.get("status") == "succeeded"
                    for receipt in action_receipts
                ):
                    reply_text = "阶段进度已发送，我会继续处理当前请求。"
                if continuation_error:
                    reply_text = (
                        f"{reply_text}\n\n本轮后续会话续接失败，以上为已确认的发送结果。"
                        f" Trace ID: {trace.trace_id}"
                    )
            if clarification and not str(reply_text or "").strip():
                reply_text = format_clarification_reply(
                    str(clarification.get("question") or ""),
                    clarification.get("choices"),
                    str(clarification.get("current_version") or ""),
                    full_question=str(clarification.get("question") or ""),
                )
            if (
                not job_create_succeeded(action_receipts)
                and not clarification
                and str(meta.get("_nested_handoff") or "") != "1"
            ):
                if inferred_test_case_action and not action_receipts:
                    reply_text = "這次沒有產生測試用例執行回執，Milchick 尚未開始執行，請稍後重試。"
                elif (
                    not (
                        collaboration.enabled
                        and agent_id == "milchick"
                        and any(item.agent_id == "mark" for item in parse_agent_mentions(reply_text))
                    )
                    and has_unbacked_delegation_claim(reply_text)
                ) or (
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
