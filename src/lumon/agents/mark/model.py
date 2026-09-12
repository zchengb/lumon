"""Typed values exchanged by the Mark Agent modules."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID

MessageDirection = Literal["inbound", "outbound"]
MarkRunStatus = Literal["succeeded", "failed", "timed_out"]
CodexResultStatus = Literal["succeeded", "failed", "timed_out"]


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
        """Return the stable queue and history key for this chat/thread."""

        thread = self.root_id or self.thread_id
        return f"{self.chat_id}:{thread}" if thread else self.chat_id

    @property
    def admitted(self) -> bool:
        """Return whether the message is eligible for Mark processing."""

        if self.sender_type.casefold() in {"bot", "app", "application"}:
            return False
        return not self.is_group or self.mentioned_mark


@dataclass(frozen=True, slots=True)
class Message:
    """One persisted inbound or outbound transcript message."""

    conversation_key: str
    direction: MessageDirection
    text: str
    created_at: str
    message_id: str | None = None
    workspace_id: UUID | None = None


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


@dataclass(frozen=True, slots=True)
class CodexResult:
    """The safe, provider-independent result returned by the Codex runner."""

    status: CodexResultStatus
    final_text: str | None = None
    progress: tuple[str, ...] = ()
    error_code: str | None = None
    return_code: int | None = None


@dataclass(frozen=True, slots=True)
class WorkspaceContext:
    """Validated Workspace metadata supplied to a Codex execution."""

    workspace_id: UUID
    name: str
    path: Path
    agents_path: Path
    manifest_path: Path
    workspace_config_path: Path
    agents_text: str
    repositories: tuple[str, ...]
