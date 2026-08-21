"""Compatibility adapters kept outside the native Conversation Runtime."""

from agents.compat.legacy_envelopes import (
    extract_action_requests,
    extract_clarification_request,
    extract_conversation_decision,
    extract_final_response,
    has_unbacked_delegation_claim,
    job_create_succeeded,
    parse_native_response,
    prefer_action_summary,
)

__all__ = [
    "extract_action_requests",
    "extract_clarification_request",
    "extract_conversation_decision",
    "extract_final_response",
    "has_unbacked_delegation_claim",
    "job_create_succeeded",
    "parse_native_response",
    "prefer_action_summary",
]
