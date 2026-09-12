"""SQLite persistence for Mark messages, de-duplication, and runs."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from lumon.agents.mark.codex import sanitize_output
from lumon.agents.mark.model import InboundMessage, MarkRunResult, Message
from lumon.errors import AgentRuntimeError
from lumon.workspace.registry import UserStateLayout


class MarkSessionStore:
    """Expose a small durable interface over a private SQLite database."""

    def __init__(
        self,
        state_root: Path | None = None,
        db_path: Path | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        layout = UserStateLayout.from_root(state_root)
        self.path = (db_path or layout.root / "mark.sqlite3").expanduser().resolve()
        self._now = now or (lambda: datetime.now(UTC))
        self._lock = threading.RLock()
        self._prepare_database()

    def claim_event(self, event_id: str, message: InboundMessage | None = None) -> bool:
        """Atomically claim an event ID, returning ``False`` for duplicates."""

        if not event_id.strip():
            return False
        item = message or _placeholder_message(event_id)
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO events (
                    event_id, message_id, conversation_key, chat_id, chat_type,
                    thread_id, root_id, text, sender_id, sender_type,
                    received_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued')
                """,
                (
                    event_id,
                    item.message_id,
                    item.conversation_key,
                    item.chat_id,
                    item.chat_type,
                    item.thread_id,
                    item.root_id,
                    sanitize_output(item.text),
                    item.sender_id,
                    item.sender_type,
                    _timestamp(self._now()),
                ),
            )
            return cursor.rowcount == 1

    def record_message(self, message: Message) -> None:
        """Persist one transcript message without returning its content to callers."""

        with self._lock, self._connect() as connection:
            if message.message_id is not None:
                existing = connection.execute(
                    """
                    SELECT 1
                    FROM messages
                    WHERE conversation_key = ? AND direction = ? AND message_id = ?
                    LIMIT 1
                    """,
                    (message.conversation_key, message.direction, message.message_id),
                ).fetchone()
                if existing is not None:
                    return
            connection.execute(
                """
                INSERT INTO messages (
                    conversation_key, direction, message_id, workspace_id, text, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    message.conversation_key,
                    message.direction,
                    message.message_id,
                    str(message.workspace_id) if message.workspace_id else None,
                    sanitize_output(message.text),
                    message.created_at,
                ),
            )

    def load_history(self, conversation_key: str, limit: int = 20) -> tuple[Message, ...]:
        """Load the most recent transcript messages in chronological order."""

        if limit < 1:
            return ()
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT conversation_key, direction, message_id, workspace_id, text, created_at
                FROM messages
                WHERE conversation_key = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (conversation_key, limit),
            ).fetchall()
        return tuple(_message_from_row(row) for row in reversed(rows))

    def mark_event_status(self, event_id: str, status: str) -> None:
        """Update an event lifecycle state used by restart recovery."""

        if status not in {"queued", "processing", "succeeded", "failed", "timed_out"}:
            raise AgentRuntimeError(f"Invalid Mark event status: {status}")
        with self._lock, self._connect() as connection:
            connection.execute(
                "UPDATE events SET status = ? WHERE event_id = ?", (status, event_id)
            )

    def attach_workspace(self, event_id: str, workspace_id: UUID) -> None:
        """Associate the resolved Workspace with an accepted event and its message."""

        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT conversation_key, message_id FROM events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
            if row is None:
                return
            connection.execute(
                "UPDATE events SET workspace_id = ? WHERE event_id = ?",
                (str(workspace_id), event_id),
            )
            connection.execute(
                """
                UPDATE messages
                SET workspace_id = ?
                WHERE conversation_key = ? AND message_id = ? AND direction = 'inbound'
                """,
                (str(workspace_id), str(row["conversation_key"]), str(row["message_id"])),
            )

    def record_result(self, result: MarkRunResult) -> None:
        """Persist a run result and close the associated event in one transaction."""

        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO runs (
                    run_id, event_id, conversation_key, workspace_id, status,
                    error_code, started_at, ended_at, final_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.run_id,
                    result.event_id,
                    result.conversation_key,
                    str(result.workspace_id) if result.workspace_id else None,
                    result.status,
                    result.error_code,
                    result.started_at,
                    result.ended_at,
                    sanitize_output(result.final_text) if result.final_text else None,
                ),
            )
            connection.execute(
                "UPDATE events SET status = ? WHERE event_id = ?",
                (result.status, result.event_id),
            )

    def recover_pending(self) -> tuple[InboundMessage, ...]:
        """Return queued or interrupted events, making interrupted work runnable again."""

        with self._lock, self._connect() as connection:
            connection.execute("UPDATE events SET status = 'queued' WHERE status = 'processing'")
            rows = connection.execute(
                """
                SELECT event_id, message_id, chat_id, chat_type, text, sender_id,
                       sender_type, thread_id, root_id
                FROM events
                WHERE status = 'queued'
                ORDER BY received_at ASC
                """
            ).fetchall()
        return tuple(_inbound_from_row(row) for row in rows)

    def event_status(self, event_id: str) -> str | None:
        """Return one event's status for diagnostics and tests."""

        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT status FROM events WHERE event_id = ?", (event_id,)
            ).fetchone()
        return str(row["status"]) if row else None

    def _prepare_database(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.parent.chmod(0o700)
            if self.path.exists():
                self.path.chmod(0o600)
            with self._connect() as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS events (
                        event_id TEXT PRIMARY KEY,
                        message_id TEXT NOT NULL,
                        conversation_key TEXT NOT NULL,
                        chat_id TEXT NOT NULL,
                        chat_type TEXT NOT NULL,
                        thread_id TEXT,
                        root_id TEXT,
                        workspace_id TEXT,
                        text TEXT NOT NULL,
                        sender_id TEXT NOT NULL,
                        sender_type TEXT NOT NULL,
                        received_at TEXT NOT NULL,
                        status TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_key TEXT NOT NULL,
                        direction TEXT NOT NULL,
                        message_id TEXT,
                        workspace_id TEXT,
                        text TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS runs (
                        run_id TEXT PRIMARY KEY,
                        event_id TEXT NOT NULL,
                        conversation_key TEXT NOT NULL,
                        workspace_id TEXT,
                        status TEXT NOT NULL,
                        error_code TEXT,
                        started_at TEXT NOT NULL,
                        ended_at TEXT NOT NULL,
                        final_text TEXT
                    );
                    CREATE INDEX IF NOT EXISTS messages_conversation_idx
                        ON messages (conversation_key, id);
                    CREATE INDEX IF NOT EXISTS events_status_idx
                        ON events (status, received_at);
                    """
                )
                columns = {
                    str(row["name"])
                    for row in connection.execute("PRAGMA table_info(events)").fetchall()
                }
                if "workspace_id" not in columns:
                    connection.execute("ALTER TABLE events ADD COLUMN workspace_id TEXT")
            self.path.chmod(0o600)
        except OSError as exc:
            raise AgentRuntimeError(f"Unable to prepare Mark SQLite database: {self.path}") from exc
        except sqlite3.Error as exc:
            raise AgentRuntimeError(
                f"Unable to initialize Mark SQLite database: {self.path}"
            ) from exc

    def _connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(self.path, timeout=30)
        except sqlite3.Error as exc:
            raise AgentRuntimeError(f"Unable to open Mark SQLite database: {self.path}") from exc
        connection.row_factory = sqlite3.Row
        return connection


def _placeholder_message(event_id: str) -> InboundMessage:
    return InboundMessage(
        event_id=event_id,
        message_id=event_id,
        chat_id="",
        chat_type="p2p",
        text="",
        sender_id="",
        sender_type="user",
    )


def _message_from_row(row: sqlite3.Row) -> Message:
    raw_workspace_id = row["workspace_id"]
    workspace_id = UUID(str(raw_workspace_id)) if raw_workspace_id else None
    direction = str(row["direction"])
    if direction not in {"inbound", "outbound"}:
        raise AgentRuntimeError("Mark SQLite database contains an invalid message direction.")
    return Message(
        conversation_key=str(row["conversation_key"]),
        direction=direction,  # type: ignore[arg-type]
        message_id=str(row["message_id"]) if row["message_id"] else None,
        workspace_id=workspace_id,
        text=str(row["text"]),
        created_at=str(row["created_at"]),
    )


def _inbound_from_row(row: sqlite3.Row) -> InboundMessage:
    return InboundMessage(
        event_id=str(row["event_id"]),
        message_id=str(row["message_id"]),
        chat_id=str(row["chat_id"]),
        chat_type=str(row["chat_type"]),
        text=str(row["text"]),
        sender_id=str(row["sender_id"]),
        sender_type=str(row["sender_type"]),
        thread_id=str(row["thread_id"]) if row["thread_id"] else None,
        root_id=str(row["root_id"]) if row["root_id"] else None,
    )


def _timestamp(now: datetime) -> str:
    return now.astimezone(UTC).isoformat()
