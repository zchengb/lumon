"""SQLite persistence for Mark sessions, messages, de-duplication, and runs."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from lumon.agents.mark.model import (
    InboundMessage,
    MarkRunResult,
    MarkSession,
    Message,
)
from lumon.errors import AgentRuntimeError
from lumon.tools.safety import sanitize_output
from lumon.workspace.registry import UserStateLayout


class MarkSessionStore:
    """Expose a small durable interface over Mark's private SQLite database.

    A session is the durable conversation boundary: one direct chat maps to
    one session, while one group Thread maps to one session. The prompt
    payload sent to an Agent is stored on its run before execution starts.
    The native provider session ID is stored separately so later turns can
    resume the provider conversation without rebuilding its bootstrap context.
    """

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

    def get_or_create_session(self, message: InboundMessage) -> MarkSession:
        """Return the stable Session for a direct chat or group Thread."""

        session_key = message.conversation_key
        timestamp = _timestamp(self._now())
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM sessions WHERE session_key = ?",
                (session_key,),
            ).fetchone()
            if row is None:
                session_id = str(uuid4())
                try:
                    connection.execute(
                        """
                        INSERT INTO sessions (
                            session_id, session_key, chat_id, chat_type,
                            thread_id, root_id, workspace_id, agent_session_id,
                            created_at, last_activity_at, status
                        ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, 'active')
                        """,
                        (
                            session_id,
                            session_key,
                            message.chat_id,
                            message.chat_type,
                            message.thread_id,
                            message.root_id,
                            timestamp,
                            timestamp,
                        ),
                    )
                except sqlite3.IntegrityError:
                    # Another Mark process may have created this key between
                    # the SELECT and INSERT. Reuse that durable identity.
                    row = connection.execute(
                        "SELECT * FROM sessions WHERE session_key = ?",
                        (session_key,),
                    ).fetchone()
                    if row is None:
                        raise AgentRuntimeError(
                            "Unable to create the Mark conversation session."
                        ) from None
                else:
                    row = connection.execute(
                        "SELECT * FROM sessions WHERE session_id = ?",
                        (session_id,),
                    ).fetchone()
            else:
                connection.execute(
                    """
                    UPDATE sessions
                    SET last_activity_at = ?,
                        thread_id = COALESCE(thread_id, ?),
                        root_id = COALESCE(root_id, ?)
                    WHERE session_id = ?
                    """,
                    (timestamp, message.thread_id, message.root_id, row["session_id"]),
                )
                row = connection.execute(
                    "SELECT * FROM sessions WHERE session_id = ?",
                    (row["session_id"],),
                ).fetchone()
            if row is None:
                raise AgentRuntimeError("Mark SQLite session disappeared during creation.")
            return _session_from_row(row)

    def get_session(self, session_id: str) -> MarkSession | None:
        """Return one durable conversation session by its Lumon ID."""

        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        return _session_from_row(row) if row is not None else None

    def bind_agent_session(self, session_id: str, agent_session_id: str) -> None:
        """Persist the provider-native session used by one Lumon Session."""

        normalized = agent_session_id.strip()
        if not normalized:
            return
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE sessions
                SET agent_session_id = ?, last_activity_at = ?
                WHERE session_id = ?
                """,
                (normalized, _timestamp(self._now()), session_id),
            )

    def clear_agent_session(self, session_id: str) -> None:
        """Forget a provider session so the next turn starts a new bootstrap."""

        with self._lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE sessions
                SET agent_session_id = NULL, last_activity_at = ?
                WHERE session_id = ?
                """,
                (_timestamp(self._now()), session_id),
            )

    def claim_event(self, event_id: str, message: InboundMessage | None = None) -> bool:
        """Atomically claim an event ID, returning ``False`` for duplicates."""

        if not event_id.strip():
            return False
        item = message or _placeholder_message(event_id)
        session = self.get_or_create_session(item)
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO events (
                    event_id, message_id, session_id, conversation_key, chat_id,
                    chat_type, thread_id, root_id, text, sender_id, sender_type,
                    received_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued')
                """,
                (
                    event_id,
                    item.message_id,
                    session.session_id,
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
                    conversation_key, session_id, direction, message_id,
                    workspace_id, text, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.conversation_key,
                    message.session_id,
                    message.direction,
                    message.message_id,
                    str(message.workspace_id) if message.workspace_id else None,
                    sanitize_output(message.text),
                    message.created_at,
                ),
            )

    def load_history(
        self,
        session_id: str,
        limit: int = 20,
        *,
        conversation_key: str | None = None,
        legacy_conversation_key: str | None = None,
    ) -> tuple[Message, ...]:
        """Load recent history for a Session, with a legacy-key fallback.

        The fallback keeps transcripts written by older Lumon versions usable
        while all new rows are associated with the explicit Session ID.
        """

        if limit < 1:
            return ()
        history_key = conversation_key or session_id
        conversation_keys = [history_key]
        if legacy_conversation_key and legacy_conversation_key not in conversation_keys:
            conversation_keys.append(legacy_conversation_key)
        placeholders = ", ".join("?" for _ in conversation_keys)
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT conversation_key, session_id, direction, message_id,
                       workspace_id, text, created_at
                FROM messages
                WHERE recalled = 0
                  AND (session_id = ? OR conversation_key IN ({placeholders}))
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, *conversation_keys, limit),
            ).fetchall()
        return tuple(_message_from_row(row) for row in reversed(rows))

    def mark_event_status(self, event_id: str, status: str) -> None:
        """Update an event lifecycle state used by restart recovery."""

        if status not in {
            "queued",
            "processing",
            "cancel_requested",
            "cancelled",
            "succeeded",
            "failed",
            "timed_out",
        }:
            raise AgentRuntimeError(f"Invalid Mark event status: {status}")
        with self._lock, self._connect() as connection:
            connection.execute(
                "UPDATE events SET status = ? WHERE event_id = ?", (status, event_id)
            )

    def bind_event_session(self, event_id: str, session_id: str) -> None:
        """Backfill the Session link for events created by an older schema."""

        with self._lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE events
                SET session_id = COALESCE(session_id, ?)
                WHERE event_id = ?
                """,
                (session_id, event_id),
            )

    def request_message_cancellation(self, message_id: str) -> str | None:
        """Request cancellation for the active event carrying a message ID."""

        if not message_id.strip():
            return None
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT event_id, status
                FROM events
                WHERE message_id = ?
                  AND status IN ('queued', 'processing', 'cancel_requested', 'cancelled')
                ORDER BY received_at DESC
                LIMIT 1
                """,
                (message_id,),
            ).fetchone()
            if row is None:
                return None
            event_id = str(row["event_id"])
            if str(row["status"]) in {"queued", "processing"}:
                connection.execute(
                    "UPDATE events SET status = 'cancel_requested' WHERE event_id = ?",
                    (event_id,),
                )
            return event_id

    def is_cancellation_requested(self, event_id: str) -> bool:
        """Return whether an event is cancelled or awaiting cancellation."""

        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM events
                WHERE event_id = ? AND status IN ('cancel_requested', 'cancelled')
                """,
                (event_id,),
            ).fetchone()
        return row is not None

    def mark_event_cancelled(self, event_id: str) -> None:
        """Finalize user-requested cancellation and exclude its message from history."""

        with self._lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE messages
                SET recalled = 1
                WHERE direction = 'inbound'
                  AND message_id IN (
                      SELECT message_id FROM events WHERE event_id = ?
                  )
                """,
                (event_id,),
            )
            connection.execute(
                """
                UPDATE events
                SET status = 'cancelled'
                WHERE event_id = ?
                  AND status IN ('queued', 'processing', 'cancel_requested')
                """,
                (event_id,),
            )

    def mark_run_cancelled(self, run_id: str, ended_at: str) -> None:
        """Close an in-flight run because its inbound message was recalled."""

        with self._lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE runs
                SET status = 'cancelled', error_code = 'message_recalled', ended_at = ?
                WHERE run_id = ? AND status = 'running'
                """,
                (ended_at, run_id),
            )

    def attach_workspace(self, event_id: str, workspace_id: UUID) -> None:
        """Associate the resolved Workspace with an event, message, and Session."""

        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT conversation_key, message_id, session_id
                FROM events
                WHERE event_id = ?
                """,
                (event_id,),
            ).fetchone()
            if row is None:
                return
            workspace_value = str(workspace_id)
            connection.execute(
                "UPDATE events SET workspace_id = ? WHERE event_id = ?",
                (workspace_value, event_id),
            )
            connection.execute(
                """
                UPDATE messages
                SET workspace_id = ?
                WHERE conversation_key = ? AND message_id = ? AND direction = 'inbound'
                """,
                (workspace_value, str(row["conversation_key"]), str(row["message_id"])),
            )
            if row["session_id"]:
                connection.execute(
                    "UPDATE sessions SET workspace_id = ? WHERE session_id = ?",
                    (workspace_value, str(row["session_id"])),
                )

    def record_run_started(
        self,
        *,
        run_id: str,
        event_id: str,
        session_id: str,
        conversation_key: str,
        workspace_id: UUID,
        agent_provider: str,
        prompt_text: str,
        started_at: str,
    ) -> None:
        """Persist the exact Agent prompt before starting the external process."""

        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO runs (
                    run_id, event_id, session_id, conversation_key, workspace_id,
                    agent_provider, status, error_code, started_at, ended_at,
                    final_text, prompt_text
                ) VALUES (?, ?, ?, ?, ?, ?, 'running', NULL, ?, ?, NULL, ?)
                """,
                (
                    run_id,
                    event_id,
                    session_id,
                    conversation_key,
                    str(workspace_id),
                    agent_provider,
                    started_at,
                    started_at,
                    prompt_text,
                ),
            )

    def record_result(self, result: MarkRunResult) -> None:
        """Persist a terminal run result and close the associated event."""

        final_text = sanitize_output(result.final_text) if result.final_text else None
        with self._lock, self._connect() as connection:
            updated = connection.execute(
                """
                UPDATE runs
                SET event_id = ?,
                    session_id = COALESCE(?, session_id),
                    conversation_key = ?,
                    workspace_id = ?,
                    agent_provider = COALESCE(?, agent_provider),
                    status = ?,
                    error_code = ?,
                    started_at = ?,
                    ended_at = ?,
                    final_text = ?,
                    prompt_text = COALESCE(?, prompt_text)
                WHERE run_id = ?
                """,
                (
                    result.event_id,
                    result.session_id,
                    result.conversation_key,
                    str(result.workspace_id) if result.workspace_id else None,
                    result.agent_provider,
                    result.status,
                    result.error_code,
                    result.started_at,
                    result.ended_at,
                    final_text,
                    result.prompt_text,
                    result.run_id,
                ),
            ).rowcount
            if updated == 0:
                connection.execute(
                    """
                    INSERT INTO runs (
                        run_id, event_id, session_id, conversation_key, workspace_id,
                        agent_provider, status, error_code, started_at, ended_at,
                        final_text, prompt_text
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.run_id,
                        result.event_id,
                        result.session_id,
                        result.conversation_key,
                        str(result.workspace_id) if result.workspace_id else None,
                        result.agent_provider,
                        result.status,
                        result.error_code,
                        result.started_at,
                        result.ended_at,
                        final_text,
                        result.prompt_text,
                    ),
                )
            connection.execute(
                "UPDATE events SET status = ? WHERE event_id = ?",
                (result.status, result.event_id),
            )

    def mark_run_interrupted(self, run_id: str, ended_at: str) -> None:
        """Close an in-flight run after service cancellation without closing its event."""

        with self._lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE runs
                SET status = 'interrupted', error_code = 'interrupted', ended_at = ?
                WHERE run_id = ? AND status = 'running'
                """,
                (ended_at, run_id),
            )

    def recover_pending(self) -> tuple[InboundMessage, ...]:
        """Return queued or interrupted events, making interrupted work runnable again."""

        timestamp = _timestamp(self._now())
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE runs
                SET status = 'interrupted', error_code = 'interrupted', ended_at = ?
                WHERE status = 'running'
                  AND event_id IN (
                      SELECT event_id FROM events WHERE status = 'processing'
                  )
                """,
                (timestamp,),
            )
            connection.execute(
                """
                UPDATE runs
                SET status = 'cancelled', error_code = 'message_recalled', ended_at = ?
                WHERE status = 'running'
                  AND event_id IN (
                      SELECT event_id FROM events WHERE status = 'cancel_requested'
                  )
                """,
                (timestamp,),
            )
            connection.execute(
                """
                UPDATE messages
                SET recalled = 1
                WHERE direction = 'inbound'
                  AND message_id IN (
                      SELECT message_id FROM events WHERE status = 'cancel_requested'
                  )
                """
            )
            connection.execute(
                "UPDATE events SET status = 'cancelled' WHERE status = 'cancel_requested'"
            )
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
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        session_key TEXT NOT NULL UNIQUE,
                        chat_id TEXT NOT NULL,
                        chat_type TEXT NOT NULL,
                        thread_id TEXT,
                        root_id TEXT,
                        workspace_id TEXT,
                        agent_session_id TEXT,
                        created_at TEXT NOT NULL,
                        last_activity_at TEXT NOT NULL,
                        status TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS events (
                        event_id TEXT PRIMARY KEY,
                        message_id TEXT NOT NULL,
                        session_id TEXT,
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
                        session_id TEXT,
                        direction TEXT NOT NULL,
                        message_id TEXT,
                        workspace_id TEXT,
                        text TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        recalled INTEGER NOT NULL DEFAULT 0
                    );
                    CREATE TABLE IF NOT EXISTS runs (
                        run_id TEXT PRIMARY KEY,
                        event_id TEXT NOT NULL,
                        session_id TEXT,
                        conversation_key TEXT NOT NULL,
                        workspace_id TEXT,
                        agent_provider TEXT,
                        status TEXT NOT NULL,
                        error_code TEXT,
                        started_at TEXT NOT NULL,
                        ended_at TEXT NOT NULL,
                        final_text TEXT,
                        prompt_text TEXT
                    );
                    """
                )
                _ensure_column(connection, "events", "workspace_id", "TEXT")
                _ensure_column(connection, "events", "session_id", "TEXT")
                _ensure_column(connection, "sessions", "agent_session_id", "TEXT")
                _ensure_column(connection, "messages", "session_id", "TEXT")
                _ensure_column(
                    connection,
                    "messages",
                    "recalled",
                    "INTEGER NOT NULL DEFAULT 0",
                )
                _ensure_column(connection, "runs", "agent_provider", "TEXT")
                _ensure_column(connection, "runs", "session_id", "TEXT")
                _ensure_column(connection, "runs", "prompt_text", "TEXT")
                connection.executescript(
                    """
                    CREATE INDEX IF NOT EXISTS sessions_activity_idx
                        ON sessions (last_activity_at);
                    CREATE INDEX IF NOT EXISTS events_status_idx
                        ON events (status, received_at);
                    CREATE INDEX IF NOT EXISTS events_session_idx
                        ON events (session_id, received_at);
                    CREATE INDEX IF NOT EXISTS messages_conversation_idx
                        ON messages (conversation_key, id);
                    CREATE INDEX IF NOT EXISTS messages_session_idx
                        ON messages (session_id, id);
                    CREATE INDEX IF NOT EXISTS runs_session_idx
                        ON runs (session_id, started_at);
                    """
                )
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


def _ensure_column(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> None:
    columns = {
        str(row["name"]) for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _placeholder_message(event_id: str) -> InboundMessage:
    return InboundMessage(
        event_id=event_id,
        message_id=event_id,
        chat_id=f"event:{event_id}",
        chat_type="p2p",
        text="",
        sender_id="",
        sender_type="user",
    )


def _session_from_row(row: sqlite3.Row) -> MarkSession:
    raw_workspace_id = row["workspace_id"]
    workspace_id = UUID(str(raw_workspace_id)) if raw_workspace_id else None
    return MarkSession(
        session_id=str(row["session_id"]),
        session_key=str(row["session_key"]),
        chat_id=str(row["chat_id"]),
        chat_type=str(row["chat_type"]),
        thread_id=str(row["thread_id"]) if row["thread_id"] else None,
        root_id=str(row["root_id"]) if row["root_id"] else None,
        workspace_id=workspace_id,
        agent_session_id=(str(row["agent_session_id"]) if row["agent_session_id"] else None),
        created_at=str(row["created_at"]),
        last_activity_at=str(row["last_activity_at"]),
        status=str(row["status"]),
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
        session_id=str(row["session_id"]) if row["session_id"] else None,
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
