"""Provider-neutral conversation events.

Conversation events are the public seam between an Agent Harness and the
conversation transport.  The event payload is deliberately small: useful
work can be shared with the Thread, while private model reasoning, secrets,
and raw tool arguments stay inside the Harness.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from risk.store import utc_now


PUBLIC_EVENT_TYPES = frozenset(
    {
        "agent.started",
        "agent.resumed",
        "agent.message",
        "agent.progress",
        "agent.finding",
        "agent.decision",
        "agent.question",
        "agent.handoff",
        "agent.artifact",
        "agent.blocked",
        "agent.completed",
    }
)

OBSERVABILITY_EVENT_TYPES = frozenset(
    {
        "human.message",
        "tool.started",
        "tool.completed",
        "tool.failed",
        "session.started",
        "session.waiting",
        "session.resumed",
        "session.completed",
        "relay.started",
        "relay.completed",
        "relay.blocked",
    }
)

_TYPE_ALIASES = {
    "assistant_message": "agent.message",
    "message": "agent.message",
    "progress": "agent.progress",
    "finding": "agent.finding",
    "decision": "agent.decision",
    "question": "agent.question",
    "handoff": "agent.handoff",
    "artifact": "agent.artifact",
    "blocked": "agent.blocked",
    "completed": "agent.completed",
    "started": "agent.started",
    "resumed": "agent.resumed",
}


def canonical_event_type(value: str, *, agent: bool = True) -> str:
    """Normalize an adapter event name into the runtime vocabulary."""

    raw = str(value or "").strip().casefold().replace("-", "_")
    if not raw:
        return "agent.message" if agent else ""
    if raw in _TYPE_ALIASES:
        return _TYPE_ALIASES[raw] if agent else raw
    if raw.startswith("agent.") or raw.startswith("tool.") or raw.startswith("session.") or raw.startswith("conversation."):
        return raw
    if raw.startswith("human.") or raw.startswith("relay."):
        return raw
    return f"agent.{raw}" if agent else raw


@dataclass(frozen=True)
class ConversationEvent:
    """A durable event in a shared conversation workstream."""

    event_id: str
    thread_id: str
    agent_id: str
    type: str
    text: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    visibility: str = "public"
    created_at: str = ""
    chat_id: str = ""
    source_message_id: str = ""
    session_id: str = ""
    dedupe_key: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", str(self.event_id or "").strip() or f"event_{uuid.uuid4().hex[:20]}")
        object.__setattr__(self, "thread_id", str(self.thread_id or "").strip())
        object.__setattr__(self, "agent_id", str(self.agent_id or "").strip().lower())
        object.__setattr__(self, "type", canonical_event_type(self.type, agent=self.agent_id != ""))
        object.__setattr__(self, "text", None if self.text is None else str(self.text))
        object.__setattr__(self, "visibility", str(self.visibility or "public").strip().lower() or "public")
        object.__setattr__(self, "created_at", str(self.created_at or utc_now()))
        object.__setattr__(self, "chat_id", str(self.chat_id or "").strip())
        object.__setattr__(self, "source_message_id", str(self.source_message_id or "").strip())
        object.__setattr__(self, "session_id", str(self.session_id or "").strip())
        object.__setattr__(self, "dedupe_key", str(self.dedupe_key or "").strip())
        if not isinstance(self.payload, dict):
            object.__setattr__(self, "payload", {})

    @classmethod
    def create(
        cls,
        *,
        thread_id: str,
        agent_id: str,
        type: str,
        text: str | None = None,
        payload: Mapping[str, Any] | None = None,
        visibility: str = "public",
        chat_id: str = "",
        source_message_id: str = "",
        session_id: str = "",
        dedupe_key: str = "",
    ) -> "ConversationEvent":
        return cls(
            event_id=f"event_{uuid.uuid4().hex[:20]}",
            thread_id=thread_id,
            agent_id=agent_id,
            type=type,
            text=text,
            payload=dict(payload or {}),
            visibility=visibility,
            chat_id=chat_id,
            source_message_id=source_message_id,
            session_id=session_id,
            dedupe_key=dedupe_key,
        )

    @property
    def user_visible(self) -> bool:
        return self.visibility in {"public", "user", "thread"} and self.type in PUBLIC_EVENT_TYPES

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["user_visible"] = self.user_visible
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ConversationEvent":
        data = dict(value)
        data.pop("user_visible", None)
        data["payload"] = dict(data.get("payload") or {}) if isinstance(data.get("payload"), dict) else {}
        return cls(**{key: data.get(key) for key in (
            "event_id", "thread_id", "agent_id", "type", "text", "payload", "visibility",
            "created_at", "chat_id", "source_message_id", "session_id", "dedupe_key",
        )})
