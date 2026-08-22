"""Conversation-quality measurements for the native Agent output seam.

The quality model is deliberately observational.  It records how an Agent
communicated, but it never rejects a message or imposes a public-message cap.
"""

from __future__ import annotations

import re
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Mapping

from agents.conversation.config import DEFAULT_REPLY_LANGUAGE, normalize_reply_language


_CJK_RE = re.compile(r"[\u3400-\u9fff]")
_LATIN_RE = re.compile(r"[A-Za-z]")
_AGENT_MENTION_RE = re.compile(r"@(dylan|mark|irving|milchick)\b", re.IGNORECASE)
_TRADITIONAL_MARKERS = set("這為與對嗎發現現場連續實際應該還會請問過於關於層級")
_SIMPLIFIED_MARKERS = set("这为与对吗发现现场连续实际应该还会请问关于层级")
_USEFUL_TYPES = frozenset(
    {
        "agent.message",
        "agent.finding",
        "agent.decision",
        "agent.question",
        "agent.handoff",
        "agent.artifact",
        "agent.blocked",
    }
)


def detect_reply_language(text: str) -> str:
    """Best-effort language classification for telemetry, never routing."""

    value = str(text or "").strip()
    if not value:
        return ""
    cjk = _CJK_RE.findall(value)
    if cjk:
        traditional = sum(char in _TRADITIONAL_MARKERS for char in cjk)
        simplified = sum(char in _SIMPLIFIED_MARKERS for char in cjk)
        if traditional > simplified:
            return "zh-Hant"
        if simplified > traditional:
            return "zh-Hans"
        # Traditional Chinese is Lumon's historical default and is the safer
        # tie-breaker for short mixed-language messages.
        return "zh-Hant"
    if _LATIN_RE.search(value):
        return "en"
    return ""


def _collaboration_kind(payload: Mapping[str, Any], text: str) -> str:
    for key in ("collaboration_kind", "collaboration_mode", "handoff_kind", "mode", "kind"):
        value = str(payload.get(key) or "").strip().casefold()
        if value in {"consult", "transfer"}:
            return value
    lower = str(text or "").casefold()
    if "consult" in lower or "咨询" in lower or "諮詢" in lower:
        return "consult"
    if "transfer" in lower or "转交" in lower or "轉交" in lower or "接管" in lower:
        return "transfer"
    return ""


@dataclass
class ConversationQualityMetrics:
    default_language: str = DEFAULT_REPLY_LANGUAGE
    started_monotonic: float = field(default_factory=time.monotonic)
    public_message_count: int = 0
    progress_message_count: int = 0
    progress_chars: int = 0
    time_to_first_useful_message: float | None = None
    time_to_conclusion: float | None = None
    human_interrupt_count: int = 0
    handoff_count: int = 0
    consult_count: int = 0
    transfer_count: int = 0
    question_after_conclusion: bool = False
    _languages: Counter[str] = field(default_factory=Counter, repr=False)
    _conclusion_seen: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        self.default_language = normalize_reply_language(self.default_language)

    def record_human_interrupt(self, count: int = 1) -> None:
        self.human_interrupt_count += max(0, int(count or 0))

    def record_public(
        self,
        event_type: str,
        text: str,
        payload: Mapping[str, Any] | None = None,
        *,
        now: float | None = None,
    ) -> None:
        event = str(event_type or "").strip().lower()
        current = time.monotonic() if now is None else now
        elapsed = max(0.0, current - self.started_monotonic)
        self.public_message_count += 1
        if event == "agent.progress":
            self.progress_message_count += 1
            self.progress_chars += len(str(text or "").strip())
        elif event in _USEFUL_TYPES and self.time_to_first_useful_message is None:
            self.time_to_first_useful_message = elapsed

        language = detect_reply_language(text)
        if language:
            self._languages[language] += 1
        collaboration_kind = _collaboration_kind(payload or {}, text)
        if event == "agent.handoff" or collaboration_kind or _AGENT_MENTION_RE.search(str(text or "")):
            self.handoff_count += 1
            if collaboration_kind == "consult":
                self.consult_count += 1
            elif collaboration_kind == "transfer":
                self.transfer_count += 1
        if event == "agent.question" and self._conclusion_seen:
            self.question_after_conclusion = True
        if event == "agent.decision":
            self.mark_conclusion(now=current)

    def mark_conclusion(self, *, now: float | None = None) -> None:
        current = time.monotonic() if now is None else now
        self._conclusion_seen = True
        if self.time_to_conclusion is None:
            self.time_to_conclusion = max(0.0, current - self.started_monotonic)

    @property
    def language_used(self) -> str:
        return self._languages.most_common(1)[0][0] if self._languages else ""

    def summary(self) -> dict[str, Any]:
        average = self.progress_chars / self.progress_message_count if self.progress_message_count else 0.0
        return {
            "public_message_count": self.public_message_count,
            "progress_message_count": self.progress_message_count,
            "average_progress_chars": round(average, 2),
            "time_to_first_useful_message": self.time_to_first_useful_message,
            "time_to_conclusion": self.time_to_conclusion,
            "human_interrupt_count": self.human_interrupt_count,
            "handoff_count": self.handoff_count,
            "consult_count": self.consult_count,
            "transfer_count": self.transfer_count,
            "language_used": self.language_used,
            "default_language_used": bool(self.language_used and self.language_used == self.default_language),
            "question_after_conclusion": self.question_after_conclusion,
        }
