from __future__ import annotations

import json
import os
import sqlite3
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable



def _agents_home() -> Path:
    configured = os.environ.get("LUMEN_AGENTS_HOME", "").strip()
    path = Path(configured).expanduser() if configured else Path.home() / ".lumon" / "agents"
    path.mkdir(parents=True, exist_ok=True)
    return path


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def thread_key(
    *,
    thread_id: str = "",
    root_id: str = "",
    parent_id: str = "",
    message_id: str = "",
) -> str:
    """Return Feishu's stable conversation anchor for a message."""

    return str(thread_id or root_id or parent_id or message_id or "").strip()


def thread_keys(
    *,
    thread_id: str = "",
    root_id: str = "",
    parent_id: str = "",
    message_id: str = "",
) -> tuple[str, ...]:
    """Return all usable Feishu anchors without losing a root fallback."""

    values = (
        str(thread_id or "").strip(),
        str(root_id or "").strip(),
        str(parent_id or "").strip(),
        str(message_id or "").strip(),
    )
    return tuple(dict.fromkeys(value for value in values if value))


def _json_list(value: Any) -> list[str]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            value = [value] if value.strip() else []
    if not isinstance(value, (list, tuple, set)):
        return []
    return list(dict.fromkeys(str(item or "").strip() for item in value if str(item or "").strip()))


