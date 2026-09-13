"""Typed values exchanged by the Mark Agent modules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal
from uuid import UUID

MessageDirection = Literal["inbound", "outbound"]
MarkRunStatus = Literal["succeeded", "failed", "timed_out", "cancelled"]
AgentProvider = Literal["codex"]
AgentResultStatus = Literal["succeeded", "failed", "timed_out"]
RunStatus = Literal[
    "running",
    "succeeded",
    "failed",
    "timed_out",
    "interrupted",
    "cancelled",
]


class AgentErrorCode(StrEnum):
    """Provider-neutral errors returned by a local Agent CLI runner."""

    TIMEOUT = "timeout"
    CLI_NOT_FOUND = "cli_not_found"
    START_FAILED = "start_failed"
    EXECUTION_FAILED = "execution_failed"
    EMPTY_RESULT = "empty_result"
    INTERRUPTED = "interrupted"


class ProgressPhase(StrEnum):
    """User-visible stages that an Agent may report during a long request."""

    UNDERSTANDING = "understanding"
    INSPECTING = "inspecting"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    WAITING = "waiting"


@dataclass(frozen=True, slots=True)
class AgentProgress:
    """A concise, validated candidate status from an Agent runner."""

    phase: ProgressPhase
    message: str
    notify_requested: bool = True


@dataclass(frozen=True, slots=True)
class InboundMessage:
    """A normalized Feishu message that passed through the channel seam."""

    event_id: str
    message_id: str
    chat_id: str
    chat_type: str
    text: str
    sender_id: str
    sender_type: str
    mentioned_mark: bool = False
    thread_id: str | None = None
    root_id: str | None = None

    @property
    def is_group(self) -> bool:
        """Return whether the message came from a group chat."""

        return self.chat_type.casefold() not in {"p2p", "private", "dm"}

    @property
    def conversation_key(self) -> str:
        """Return the stable queue, session, and history key for this chat/thread.

        Feishu direct messages share one session for the whole chat, even when
        the SDK attaches different thread metadata. Group messages are scoped
        to their Thread; a root message ID is the final fallback when Feishu
        does not provide a dedicated thread ID.
        """

        if not self.is_group:
            return self.chat_id
        thread = self.thread_id or self.root_id or self.message_id
        return f"{self.chat_id}:{thread}" if thread else self.chat_id

    @property
    def legacy_conversation_key(self) -> str | None:
        """Return the pre-Session key when an upgraded transcript may need it."""

        legacy_thread = self.root_id or self.thread_id
        legacy_key = f"{self.chat_id}:{legacy_thread}" if legacy_thread else self.chat_id
        return legacy_key if legacy_key != self.conversation_key else None

    @property
    def admitted(self) -> bool:
        """Return whether the message is eligible for Mark processing."""

        if self.sender_type.casefold() in {"bot", "app", "application"}:
            return False
        return not self.is_group or self.mentioned_mark


@dataclass(frozen=True, slots=True)
class RecalledMessage:
    """A normalized Feishu event indicating that an inbound message was recalled."""

    event_id: str
    message_id: str
    chat_id: str | None = None


@dataclass(frozen=True, slots=True)
class Message:
    """One persisted inbound or outbound transcript message."""

    conversation_key: str
    direction: MessageDirection
    text: str
    created_at: str
    message_id: str | None = None
    workspace_id: UUID | None = None
    session_id: str | None = None


@dataclass(frozen=True, slots=True)
class MarkSession:
    """The durable identity of one direct chat or group Thread conversation."""

    session_id: str
    session_key: str
    chat_id: str
    chat_type: str
    thread_id: str | None
    root_id: str | None
    workspace_id: UUID | None
    created_at: str
    last_activity_at: str
    status: str = "active"


@dataclass(frozen=True, slots=True)
class MarkRunResult:
    """The durable outcome of one accepted Mark request."""

    run_id: str
    event_id: str
    conversation_key: str
    status: MarkRunStatus
    started_at: str
    ended_at: str
    workspace_id: UUID | None = None
    final_text: str | None = None
    error_code: str | None = None
    agent_provider: str | None = None
    session_id: str | None = None
    prompt_text: str | None = None


@dataclass(frozen=True, slots=True)
class AgentResult:
    """The safe, provider-independent result returned by an Agent runner."""

    status: AgentResultStatus
    final_text: str | None = None
    progress: tuple[AgentProgress, ...] = ()
    error_code: AgentErrorCode | None = None
    return_code: int | None = None


@dataclass(frozen=True, slots=True)
class WorkspaceContext:
    """Validated Workspace metadata supplied to an Agent execution."""

    workspace_id: UUID
    name: str
    path: Path
    agents_path: Path
    manifest_path: Path
    workspace_config_path: Path
    agents_text: str
    repositories: tuple[str, ...]
