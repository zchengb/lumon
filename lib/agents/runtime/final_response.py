from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


_PLANNING_PREFIX = re.compile(
    r"^(?:I'll |I will |Let me |I'm going to |I am going to |Pulling |Checking |Looking |Atlassian |"
    r"Using |Running |Searching |Reading |Investigating ).{0,240}?\n+",
    re.IGNORECASE | re.MULTILINE,
)

_INTERNAL_PROGRESS_PREFIX = re.compile(
    r"^(?:(?:User\s+(?:approved|confirmed|answered|chose)\b|"
    r"Story\s+(?:marked|updated)\b|Decisions\s+recorded\b|"
    r"Let\s+me\b|Now\s+(?:I'll|I\s+will)\b).*?)"
    r"(?=(?:\*\*|#{1,6}\s|[\u4e00-\u9fff]))",
    re.IGNORECASE | re.DOTALL,
)

_FINAL_ENVELOPE = re.compile(
    r"<FINAL_RESPONSE>\s*(.*?)\s*</FINAL_RESPONSE>",
    re.IGNORECASE | re.DOTALL,
)

_FINAL_OPEN = re.compile(r"<FINAL_RESPONSE>\s*", re.IGNORECASE)

_ACTION_ENVELOPE = re.compile(
    r"<ACTION_REQUEST>\s*(.*?)\s*</ACTION_REQUEST>",
    re.IGNORECASE | re.DOTALL,
)

_NATIVE_TOOL_ENVELOPE = re.compile(
    r"<(?:NATIVE_TOOL_CALL|TOOL_CALL)>\s*(.*?)\s*</(?:NATIVE_TOOL_CALL|TOOL_CALL)>",
    re.IGNORECASE | re.DOTALL,
)

_CLARIFICATION_ENVELOPE = re.compile(
    r"<CLARIFICATION_REQUEST>\s*(.*?)\s*</CLARIFICATION_REQUEST>",
    re.IGNORECASE | re.DOTALL,
)

_CONVERSATION_DECISION_ENVELOPE = re.compile(
    r"<CONVERSATION_DECISION>\s*(.*?)\s*</CONVERSATION_DECISION>",
    re.IGNORECASE | re.DOTALL,
)

# DeepSeek/OpenCode may leave protocol delimiters in the text stream after a
# tool call. They are transport syntax, never user-facing response content.
_DSML_MARKER = re.compile(
    r"</?\s*(?:[|｜]\s*){1,2}DSML(?:\s*[|｜]){1,2}[^>]*>",
    re.IGNORECASE,
)

_FORGED_IDENTITY_KEYS = frozenset(
    {
        "actor_user_id",
        "actor",
        "chat_id",
        "thread_id",
        "source_message_id",
        "trace_id",
        "explicit_authorization",
        "agent_id",
        "project_slug",
        "chat_type",
        "workspace_path",
        "_workspace_path",
    }
)

_ACTION_ALIASES = {
    "job.create": "agent.job.create",
    "create_job": "agent.job.create",
    "job.list": "agent.job.list",
    "job.show": "agent.job.show",
    "job.cancel": "agent.job.cancel",
    "job.retry": "agent.job.retry",
    "jira.testcase.generate": "test_case.generate",
    "testcase.generate": "test_case.generate",
}


@dataclass
class FinalResponseParse:
    text: str
    mode: str
    valid: bool
    fallback_used: bool
    error_code: str = ""
    action_requests: list[dict[str, Any]] = field(default_factory=list)
    clarification_request: dict[str, Any] | None = None
    conversation_decision: dict[str, Any] | None = None


