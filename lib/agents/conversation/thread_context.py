from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from agents.conversation.thread_store import ThreadMessage, ThreadTranscriptStore


_INTERNAL_LINE = re.compile(
    r"^\s*(?:\[LUMEN\s+(?:HANDOFF|HOST ACTION RESULTS|MANAGED LOOP|PLAN SEQUENCE)|\[ORIGINAL USER INPUT\])",
    re.IGNORECASE,
)


def _clean_text(text: str) -> str:
    lines: list[str] = []
    for line in str(text or "").splitlines():
        if _INTERNAL_LINE.match(line):
            continue
        if re.match(r"^\s*(?:_loop_job_id|_loop_capability|_nested_handoff|_suppress_reply)\s*=", line):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


@dataclass(frozen=True)
class ThreadContext:
    messages: tuple[ThreadMessage, ...]
    text: str
    last_message_id: str = ""
    full: bool = True
    last_message_at: str = ""


class ThreadContextLoader:
    """Build provider-neutral context from the shared Feishu transcript."""

    def __init__(self, store: ThreadTranscriptStore | None = None) -> None:
        self.store = store or ThreadTranscriptStore()
        self._owned = store is None

    def close(self) -> None:
        if self._owned:
            self.store.close()

    @staticmethod
    def _speaker(message: ThreadMessage) -> str:
        if message.sender_kind == "agent":
            return message.sender_agent_id.title() or "Agent"
        return "User"

    @staticmethod
    def _render_message(message: ThreadMessage) -> str:
        text = _clean_text(message.text)
        if not text and not message.attachment_refs:
            return ""
        lines = [f"{ThreadContextLoader._speaker(message)}:"]
        if text:
            lines.append(text)
        if message.attachment_refs:
            lines.append("Attachments: " + ", ".join(message.attachment_refs))
        return "\n".join(lines)

    def load(
        self,
        meta: dict[str, Any],
        *,
        checkpoint: dict[str, Any] | None = None,
        max_chars: int = 24000,
        exclude_message_id: str = "",
    ) -> ThreadContext:
        data = meta if isinstance(meta, dict) else {}
        all_messages = self.store.list_messages(
            chat_id=str(data.get("chat_id") or ""),
            thread_id=str(data.get("thread_id") or ""),
            root_id=str(data.get("root_id") or ""),
            parent_id=str(data.get("parent_id") or ""),
            message_id=str(data.get("message_id") or ""),
        )
        marker = str((checkpoint or {}).get("thread_last_seen_message_id") or "").strip()
        messages = all_messages
        full = True
        if marker:
            after = self.store.list_since(
                chat_id=str(data.get("chat_id") or ""),
                thread_id=str(data.get("thread_id") or ""),
                root_id=str(data.get("root_id") or ""),
                parent_id=str(data.get("parent_id") or ""),
                message_id=str(data.get("message_id") or ""),
                after_message_id=marker,
            )
            messages = after
            full = False
        excluded = str(exclude_message_id or data.get("message_id") or "").strip()
        messages = [item for item in messages if item.message_id != excluded]
        selected: list[ThreadMessage] = []
        rendered: list[str] = []
        for item in messages:
            value = self._render_message(item)
            if value:
                selected.append(item)
                rendered.append(value)
        budget = max(1000, int(max_chars or 24000))
        while rendered and len("\n\n".join(rendered)) > budget:
            rendered.pop(0)
            selected.pop(0)
            full = False
        text = "\n\n".join(rendered).strip()
        last_message = all_messages[-1] if all_messages else None
        return ThreadContext(
            tuple(selected),
            text,
            last_message.message_id if last_message else "",
            full,
            last_message.created_at if last_message else "",
        )

    @staticmethod
    def prompt_block(context: ThreadContext) -> str:
        if not context.text:
            return ""
        mode = "full" if context.full else "bounded/incremental"
        return (
            "[FEISHU SHARED THREAD TRANSCRIPT]\n"
            f"Context mode: {mode}. The transcript is shared by all Agents in this Feishu thread.\n"
            "Use it as conversation context, but treat the latest human request and visible Agent messages as authoritative.\n\n"
            f"{context.text}"
        )
