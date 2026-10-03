"""Read-only, workspace-scoped messages and summaries of Feishu Agent executions."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from lumon.agents.agent.session_store import resolve_database_path
from lumon.errors import AgentRuntimeError
from lumon.tools.safety import sanitize_output

ChatKind = Literal["all", "group", "direct"]


@dataclass(frozen=True, slots=True)
class ChatInteraction:
    run_id: str
    started_at: str
    chat_id: str
    chat_type: str
    sender_id: str
    input_preview: str
    output_preview: str
    status: str
    duration_seconds: int | None
    chat_name: str | None = None
    sender_name: str | None = None


@dataclass(frozen=True, slots=True)
class ChatInteractionPage:
    items: tuple[ChatInteraction, ...]
    total: int


@dataclass(frozen=True, slots=True)
class ChatInteractionDetail:
    run_id: str
    input_text: str
    output_text: str


# Join by event, never by the session's latest Workspace or latest reply: a
# session can move Workspaces and contain multiple users, turns, and retries.
_INTERACTIONS = """
    SELECT r.run_id, r.started_at, r.ended_at, r.status, r.final_text,
           e.chat_id, e.chat_type, e.sender_id, e.text AS input_text
    FROM runs r JOIN events e
      ON e.event_id = r.event_id AND e.conversation_key = r.conversation_key
    WHERE r.workspace_id = :workspace_id AND e.workspace_id = :workspace_id
      AND e.status != 'cancelled'
      AND NOT EXISTS (
          SELECT 1 FROM messages m
          WHERE m.message_id = e.message_id AND m.conversation_key = e.conversation_key
            AND m.workspace_id = :workspace_id AND m.direction = 'inbound' AND m.recalled = 1
      )
      AND (:kind = 'all' OR
           (:kind = 'direct' AND LOWER(e.chat_type) IN ('p2p', 'private', 'dm')) OR
           (:kind = 'group' AND LOWER(e.chat_type) NOT IN ('p2p', 'private', 'dm')))
      AND (:search = '' OR INSTR(LOWER(e.chat_id), :search) > 0 OR
           INSTR(LOWER(COALESCE(e.thread_id, e.root_id, '')), :search) > 0 OR
           INSTR(LOWER(e.sender_id), :search) > 0)
"""


class AgentChatHistory:
    """Read user-facing messages without creating, migrating, or recovering state."""

    def __init__(self, state_root: Path) -> None:
        self._state_root = state_root

    def conversations(
        self,
        workspace_id: UUID,
        *,
        kind: ChatKind = "all",
        search: str = "",
        limit: int = 20,
        offset: int = 0,
    ) -> ChatInteractionPage:
        parameters = {
            "workspace_id": str(workspace_id),
            "kind": kind,
            "search": search.strip().lower(),
            "limit": limit,
            "offset": offset,
        }
        with self._connect() as connection:
            if connection is None:
                return ChatInteractionPage((), 0)
            total = connection.execute(
                f"SELECT COUNT(*) FROM ({_INTERACTIONS})", parameters
            ).fetchone()[0]
            rows = connection.execute(
                _INTERACTIONS
                + " ORDER BY r.started_at DESC, r.run_id DESC LIMIT :limit OFFSET :offset",
                parameters,
            ).fetchall()
        return ChatInteractionPage(tuple(_interaction(row) for row in rows), int(total))

    def interaction(self, workspace_id: UUID, run_id: str) -> ChatInteractionDetail | None:
        """Read only user-facing text; apply the same visibility rules as the list."""

        parameters = {
            "workspace_id": str(workspace_id),
            "kind": "all",
            "search": "",
            "run_id": run_id,
        }
        with self._connect() as connection:
            if connection is None:
                return None
            row = connection.execute(
                _INTERACTIONS + " AND r.run_id = :run_id", parameters
            ).fetchone()
        if row is None:
            return None
        return ChatInteractionDetail(
            run_id=str(row["run_id"]),
            input_text=sanitize_output(row["input_text"] or "").strip(),
            output_text=sanitize_output(row["final_text"] or "").strip(),
        )

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection | None]:
        path = resolve_database_path(self._state_root)
        if not path.is_file():
            yield None
            return
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=5)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only = ON")
            connection.execute("BEGIN")
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
            # Incomplete schemas are upgraded by the Agent, never by this viewer.
            ready = {"runs", "events", "messages"}.issubset({row["name"] for row in tables})
            yield connection if ready else None
        except (sqlite3.Error, OSError) as exc:
            raise AgentRuntimeError("Cannot read local Agent chat history.") from exc
        finally:
            if connection is not None:
                connection.close()


def _interaction(row: sqlite3.Row) -> ChatInteraction:
    return ChatInteraction(
        run_id=str(row["run_id"]),
        started_at=str(row["started_at"]),
        chat_id=str(row["chat_id"]),
        chat_type=str(row["chat_type"]),
        sender_id=str(row["sender_id"]),
        input_preview=_preview(row["input_text"]),
        output_preview=_preview(row["final_text"], preserve_lines=True),
        status=str(row["status"]),
        duration_seconds=_duration(str(row["status"]), row["started_at"], row["ended_at"]),
    )


def _preview(text: str | None, *, preserve_lines: bool = False) -> str:
    redacted = sanitize_output(text or "").strip()
    summary = redacted if preserve_lines else " ".join(redacted.split())
    return summary[:239] + "…" if len(summary) > 240 else summary


def _duration(status: str, started_at: str, ended_at: str) -> int | None:
    if status == "running":
        return None
    try:
        seconds = (
            datetime.fromisoformat(ended_at) - datetime.fromisoformat(started_at)
        ).total_seconds()
    except (ValueError, TypeError):
        return None
    return int(seconds) if seconds >= 0 else None
