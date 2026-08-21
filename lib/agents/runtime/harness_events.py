"""Common event contract for Cursor, OpenCode, Codex, and API adapters."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping


HARNESS_EVENT_TYPES = frozenset(
    {
        "assistant_message",
        "tool_call",
        "tool_result",
        "question",
        "progress",
        "artifact",
        "error",
        "completed",
    }
)


def _safe_summary(value: Any, *, limit: int = 240) -> str:
    """Return a bounded, non-secret summary for observability and routing."""

    if isinstance(value, (dict, list, tuple)):
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except Exception:
            text = str(value)
    else:
        text = str(value or "")
    lowered = text.casefold()
    if any(token in lowered for token in ("api_key", "access_token", "secret", "password", "authorization", "cookie")):
        return "[redacted]"
    return text[:limit]


_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "access_token",
        "authorization",
        "cookie",
        "password",
        "secret",
        "token",
    }
)


def _safe_payload(value: Any, *, key: str = "", depth: int = 0) -> Any:
    """Bound provider metadata before it can enter the shared event stream."""

    if str(key or "").casefold().replace("-", "_") in _SENSITIVE_KEYS:
        return "[redacted]"
    if depth >= 3:
        return _safe_summary(value, limit=160)
    if isinstance(value, Mapping):
        return {
            str(item_key)[:80]: _safe_payload(item_value, key=str(item_key), depth=depth + 1)
            for item_key, item_value in list(value.items())[:32]
        }
    if isinstance(value, (list, tuple)):
        return [_safe_payload(item, depth=depth + 1) for item in list(value)[:32]]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value if not isinstance(value, str) else value[:1000]
    return _safe_summary(value, limit=240)


@dataclass(frozen=True)
class HarnessEvent:
    """Normalized event emitted by a provider adapter."""

    type: str
    text: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    provider: str = ""
    provider_session_id: str = ""
    request_id: str = ""
    sequence: int = 0
    event_id: str = ""

    def __post_init__(self) -> None:
        event_type = str(self.type or "").strip().casefold().replace("-", "_")
        if event_type not in HARNESS_EVENT_TYPES:
            event_type = "assistant_message" if event_type in {"message", "assistant"} else "error"
        object.__setattr__(self, "type", event_type)
        object.__setattr__(self, "text", str(self.text or ""))
        object.__setattr__(self, "provider", str(self.provider or "").strip().casefold())
        object.__setattr__(self, "provider_session_id", str(self.provider_session_id or "").strip())
        object.__setattr__(self, "request_id", str(self.request_id or "").strip())
        object.__setattr__(self, "sequence", max(0, int(self.sequence or 0)))
        object.__setattr__(self, "payload", _safe_payload(self.payload if isinstance(self.payload, dict) else {}))
        if not str(self.event_id or "").strip():
            seed = f"{self.provider}\0{self.provider_session_id}\0{self.request_id}\0{self.sequence}\0{self.type}\0{self.text}"
            object.__setattr__(self, "event_id", f"harness_{hashlib.sha256(seed.encode()).hexdigest()[:20]}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _text_from(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(
            str(item.get("text") or item.get("content") or "")
            for item in value
            if isinstance(item, dict)
        )
    if isinstance(value, dict):
        return str(value.get("text") or value.get("content") or value.get("message") or "")
    return str(value or "")


def _session_id(event: Mapping[str, Any]) -> str:
    return str(
        event.get("session_id")
        or event.get("sessionID")
        or event.get("sessionId")
        or event.get("thread_id")
        or event.get("threadId")
        or ""
    ).strip()


def from_provider_event(
    event: Mapping[str, Any],
    *,
    provider: str,
    sequence: int = 0,
) -> HarnessEvent | None:
    """Translate one known provider event without exposing raw arguments."""

    raw = dict(event)
    event_type = str(raw.get("type") or "").strip().casefold().replace("-", "_")
    item = raw.get("item") if isinstance(raw.get("item"), dict) else {}
    part = raw.get("part") if isinstance(raw.get("part"), dict) else {}
    item_type = str(item.get("type") or part.get("type") or "").strip().casefold()
    session_id = _session_id(raw)
    request_id = str(
        raw.get("request_id")
        or raw.get("requestId")
        or raw.get("requestID")
        or raw.get("turn_id")
        or raw.get("turnId")
        or part.get("messageID")
        or ""
    ).strip()

    if event_type in {"assistant", "message", "text", "assistant_message"} or item_type in {
        "agent_message", "assistant_message", "message"
    } or str(part.get("type") or "").casefold() == "text":
        value = _text_from(item or part or raw.get("message") or raw.get("text") or raw.get("result"))
        if not value.strip():
            return None
        return HarnessEvent(
            type="assistant_message",
            text=value,
            provider=provider,
            provider_session_id=session_id,
            request_id=request_id,
            sequence=sequence,
        )

    if event_type in {"tool_call", "tool_use", "item.tool_call"} or item_type in {
        "command_execution", "file_change", "mcp_tool_call", "web_search", "computer_call", "tool_call"
    } or bool(part.get("tool") or raw.get("tool")):
        status = str(item.get("status") or part.get("status") or raw.get("subtype") or "started").casefold()
        kind = item_type or str(part.get("tool") or raw.get("tool") or event_type)
        event_kind = "tool_result" if status in {"completed", "complete", "success", "succeeded", "failed", "error"} or event_type == "tool_result" else "tool_call"
        return HarnessEvent(
            type=event_kind,
            provider=provider,
            provider_session_id=session_id,
            request_id=request_id,
            sequence=sequence,
            payload={
                "tool": kind[:120],
                "call_id": str(item.get("id") or part.get("callID") or raw.get("call_id") or "")[:120],
                "status": status[:80],
            },
        )

    if event_type in {"question", "native_question", "ask_user", "user_input_required"} or item_type == "question":
        value = _text_from(raw.get("question") or raw.get("message") or item or part)
        raw_choices = raw.get("choices") if isinstance(raw.get("choices"), list) else []
        return HarnessEvent(
            type="question",
            text=value,
            payload={"choices": _safe_payload(raw_choices)},
            provider=provider,
            provider_session_id=session_id,
            request_id=request_id,
            sequence=sequence,
        )

    if event_type in {"progress", "finding", "decision", "handoff", "artifact", "blocked"}:
        value = _text_from(raw.get("message") or raw.get("text") or raw.get("result") or raw.get("content"))
        payload = {
            "kind": event_type,
            **{
                key: _safe_summary(item_value)
                for key, item_value in raw.items()
                if key in {"phase", "path", "caption", "status", "kind"}
            },
        }
        return HarnessEvent(
            type="artifact" if event_type == "artifact" else "progress",
            text=value,
            payload=payload,
            provider=provider,
            provider_session_id=session_id,
            request_id=request_id,
            sequence=sequence,
        )

    if event_type in {"error", "turn.failed", "failed"} or bool(raw.get("is_error")):
        return HarnessEvent(
            type="error",
            text=_safe_summary(raw.get("message") or raw.get("error") or raw.get("result") or "provider error"),
            provider=provider,
            provider_session_id=session_id,
            request_id=request_id,
            sequence=sequence,
        )

    if event_type in {"result", "turn.completed", "completed", "session.completed"}:
        value = _text_from(raw.get("result") or raw.get("message") or raw.get("text"))
        return HarnessEvent(
            type="completed",
            text=value,
            provider=provider,
            provider_session_id=session_id,
            request_id=request_id,
            sequence=sequence,
        )
    return None


def normalize_provider_events(events: Iterable[Mapping[str, Any]], *, provider: str) -> list[HarnessEvent]:
    result: list[HarnessEvent] = []
    for index, event in enumerate(events):
        if not isinstance(event, Mapping):
            continue
        normalized = from_provider_event(event, provider=provider, sequence=index)
        if normalized is not None:
            result.append(normalized)
    return result