def sanitize_feishu_answer(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return raw
    cleaned = _DSML_MARKER.sub("", raw).strip()
    for _ in range(6):
        nxt = _INTERNAL_PROGRESS_PREFIX.sub("", cleaned, count=1).lstrip()
        if nxt == cleaned:
            nxt = _PLANNING_PREFIX.sub("", cleaned, count=1).lstrip()
        if nxt == cleaned:
            break
        cleaned = nxt
    if "### " in cleaned or "## " in cleaned:
        for marker in ("\n### ", "\n## ", "\n**"):
            idx = cleaned.find(marker)
            if idx > 40:
                head = cleaned[:idx].strip()
                if any(tok in head.lower() for tok in ("i'll ", "pulling ", "checking ", "looking ", "via `", "mcp")):
                    cleaned = cleaned[idx + 1 :].lstrip()
                    break
    cleaned = cleaned.strip()
    if cleaned:
        return cleaned
    return "" if _DSML_MARKER.search(raw) else raw


def _strip_forged_identity(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned = {k: v for k, v in payload.items() if k not in _FORGED_IDENTITY_KEYS}
    resource = cleaned.get("resource")
    if isinstance(resource, dict):
        cleaned["resource"] = {k: v for k, v in resource.items() if k not in _FORGED_IDENTITY_KEYS}
    arguments = cleaned.get("arguments")
    if isinstance(arguments, dict):
        cleaned["arguments"] = {k: v for k, v in arguments.items() if k not in _FORGED_IDENTITY_KEYS}
    return cleaned


def extract_action_requests(raw: str) -> list[dict[str, Any]]:
    text = str(raw or "")
    requests: list[dict[str, Any]] = []
    for match in _ACTION_ENVELOPE.finditer(text):
        body = match.group(1).strip()
        if not body:
            continue
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        action = str(payload.get("action") or "").strip().lower()
        if not action:
            continue
        cleaned = _strip_forged_identity(payload)
        cleaned["action"] = _ACTION_ALIASES.get(action, action)
        if "resource" not in cleaned or not isinstance(cleaned.get("resource"), dict):
            cleaned["resource"] = {}
        if "arguments" not in cleaned or not isinstance(cleaned.get("arguments"), dict):
            cleaned["arguments"] = {}
        requests.append(cleaned)
    # Provider adapters may surface a native tool call as a compact JSON event
    # in a streamed result. Normalize it to the same host request shape while
    # retaining the old envelope parser for older workspaces.
    for match in _NATIVE_TOOL_ENVELOPE.finditer(text):
        try:
            payload = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        cleaned = _strip_forged_identity(payload)
        action = str(cleaned.get("name") or cleaned.get("tool") or cleaned.get("action") or "").strip().lower()
        arguments = cleaned.get("arguments") if isinstance(cleaned.get("arguments"), dict) else {}
        if not action:
            continue
        requests.append(
            {
                "action": _ACTION_ALIASES.get(action, action),
                "arguments": arguments,
                "resource": cleaned.get("resource") if isinstance(cleaned.get("resource"), dict) else {},
            }
        )
    return requests


def extract_clarification_request(raw: str) -> dict[str, Any] | None:
    for match in _CLARIFICATION_ENVELOPE.finditer(str(raw or "")):
        try:
            payload = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return _strip_forged_identity(payload)
    for match in re.finditer(r"<NATIVE_QUESTION>\s*(.*?)\s*</NATIVE_QUESTION>", str(raw or ""), re.IGNORECASE | re.DOTALL):
        try:
            payload = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return _strip_forged_identity(payload)
    return None


def extract_conversation_decision(raw: str) -> dict[str, Any] | None:
    for match in _CONVERSATION_DECISION_ENVELOPE.finditer(str(raw or "")):
        try:
            payload = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return _strip_forged_identity(payload)
    return None


def extract_final_response(raw: str) -> FinalResponseParse:
    text = str(raw or "").strip()
    actions = extract_action_requests(text)
    clarification = extract_clarification_request(text)
    conversation_decision = extract_conversation_decision(text)
    if not text:
        return FinalResponseParse(
            text="",
            mode="empty",
            valid=False,
            fallback_used=True,
            error_code="EMPTY_RESPONSE",
            action_requests=actions,
            clarification_request=clarification,
            conversation_decision=conversation_decision,
        )
    match = _FINAL_ENVELOPE.search(text)
    if match:
        body = sanitize_feishu_answer(_CONVERSATION_DECISION_ENVELOPE.sub("", match.group(1)))
        if body:
            return FinalResponseParse(
                text=body,
                mode="final_response_envelope",
                valid=True,
                fallback_used=False,
                action_requests=actions,
                clarification_request=clarification,
                conversation_decision=conversation_decision,
            )
    opening = _FINAL_OPEN.search(text)
    if opening:
        body = _CONVERSATION_DECISION_ENVELOPE.sub("", text[opening.end() :]).strip()
        body = _CLARIFICATION_ENVELOPE.sub("", _ACTION_ENVELOPE.sub("", body)).strip()
        body = sanitize_feishu_answer(body)
        if body:
            return FinalResponseParse(
                text=body,
                mode="final_response_unclosed",
                valid=False,
                fallback_used=True,
                error_code="UNCLOSED_FINAL_RESPONSE",
                action_requests=actions,
                clarification_request=clarification,
                conversation_decision=conversation_decision,
            )
    without_actions = _CONVERSATION_DECISION_ENVELOPE.sub(
        "", _CLARIFICATION_ENVELOPE.sub("", _ACTION_ENVELOPE.sub("", text))
    ).strip()
    cleaned = sanitize_feishu_answer(without_actions)
    if clarification and not cleaned:
        cleaned = str(clarification.get("question") or "").strip()
    if not cleaned:
        cleaned = sanitize_feishu_answer(text)
    return FinalResponseParse(
        text=cleaned,
        mode="legacy_sanitizer",
        valid=bool(cleaned),
        fallback_used=True,
        error_code="" if cleaned else "SANITIZE_EMPTY",
        action_requests=actions,
        clarification_request=clarification,
        conversation_decision=conversation_decision,
    )


_STATUS_READ_ACTIONS = frozenset(
    {
        "agent.job.list",
        "agent.job.show",
        "agent.job.create",
        "jira.workitem.get",
        "jira.workitem.query",
        "jira.sprint.untested.report",
        "jira.workitem.create",
        "jira.workitem.update",
        "agent.health",
        "agent.list",
        "project.status",
        "workflow.status",
        "schedule.status",
    }
)


def is_planning_reply(text: str) -> bool:
    raw = str(text or "").strip()
    if not raw:
        return True
    lowered = raw.lower()
    starters = (
        "i'll ",
        "i will ",
        "let me ",
        "i'm going to ",
        "i am going to ",
        "checking ",
        "pulling ",
        "looking ",
        "searching ",
        "investigating ",
    )
    if len(raw) > 360:
        return False
    return any(lowered.startswith(s) for s in starters)


_CAPABILITY_PHRASES = {
    "test_case.generate": "test case generation",
    "scan.run": "code scan",
    "agent.job.create": "job create",
    "agent.job.retry": "job retry",
}


def _nested_inner(job: dict[str, Any]) -> dict[str, Any]:
    result = job.get("result") if isinstance(job.get("result"), dict) else {}
    inner = result.get("result") if isinstance(result.get("result"), dict) else result
    return inner if isinstance(inner, dict) else {}


def _nested_outcome(job: dict[str, Any]) -> str:
    result = job.get("result") if isinstance(job.get("result"), dict) else {}
    inner = _nested_inner(job)
    if not inner:
        return ""
    lines: list[str] = []
    if str(inner.get("status") or "").lower() == "failed":
        code = str(inner.get("code") or "").strip()
        message = str(inner.get("message") or "").strip()
        if code and message:
            lines.append(f"{code} — {message}")
        elif code or message:
            lines.append(code or message)
    else:
        message = str(inner.get("message") or inner.get("summary") or "").strip()
        if message:
            lines.append(message)
    sheet_url = str(inner.get("sheet_url") or result.get("sheet_url") or "").strip()
    view_name = str(inner.get("view_name") or result.get("view_name") or "").strip()
    message = "\n".join(lines)
    if sheet_url and sheet_url not in message:
        label = (view_name or "Open Test Cases sheet").replace("'", "").strip() or "Open Test Cases sheet"
        lines.append(f"<link icon='sheet-bitable_outlined' url='{sheet_url}'>{label}</link>")
        lines.append(sheet_url)
    return "\n".join(lines).strip()


def _issue_key(job: dict[str, Any]) -> str:
    for blob in (job.get("input"), job.get("result")):
        if not isinstance(blob, dict):
            continue
        key = str(blob.get("issue_key") or blob.get("story") or "").strip()
        if key:
            return key
        resource = blob.get("resource") if isinstance(blob.get("resource"), dict) else {}
        key = str(resource.get("issue_key") or resource.get("story") or "").strip()
        if key:
            return key
        nested = blob.get("result") if isinstance(blob.get("result"), dict) else {}
        key = str(nested.get("issue_key") or nested.get("story") or "").strip()
        if key:
            return key
    return ""


def _capability_phrase(capability: str) -> str:
    key = str(capability or "").strip()
    if not key:
        return "work"
    return _CAPABILITY_PHRASES.get(key, key.replace(".", " ").replace("_", " "))


def _agent_display(job: dict[str, Any]) -> str:
    owner = str(job.get("target_agent") or job.get("delegated_by") or "").strip()
    return owner[:1].upper() + owner[1:] if owner else ""


def _effective_status(job: dict[str, Any]) -> str:
    status = str(job.get("status") or "unknown").strip().lower() or "unknown"
    inner = _nested_inner(job)
    if str(inner.get("status") or "").lower() == "failed":
        return "failed"
    if str(inner.get("code") or "").startswith("TEST_CASE_"):
        return "failed"
    return status


def _format_one_job(job: dict[str, Any]) -> str:
    capability = str(job.get("capability") or "").strip()
    issue = _issue_key(job)
    outcome = _nested_outcome(job)
    if not capability and not outcome:
        return ""
    status = _effective_status(job)
    phrase = _capability_phrase(capability)
    who = _agent_display(job)
    subject = f"{phrase} for {issue}" if issue else phrase
    if status in {"completed", "succeeded", "success"}:
        head = f"{who} finished {subject}." if who else f"{subject[:1].upper() + subject[1:]} is complete."
    elif status == "failed":
        head = f"{who} failed {subject}." if who else f"{subject[:1].upper() + subject[1:]} failed."
    elif status in {"queued", "pending", "created"}:
        head = f"{subject[:1].upper() + subject[1:]} is queued" + (f" with {who}." if who else ".")
    elif status in {"running", "in_progress"}:
        head = f"{subject[:1].upper() + subject[1:]} is running" + (f" with {who}." if who else ".")
    elif status == "waiting_user":
        head = f"{subject[:1].upper() + subject[1:]} is waiting for your answer" + (f" ({who})." if who else ".")
    else:
        head = f"{subject[:1].upper() + subject[1:]} is {status}" + (f" ({who})." if who else ".")
    if not outcome:
        return head
    if outcome.lower().startswith(head.lower().rstrip(".")):
        return outcome
    return f"{head}\n{outcome}"


def _latest_capability_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for job in jobs:
        if not isinstance(job, dict):
            continue
        capability = str(job.get("capability") or "").strip()
        if not capability:
            continue
        issue = _issue_key(job) or str(job.get("job_id") or "")
        key = (capability, issue.upper())
        if key in seen:
            continue
        seen.add(key)
        latest.append(job)
    return latest


def _format_jira_receipt(action: str, result: dict[str, Any]) -> str:
    if not isinstance(result, dict):
        return ""
    nested_status = str(result.get("status") or "").strip().lower()
    if action == "jira.sprint.untested.report":
        if nested_status == "failed":
            return f"Jira sprint report failed: {str(result.get('message') or result.get('code') or 'failed').strip()}"
        count = result.get("count", 0)
        sprint = str(result.get("sprint_name") or result.get("sprint_id") or "active sprint").strip()
        lines = [f"Active sprint report ({sprint}): {count} matching Jira work item(s)."]
        for item in (result.get("items") if isinstance(result.get("items"), list) else [])[:12]:
            if not isinstance(item, dict):
                continue
            key = str(item.get("issue_key") or "").strip()
            summary = str(item.get("summary") or "").strip()
            status = str(item.get("status") or "").strip()
            subject = " — ".join(part for part in (key, summary) if part)
            lines.append(f"- {subject}" + (f" [{status}]" if status else ""))
        return "\n".join(lines)
    if action == "jira.workitem.get":
        if nested_status == "failed":
            return f"Jira read failed for {str(result.get('issue_key') or '').strip()}: {str(result.get('message') or result.get('code') or 'failed').strip()}"
        key = str(result.get("issue_key") or "").strip()
        summary = str(result.get("summary") or "").strip()
        status = str(result.get("issue_status") or "").strip()
        url = str(result.get("url") or "").strip()
        head = " — ".join(part for part in (key, summary) if part) or "Jira work item read"
        if status:
            head += f" [{status}]"
        return f"{head}\n{url}" if url else head
    if action == "jira.workitem.query":
        if nested_status == "failed":
            return f"Jira query failed: {str(result.get('message') or result.get('code') or 'failed').strip()}"
        lines = [f"Jira query returned {result.get('count', 0)} work item(s)."]
        for item in (result.get("items") if isinstance(result.get("items"), list) else [])[:12]:
            if not isinstance(item, dict):
                continue
            key = str(item.get("issue_key") or "").strip()
            summary = str(item.get("summary") or "").strip()
            status = str(item.get("status") or "").strip()
            subject = " — ".join(part for part in (key, summary) if part)
            lines.append(f"- {subject}" + (f" [{status}]" if status else ""))
        return "\n".join(lines)
    key = str(result.get("issue_key") or "").strip()
    url = str(result.get("url") or "").strip()
    title = str(result.get("summary") or "").strip()
    if nested_status == "failed":
        msg = str(result.get("message") or result.get("code") or "failed").strip()
        head = f"Jira {'create' if 'create' in action else 'update'} failed"
        if key:
            head = f"{head} for {key}"
        return f"{head}: {msg}"
    verb = "Created" if "create" in action else "Updated"
    if key and title and "create" in action:
        head = f"{verb} {key}: {title}"
    elif key:
        head = f"{verb} {key}."
    elif title:
        head = f"{verb}: {title}"
    else:
        head = f"{verb} Jira work item, but no issue key was returned."
    if url and url not in head:
        return f"{head}\n{url}"
    return head


def _format_jobs_payload(result: dict[str, Any]) -> str:
    jobs: list[dict[str, Any]] = []
    if isinstance(result.get("jobs"), list):
        jobs = [j for j in result["jobs"] if isinstance(j, dict)]
    elif isinstance(result.get("job"), dict):
        jobs = [result["job"]]
    elif result.get("job_id"):
        jobs = [result]
    summary = result.get("summary") if isinstance(result.get("summary"), dict) else None
    if summary and isinstance(summary.get("children"), list):
        children = [c for c in summary["children"] if isinstance(c, dict)]
        if children:
            jobs = children
        overall = str(summary.get("overall_state") or "").strip()
        lines = ["**Job status**" + (f": {overall}" if overall else "")]
        for child in _latest_capability_jobs(children or jobs):
            text = _format_one_job(child)
            if text:
                lines.append(text)
        next_dep = str(summary.get("next_dependency") or "").strip()
        if next_dep and not next_dep.startswith("job_"):
            lines.append(f"Next: {next_dep}")
        return "\n\n".join(line for line in lines if line).strip()
    formatted = [text for text in (_format_one_job(job) for job in _latest_capability_jobs(jobs)[:8]) if text]
    if not formatted:
        return ""
    return "**Job status**\n\n" + "\n\n".join(formatted)

def format_action_receipts_summary(receipts: list[dict[str, Any]]) -> str:
    if not receipts:
        return ""
    job_detail = ""
    agent_detail = ""
    note_detail = ""
    test_case_details: list[str] = []
    for receipt in receipts:
        action = str(receipt.get("action") or "").strip()
        if action == "test_case.generate" and receipt.get("status") == "succeeded":
            result = receipt.get("result") if isinstance(receipt.get("result"), dict) else {}
            if str(result.get("status") or "").strip().lower() == "failed":
                code = str(result.get("code") or "").strip()
                message = str(result.get("message") or "").strip()
                detail = " — ".join(item for item in (code, message) if item) or "generation failed"
                language = str(result.get("response_language") or "en").strip()
                if language == "zh-Hans":
                    test_case_details.append(f"测试用例生成失败：{detail}")
                elif language == "zh-Hant":
                    test_case_details.append(f"測試用例生成失敗：{detail}")
                else:
                    test_case_details.append(f"Test-case generation failed: {detail}")
            else:
                detail = str(result.get("summary") or "").strip()
                if detail:
                    test_case_details.append(detail)
            continue
        if action not in _STATUS_READ_ACTIONS:
            continue
        if receipt.get("status") != "succeeded":
            continue
        result = receipt.get("result") if isinstance(receipt.get("result"), dict) else {}
        if action.startswith("jira.") and not job_detail:
            detail = _format_jira_receipt(action, result)
            if detail:
                job_detail = detail
            continue
        if action == "agent.job.create" and not job_detail:
            handoff = str(result.get("handoff_text") or "").strip()
            if handoff:
                job_detail = handoff
                continue
            child = result.get("child") if isinstance(result.get("child"), dict) else {}
            if child:
                detail = _format_one_job(child)
                if detail:
                    job_detail = detail
            continue
        if action in {"agent.job.list", "agent.job.show"} and not job_detail:
            detail = _format_jobs_payload(result)
            if detail:
                job_detail = detail
            continue
        if action in {"agent.health", "agent.list"} and not agent_detail:
            agents = result.get("agents") if isinstance(result.get("agents"), list) else []
            if agents:
                names = [
                    str(a.get("id") or a.get("display_name") or "").strip()
                    for a in agents
                    if isinstance(a, dict)
                ]
                names = [n for n in names if n]
                if names:
                    agent_detail = "**Agents:** " + ", ".join(names[:12])
            continue
        if not note_detail:
            note = str(result.get("note") or result.get("status") or "").strip()
            if note:
                note_detail = f"**{action}:** {note}"
    if job_detail:
        return "\n\n".join([job_detail, *test_case_details]).strip()
    if test_case_details:
        return "\n\n".join(test_case_details)
    if agent_detail:
        return agent_detail
    if note_detail:
        return note_detail
    lines = []
    for receipt in receipts:
        action = receipt.get("action") or "action"
        status = receipt.get("status") or "unknown"
        if status == "succeeded":
            lines.append(f"- {action}: succeeded")
        else:
            err = receipt.get("error") or receipt.get("error_code") or status
            lines.append(f"- {action}: {status} ({err})")
    return "Action results:\n" + "\n".join(lines)


def job_create_succeeded(receipts: list[dict[str, Any]]) -> bool:
    return any(
        str(receipt.get("action") or "").strip() == "agent.job.create"
        and str(receipt.get("status") or "").strip() == "succeeded"
        for receipt in receipts
    )


def has_unbacked_delegation_claim(reply_text: str) -> bool:
    """Detect a declarative claim that another agent is executing work."""
    text = str(reply_text or "").strip()
    if not text or any(marker in text for marker in ("?", "？", "嗎", "吗")):
        return False
    lowered = text.lower()
    if not any(name in lowered for name in ("mark", "irving", "dylan")):
        return False
    verbs = (
        "已派", "已委", "已交給", "已交给", "派給", "派给", "已由", "執行", "执行",
        "進行", "进行", "推進", "推进", "處理", "处理", "接管", "接手", "安排",
        "assigned", "delegated", "handed", "handing", "running", "working", "progress",
    )
    return any(verb in text for verb in verbs)


def _remove_unexecuted_job_claims(reply_text: str, receipts: list[dict[str, Any]]) -> str:
    """Strip claims that work was created/queued/delegated when no job.create succeeded."""
    if job_create_succeeded(receipts):
        return reply_text
    claim_tokens = (
        "已建立", "已创建", "已創建", "建立了", "创建了", "創建了",
        "已排队", "已排隊", "已將", "已将", "已把", "已派", "已交給", "已交给", "已分配",
        "派給", "派给", "created", "queued", "assigned", "delegated", "handed", "handing",
    )
    job_tokens = ("job", "任务", "任務", "工作", "mark", "irving", "dylan", "agent", "delegat", "assign", "hand")
    lines = [
        line
        for line in str(reply_text or "").splitlines()
        if not (
            any(token in line.lower() for token in claim_tokens)
            and any(token in line.lower() for token in job_tokens)
        )
    ]
    return "\n".join(lines).strip()


def prefer_action_summary(
    reply_text: str,
    receipts: list[dict[str, Any]],
    *,
    preserve_substantive: bool = False,
) -> str:
    reply_text = _remove_unexecuted_job_claims(reply_text, receipts)
    summary = format_action_receipts_summary(receipts)
    denials = [r for r in receipts if str(r.get("status") or "") == "denied"]
    denial_lines: list[str] = []
    for receipt in denials:
        action = str(receipt.get("action") or "action").strip()
        err = str(receipt.get("error") or receipt.get("error_code") or "denied").strip()
        denial_lines.append(f"- **{action}** was not executed: {err}")
    denial_text = ""
    if denial_lines:
        denial_text = "**Action blocked**\n" + "\n".join(denial_lines)
    failure_lines: list[str] = []
    for receipt in receipts:
        if str(receipt.get("status") or "") != "failed":
            continue
        action = str(receipt.get("action") or "action").strip()
        result = receipt.get("result") if isinstance(receipt.get("result"), dict) else {}
        detail = (
            _format_jira_receipt(action, result)
            if action.startswith("jira.") and any(result.get(key) for key in ("status", "issue_key", "summary", "count"))
            else ""
        )
        err = detail or str(receipt.get("error") or receipt.get("error_code") or "failed").strip()
        failure_lines.append(f"- **{action}** failed: {err}")
    failure_text = "**Action failed**\n" + "\n".join(failure_lines) if failure_lines else ""
    has_status_read = any(
        str(r.get("action") or "").strip() in _STATUS_READ_ACTIONS and r.get("status") == "succeeded"
        for r in receipts
    )
    has_test_case_failure = any(
        str(r.get("action") or "").strip() == "test_case.generate"
        and r.get("status") == "succeeded"
        and str((r.get("result") or {}).get("status") if isinstance(r.get("result"), dict) else "").strip().lower()
        in {"failed", "error", "denied", "blocked"}
        for r in receipts
    )
    if has_test_case_failure and summary:
        return summary
    if has_status_read and summary and not (preserve_substantive and reply_text and not is_planning_reply(reply_text)):
        notices = "\n\n".join(item for item in (denial_text, failure_text) if item)
        return f"{summary}\n\n{notices}" if notices else summary
    notices = "\n\n".join(item for item in (denial_text, failure_text) if item)
    if notices and (not reply_text or is_planning_reply(reply_text)):
        return notices
    if notices and reply_text and not all(item in reply_text for item in (denial_text, failure_text) if item):
        return f"{reply_text}\n\n{notices}"
    if not reply_text:
        return summary
    return reply_text