@dataclass
class ThreadMessage:
    message_id: str
    chat_id: str
    thread_id: str = ""
    root_id: str = ""
    parent_id: str = ""
    sender_kind: str = "user"
    sender_user_id: str = ""
    sender_agent_id: str = ""
    text: str = ""
    mentions: list[str] = field(default_factory=list)
    attachment_refs: list[str] = field(default_factory=list)
    project_slug: str = ""
    created_at: str = ""

    @property
    def conversation_key(self) -> str:
        return thread_key(
            thread_id=self.thread_id,
            root_id=self.root_id,
            parent_id=self.parent_id,
            message_id=self.message_id,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["mentions"] = list(self.mentions)
        payload["attachment_refs"] = list(self.attachment_refs)
        payload["thread_key"] = self.conversation_key
        return payload

    @classmethod
    def from_row(cls, row: sqlite3.Row | dict[str, Any]) -> "ThreadMessage":
        get = row.get if isinstance(row, dict) else row.__getitem__
        return cls(
            message_id=str(get("message_id") or ""),
            chat_id=str(get("chat_id") or ""),
            thread_id=str(get("thread_id") or ""),
            root_id=str(get("root_id") or ""),
            parent_id=str(get("parent_id") or ""),
            sender_kind=str(get("sender_kind") or "user"),
            sender_user_id=str(get("sender_user_id") or ""),
            sender_agent_id=str(get("sender_agent_id") or ""),
            text=str(get("text") or ""),
            mentions=_json_list(get("mentions_json")),
            attachment_refs=_json_list(get("attachment_refs_json")),
            project_slug=str(get("project_slug") or ""),
            created_at=str(get("created_at") or ""),
        )


class ThreadTranscriptStore:
    """Small durable, idempotent transcript store shared by all Agents."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path).expanduser() if path is not None else _agents_home() / "thread_transcript.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), timeout=30, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._migrate()

    def close(self) -> None:
        self.conn.close()

    def _migrate(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS thread_message (
                message_id TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL,
                thread_id TEXT,
                root_id TEXT,
                parent_id TEXT,
                thread_key TEXT NOT NULL,
                sender_kind TEXT NOT NULL,
                sender_user_id TEXT,
                sender_agent_id TEXT,
                text TEXT,
                mentions_json TEXT NOT NULL DEFAULT '[]',
                attachment_refs_json TEXT NOT NULL DEFAULT '[]',
                project_slug TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_thread_message_context
                ON thread_message(chat_id, thread_key, created_at, message_id);
            CREATE INDEX IF NOT EXISTS idx_thread_message_parent
                ON thread_message(parent_id, sender_kind, sender_agent_id);
            CREATE TABLE IF NOT EXISTS conversation_relay (
                relay_key TEXT PRIMARY KEY,
                relay_id TEXT NOT NULL,
                source_message_id TEXT NOT NULL,
                source_agent_id TEXT NOT NULL,
                target_agent_id TEXT NOT NULL,
                hop INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS conversation_event (
                event_id TEXT PRIMARY KEY,
                chat_id TEXT,
                thread_id TEXT NOT NULL,
                agent_id TEXT,
                event_type TEXT NOT NULL,
                text TEXT,
                payload_json TEXT NOT NULL DEFAULT '{}',
                visibility TEXT NOT NULL DEFAULT 'public',
                source_message_id TEXT,
                session_id TEXT,
                dedupe_key TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_conversation_event_thread
                ON conversation_event(chat_id, thread_id, created_at, event_id);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_conversation_event_dedupe
                ON conversation_event(dedupe_key)
                WHERE dedupe_key IS NOT NULL AND dedupe_key <> '';
            """
        )
        self.conn.commit()

    def record(self, message: ThreadMessage) -> ThreadMessage:
        message.message_id = str(message.message_id or "").strip()
        if not message.message_id:
            raise ValueError("thread message_id is required")
        message.chat_id = str(message.chat_id or "").strip()
        message.sender_kind = str(message.sender_kind or "user").strip().lower()
        if message.sender_kind not in {"user", "agent"}:
            raise ValueError("sender_kind must be user or agent")
        message.mentions = _json_list(message.mentions)
        message.attachment_refs = _json_list(message.attachment_refs)
        message.created_at = str(message.created_at or utc_now())
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO thread_message(
                    message_id, chat_id, thread_id, root_id, parent_id, thread_key,
                    sender_kind, sender_user_id, sender_agent_id, text, mentions_json,
                    attachment_refs_json, project_slug, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(message_id) DO UPDATE SET
                    chat_id=excluded.chat_id,
                    thread_id=COALESCE(NULLIF(excluded.thread_id, ''), thread_message.thread_id),
                    root_id=COALESCE(NULLIF(excluded.root_id, ''), thread_message.root_id),
                    parent_id=COALESCE(NULLIF(excluded.parent_id, ''), thread_message.parent_id),
                    thread_key=CASE
                        WHEN NULLIF(thread_message.thread_key, '') IS NULL THEN excluded.thread_key
                        ELSE thread_message.thread_key
                    END,
                    sender_kind=excluded.sender_kind,
                    sender_user_id=COALESCE(NULLIF(excluded.sender_user_id, ''), thread_message.sender_user_id),
                    sender_agent_id=COALESCE(NULLIF(excluded.sender_agent_id, ''), thread_message.sender_agent_id),
                    text=excluded.text,
                    mentions_json=excluded.mentions_json,
                    attachment_refs_json=excluded.attachment_refs_json,
                    project_slug=COALESCE(NULLIF(excluded.project_slug, ''), thread_message.project_slug),
                    created_at=COALESCE(NULLIF(thread_message.created_at, ''), excluded.created_at)
                """,
                (
                    message.message_id,
                    message.chat_id,
                    message.thread_id,
                    message.root_id,
                    message.parent_id,
                    message.conversation_key,
                    message.sender_kind,
                    message.sender_user_id,
                    message.sender_agent_id,
                    message.text,
                    json.dumps(message.mentions, ensure_ascii=False),
                    json.dumps(message.attachment_refs, ensure_ascii=False),
                    message.project_slug,
                    message.created_at,
                ),
            )
            self.conn.commit()
        return message

    def get(self, message_id: str) -> ThreadMessage | None:
        with self._lock:
            row = self.conn.execute(
                "SELECT * FROM thread_message WHERE message_id = ?", (str(message_id or "").strip(),)
            ).fetchone()
        return ThreadMessage.from_row(row) if row is not None else None

    def list_messages(
        self,
        *,
        chat_id: str,
        thread_id: str = "",
        root_id: str = "",
        parent_id: str = "",
        message_id: str = "",
        limit: int = 200,
    ) -> list[ThreadMessage]:
        chat = str(chat_id or "").strip()
        keys = thread_keys(thread_id=thread_id, root_id=root_id, parent_id=parent_id, message_id=message_id)
        if not chat or not keys:
            return []
        placeholders = ", ".join("?" for _ in keys)
        anchors: list[str] = [f"thread_key IN ({placeholders})"]
        params: list[Any] = [chat, *keys]
        for column, value in (
            ("thread_id", thread_id),
            ("root_id", root_id),
            ("parent_id", parent_id),
        ):
            anchor = str(value or "").strip()
            if anchor:
                anchors.append(f"{column} = ?")
                params.append(anchor)
        with self._lock:
            rows = self.conn.execute(
                f"""
                SELECT * FROM thread_message
                WHERE chat_id = ? AND ({' OR '.join(anchors)})
                ORDER BY created_at ASC, rowid ASC
                LIMIT ?
                """,
                (*params, max(1, min(int(limit or 200), 1000))),
            ).fetchall()
        return [ThreadMessage.from_row(row) for row in rows]

    def list_since(
        self,
        *,
        chat_id: str,
        thread_id: str = "",
        root_id: str = "",
        parent_id: str = "",
        message_id: str = "",
        after_message_id: str = "",
        limit: int = 200,
    ) -> list[ThreadMessage]:
        messages = self.list_messages(
            chat_id=chat_id,
            thread_id=thread_id,
            root_id=root_id,
            parent_id=parent_id,
            message_id=message_id,
            limit=limit,
        )
        marker = str(after_message_id or "").strip()
        if not marker:
            return messages
        for index, item in enumerate(messages):
            if item.message_id == marker:
                return messages[index + 1 :]
        return messages

    def agent_for_message(self, message_id: str) -> str:
        with self._lock:
            row = self.conn.execute(
                """
                SELECT sender_agent_id FROM thread_message
                WHERE message_id = ? AND sender_kind = 'agent'
                LIMIT 1
                """,
                (str(message_id or "").strip(),),
            ).fetchone()
        return str(row["sender_agent_id"] or "").strip().lower() if row else ""

    def agent_ids_in_thread(
        self,
        *,
        chat_id: str,
        thread_id: str = "",
        root_id: str = "",
        parent_id: str = "",
        message_id: str = "",
    ) -> list[str]:
        return list(
            dict.fromkeys(
                item.sender_agent_id
                for item in self.list_messages(
                    chat_id=chat_id,
                    thread_id=thread_id,
                    root_id=root_id,
                    parent_id=parent_id,
                    message_id=message_id,
                )
                if item.sender_kind == "agent" and item.sender_agent_id
            )
        )

    def mark_relay(
        self,
        *,
        relay_id: str,
        source_message_id: str,
        source_agent_id: str,
        target_agent_id: str,
        hop: int,
    ) -> bool:
        relay_key = f"{str(relay_id).strip()}:{str(target_agent_id).strip().lower()}"
        try:
            with self._lock:
                self.conn.execute(
                    """
                    INSERT INTO conversation_relay(
                        relay_key, relay_id, source_message_id, source_agent_id,
                        target_agent_id, hop, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        relay_key,
                        str(relay_id or "").strip(),
                        str(source_message_id or "").strip(),
                        str(source_agent_id or "").strip().lower(),
                        str(target_agent_id or "").strip().lower(),
                        int(hop),
                        utc_now(),
                    ),
                )
                self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def close_relay(self, relay_id: str) -> None:
        with self._lock:
            self.conn.execute(
                "DELETE FROM conversation_relay WHERE relay_id = ?", (str(relay_id or "").strip(),)
            )
            self.conn.commit()

    def record_event(self, event: Any) -> Any | None:
        """Insert one ConversationEvent idempotently.

        ``None`` means the event was already persisted by event id or its
        optional dedupe key.  The event object is kept provider-neutral here
        so the transcript store remains usable by legacy callers.
        """

        from agents.conversation.events import ConversationEvent

        if not isinstance(event, ConversationEvent):
            raise TypeError("event must be a ConversationEvent")
        with self._lock:
            try:
                self.conn.execute(
                    """
                    INSERT INTO conversation_event(
                        event_id, chat_id, thread_id, agent_id, event_type, text,
                        payload_json, visibility, source_message_id, session_id,
                        dedupe_key, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.chat_id,
                        event.thread_id,
                        event.agent_id,
                        event.type,
                        event.text,
                        json.dumps(event.payload, ensure_ascii=False, default=str),
                        event.visibility,
                        event.source_message_id,
                        event.session_id,
                        event.dedupe_key,
                        event.created_at,
                    ),
                )
                self.conn.commit()
                return event
            except sqlite3.IntegrityError:
                return None

    def get_event(self, event_id: str) -> Any | None:
        from agents.conversation.events import ConversationEvent

        with self._lock:
            row = self.conn.execute(
                "SELECT * FROM conversation_event WHERE event_id = ?",
                (str(event_id or "").strip(),),
            ).fetchone()
        return self._event_from_row(row) if row is not None else None

    def get_event_by_dedupe(self, dedupe_key: str) -> Any | None:
        """Return the durable event for an output idempotency key, if any."""

        key = str(dedupe_key or "").strip()
        if not key:
            return None
        with self._lock:
            row = self.conn.execute(
                "SELECT * FROM conversation_event WHERE dedupe_key = ?",
                (key,),
            ).fetchone()
        return self._event_from_row(row) if row is not None else None

    @staticmethod
    def _event_from_row(row: sqlite3.Row | dict[str, Any]) -> Any:
        from agents.conversation.events import ConversationEvent

        get = row.get if isinstance(row, dict) else row.__getitem__
        try:
            payload = json.loads(str(get("payload_json") or "{}"))
        except (TypeError, json.JSONDecodeError):
            payload = {}
        return ConversationEvent(
            event_id=str(get("event_id") or ""),
            chat_id=str(get("chat_id") or ""),
            thread_id=str(get("thread_id") or ""),
            agent_id=str(get("agent_id") or ""),
            type=str(get("event_type") or ""),
            text=get("text"),
            payload=payload if isinstance(payload, dict) else {},
            visibility=str(get("visibility") or "public"),
            source_message_id=str(get("source_message_id") or ""),
            session_id=str(get("session_id") or ""),
            dedupe_key=str(get("dedupe_key") or ""),
            created_at=str(get("created_at") or ""),
        )

    def list_events(
        self,
        *,
        chat_id: str = "",
        thread_id: str = "",
        after_event_id: str = "",
        limit: int = 200,
        visibility: str = "",
    ) -> list[Any]:
        clauses: list[str] = []
        params: list[Any] = []
        if str(chat_id or "").strip():
            clauses.append("chat_id = ?")
            params.append(str(chat_id).strip())
        if str(thread_id or "").strip():
            clauses.append("thread_id = ?")
            params.append(str(thread_id).strip())
        if str(visibility or "").strip():
            clauses.append("visibility = ?")
            params.append(str(visibility).strip().lower())
        marker = str(after_event_id or "").strip()
        bounded_limit = max(1, min(int(limit or 200), 1000))
        # Apply the cursor in SQL when possible.  Event IDs are not ordered,
        # so resolve the marker's durable position first rather than slicing
        # an arbitrarily limited page and accidentally replaying old events.
        if marker:
            with self._lock:
                marker_row = self.conn.execute(
                    "SELECT created_at, rowid FROM conversation_event WHERE event_id = ?",
                    (marker,),
                ).fetchone()
            if marker_row is not None:
                clauses.append("(created_at > ? OR (created_at = ? AND rowid > ?))")
                params.extend([marker_row["created_at"], marker_row["created_at"], marker_row["rowid"]])
        with self._lock:
            rows = self.conn.execute(
                f"SELECT * FROM conversation_event {('WHERE ' + ' AND '.join(clauses)) if clauses else ''} "
                "ORDER BY created_at ASC, rowid ASC LIMIT ?",
                (*params, bounded_limit),
            ).fetchall()
        return [self._event_from_row(row) for row in rows]
