"""Legacy envelope boundary for pre-3.0 workspaces.

Native Cursor/OpenCode/Codex sessions do not need these markers.  Keeping the
adapter in a named compatibility package makes the migration boundary
explicit, while the existing parser remains available to older workspaces
and third-party callers until the final retirement milestone.
"""

from __future__ import annotations

import re

from agents.runtime.final_response import (
    FinalResponseParse,
    extract_action_requests,
    extract_clarification_request,
    extract_conversation_decision,
    extract_final_response,
    has_unbacked_delegation_claim,
    job_create_succeeded,
    prefer_action_summary,
    sanitize_feishu_answer,
)


LEGACY_ENVELOPE_TYPES = frozenset(
    {
        "CONVERSATION_DECISION",
        "ACTION_REQUEST",
        "CLARIFICATION_REQUEST",
        "FINAL_RESPONSE",
    }
)

_NATIVE_MARKERS = re.compile(
    r"</?\s*(?:CONVERSATION_DECISION|ACTION_REQUEST|CLARIFICATION_REQUEST|"
    r"FINAL_RESPONSE|NATIVE_TOOL_CALL|TOOL_CALL|NATIVE_QUESTION)\b[^>]*>",
    re.IGNORECASE,
)
_NATIVE_ENVELOPE_BODY = re.compile(
    r"<(?:CONVERSATION_DECISION|ACTION_REQUEST|CLARIFICATION_REQUEST|"
    r"NATIVE_TOOL_CALL|TOOL_CALL|NATIVE_QUESTION)\b[^>]*>.*?</(?:CONVERSATION_DECISION|"
    r"ACTION_REQUEST|CLARIFICATION_REQUEST|NATIVE_TOOL_CALL|TOOL_CALL|NATIVE_QUESTION)\s*>",
    re.IGNORECASE | re.DOTALL,
)


def parse_native_response(raw: str) -> FinalResponseParse:
    """Treat a native assistant message as text, never as an action envelope.

    This is intentionally conservative: if a native provider accidentally
    prints an old envelope, the host removes the protocol markup and does not
    execute the embedded JSON.  Native tool calls must arrive through the
    connected-tool channel and native questions through Harness events.
    """

    text = str(raw or "").strip()
    text = _NATIVE_ENVELOPE_BODY.sub("", text)
    text = _NATIVE_MARKERS.sub("", text)
    text = sanitize_feishu_answer(text)
    return FinalResponseParse(
        text=text,
        mode="native",
        valid=bool(text),
        fallback_used=False,
    )
