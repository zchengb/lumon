from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from risk.migrations import connect, connect_global


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def risk_db_path(workspace: Path) -> Path:
    return Path(workspace).expanduser().resolve() / "risk" / "risk.sqlite3"


def global_db_path() -> Path:
    override = os.environ.get("LUMEN_AGENTS_HOME", "").strip()
    home = Path(override).expanduser() if override else Path.home() / ".lumon" / "agents"
    return home / "agents.sqlite3"


class RiskStore:
    def __init__(self, workspace: Path) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.path = risk_db_path(self.workspace)
        self.conn = connect(self.path)

    def close(self) -> None:
        self.conn.close()

    def execute(self, sql: str, params: tuple | list = ()) -> sqlite3.Cursor:
        return self.conn.execute(sql, params)

    def commit(self) -> None:
        self.conn.commit()

    def fetchone(self, sql: str, params: tuple | list = ()) -> Optional[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple | list = ()) -> list[sqlite3.Row]:
        return list(self.conn.execute(sql, params).fetchall())

    def upsert_scan_run(self, payload: dict[str, Any]) -> None:
        self.execute(
            """
            INSERT INTO scan_run(
                id, project_slug, source, started_at, completed_at, status,
                window_days, result_path, finding_count, high_count, data_freshness
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                completed_at=excluded.completed_at,
                status=excluded.status,
                finding_count=excluded.finding_count,
                high_count=excluded.high_count,
                data_freshness=excluded.data_freshness
            """,
            (
                payload["id"],
                payload["project_slug"],
                payload.get("source", "scan"),
                payload.get("started_at"),
                payload.get("completed_at"),
                payload.get("status", "completed"),
                payload.get("window_days"),
                payload.get("result_path"),
                payload.get("finding_count", 0),
                payload.get("high_count", 0),
                payload.get("data_freshness", "fresh"),
            ),
        )

    def get_finding_by_fingerprint(self, project_slug: str, fingerprint: str) -> Optional[sqlite3.Row]:
        return self.fetchone(
            "SELECT * FROM finding WHERE project_slug = ? AND canonical_fingerprint = ?",
            (project_slug, fingerprint),
        )

    def get_finding(self, finding_id: str) -> Optional[sqlite3.Row]:
        return self.fetchone("SELECT * FROM finding WHERE id = ?", (finding_id,))

    def list_findings(self, project_slug: str, statuses: Optional[list[str]] = None) -> list[sqlite3.Row]:
        if statuses:
            placeholders = ",".join("?" for _ in statuses)
            return self.fetchall(
                f"SELECT * FROM finding WHERE project_slug = ? AND status IN ({placeholders}) ORDER BY current_risk_score DESC",
                [project_slug, *statuses],
            )
        return self.fetchall(
            "SELECT * FROM finding WHERE project_slug = ? ORDER BY current_risk_score DESC",
            (project_slug,),
        )

    def insert_event(self, finding_id: str, event_type: str, **kwargs: Any) -> None:
        self.execute(
            """
            INSERT INTO finding_event(
                finding_id, event_type, previous_status, new_status,
                actor_type, actor_id, reason, occurred_at,
                source_message_id, trace_id, metadata_json, idempotency_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                finding_id,
                event_type,
                kwargs.get("previous_status"),
                kwargs.get("new_status"),
                kwargs.get("actor_type", "system"),
                kwargs.get("actor_id", "risk-engine"),
                kwargs.get("reason"),
                kwargs.get("occurred_at") or utc_now(),
                kwargs.get("source_message_id"),
                kwargs.get("trace_id"),
                kwargs.get("metadata_json"),
                kwargs.get("idempotency_key"),
            ),
        )

    def alert_already_sent(self, project_slug: str, event_key: str) -> bool:
        row = self.fetchone(
            """
            SELECT 1 FROM alert_delivery
            WHERE project_slug = ? AND event_key = ? AND status = 'sent'
            """,
            (project_slug, event_key),
        )
        return row is not None

    def get_alert(self, project_slug: str, event_key: str) -> Optional[sqlite3.Row]:
        return self.fetchone(
            "SELECT * FROM alert_delivery WHERE project_slug = ? AND event_key = ?",
            (project_slug, event_key),
        )

    def upsert_alert_attempt(
        self,
        project_slug: str,
        event_key: str,
        event_type: str,
        finding_id: str = "",
        *,
        status: str,
        attempt_count: int,
        last_error: str = "",
        next_retry_at: str = "",
        message_id: str = "",
    ) -> None:
        now = utc_now()
        existing = self.get_alert(project_slug, event_key)
        if existing is None:
            self.execute(
                """
                INSERT INTO alert_delivery(
                    project_slug, finding_id, event_key, event_type, delivered_at,
                    message_id, status, attempt_count, last_attempt_at, next_retry_at, last_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_slug,
                    finding_id or None,
                    event_key,
                    event_type,
                    now if status == "sent" else None,
                    message_id or None,
                    status,
                    attempt_count,
                    now,
                    next_retry_at or None,
                    last_error or None,
                ),
            )
            return
        self.execute(
            """
            UPDATE alert_delivery SET
                finding_id = COALESCE(?, finding_id),
                event_type = ?,
                delivered_at = CASE WHEN ? = 'sent' THEN ? ELSE delivered_at END,
                message_id = COALESCE(?, message_id),
                status = ?,
                attempt_count = ?,
                last_attempt_at = ?,
                next_retry_at = ?,
                last_error = ?
            WHERE project_slug = ? AND event_key = ?
            """,
            (
                finding_id or None,
                event_type,
                status,
                now,
                message_id or None,
                status,
                attempt_count,
                now,
                next_retry_at or None,
                last_error or None,
                project_slug,
                event_key,
            ),
        )

    def record_alert(self, project_slug: str, event_key: str, event_type: str, finding_id: str = "") -> None:
        self.upsert_alert_attempt(
            project_slug,
            event_key,
            event_type,
            finding_id,
            status="sent",
            attempt_count=1,
        )

    def list_retryable_alerts(self, project_slug: str = "", *, now: str = "") -> list[sqlite3.Row]:
        stamp = now or utc_now()
        if project_slug:
            return self.fetchall(
                """
                SELECT * FROM alert_delivery
                WHERE project_slug = ?
                  AND status IN ('pending', 'failed')
                  AND (next_retry_at IS NULL OR next_retry_at <= ?)
                ORDER BY id ASC
                """,
                (project_slug, stamp),
            )
        return self.fetchall(
            """
            SELECT * FROM alert_delivery
            WHERE status IN ('pending', 'failed')
              AND (next_retry_at IS NULL OR next_retry_at <= ?)
            ORDER BY id ASC
            """,
            (stamp,),
        )

    def list_alerts(self, project_slug: str = "", status: str = "") -> list[sqlite3.Row]:
        clauses: list[str] = []
        params: list[Any] = []
        if project_slug:
            clauses.append("project_slug = ?")
            params.append(project_slug)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        return self.fetchall(f"SELECT * FROM alert_delivery {where} ORDER BY id DESC", params)

    def latest_project_snapshot(self, project_slug: str) -> Optional[sqlite3.Row]:
        return self.fetchone(
            "SELECT * FROM project_risk_snapshot WHERE project_slug = ? ORDER BY id DESC LIMIT 1",
            (project_slug,),
        )

    def previous_project_snapshot(self, project_slug: str) -> Optional[sqlite3.Row]:
        rows = self.fetchall(
            "SELECT * FROM project_risk_snapshot WHERE project_slug = ? ORDER BY id DESC LIMIT 2",
            (project_slug,),
        )
        return rows[1] if len(rows) > 1 else None


RETRY_DELAYS_MINUTES = (0, 1, 5, 30)


def next_alert_retry_at(attempt_count: int, *, now: Optional[datetime] = None) -> str:
    base = now or datetime.now(timezone.utc)
    if attempt_count >= len(RETRY_DELAYS_MINUTES):
        return ""
    delay = RETRY_DELAYS_MINUTES[max(attempt_count - 1, 0)]
    return (base + timedelta(minutes=delay)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class GlobalAgentStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or global_db_path()
        self.conn = connect_global(self.path)
        self._ensure_chat_map_migrated()

    def close(self) -> None:
        self.conn.close()

    def _ensure_chat_map_migrated(self) -> None:
        row = self.conn.execute(
            "SELECT value FROM meta WHERE key = 'chat_projects_json_imported'"
        ).fetchone()
        if row is not None:
            return
        path = Path.home() / ".lumon" / "agents" / "chat_projects.json"
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
            chat_map = data.get("chat_project_map") if isinstance(data, dict) else {}
            if isinstance(chat_map, dict):
                for chat_id, slug in chat_map.items():
                    chat = str(chat_id or "").strip()
                    project = str(slug or "").strip()
                    if not chat or not project:
                        continue
                    existing = self.get_chat_project(chat)
                    if existing:
                        continue
                    self.conn.execute(
                        """
                        INSERT OR IGNORE INTO chat_project_map(chat_id, project_slug, updated_at)
                        VALUES (?, ?, ?)
                        """,
                        (chat, project, utc_now()),
                    )
        self.conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES ('chat_projects_json_imported', '1')"
        )
        self.conn.commit()

    def set_chat_project(self, chat_id: str, project_slug: str) -> None:
        self.conn.execute(
            """
            INSERT INTO chat_project_map(chat_id, project_slug, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET project_slug=excluded.project_slug, updated_at=excluded.updated_at
            """,
            (chat_id, project_slug, utc_now()),
        )
        self.conn.commit()

    def get_chat_project(self, chat_id: str) -> str:
        row = self.conn.execute(
            "SELECT project_slug FROM chat_project_map WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()
        return str(row["project_slug"]) if row else ""

    def chat_id_for_project(self, project_slug: str) -> str:
        row = self.conn.execute(
            "SELECT chat_id FROM chat_project_map WHERE project_slug = ? ORDER BY updated_at DESC LIMIT 1",
            (project_slug,),
        ).fetchone()
        return str(row["chat_id"]) if row else ""

    def cache_project_summary(self, project_slug: str, summary: dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT INTO project_summary_cache(project_slug, summary_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(project_slug) DO UPDATE SET summary_json=excluded.summary_json, updated_at=excluded.updated_at
            """,
            (project_slug, json.dumps(summary, ensure_ascii=False), utc_now()),
        )
        self.conn.commit()

    def save_agent_run(self, payload: dict[str, Any]) -> None:
        now = utc_now()
        self.conn.execute(
            """
            INSERT INTO agent_run(
                run_id, agent_id, project_slug, chat_id, thread_id, user_id, action, status,
                started_at, completed_at, result_path, summary_json, error, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                status=excluded.status,
                completed_at=excluded.completed_at,
                result_path=excluded.result_path,
                summary_json=excluded.summary_json,
                error=excluded.error,
                updated_at=excluded.updated_at
            """,
            (
                payload["run_id"],
                payload.get("agent_id", "dylan"),
                payload.get("project_slug"),
                payload.get("chat_id"),
                payload.get("thread_id"),
                payload.get("user_id"),
                payload.get("action", "scan.run"),
                payload.get("status", "running"),
                payload.get("started_at") or now,
                payload.get("completed_at"),
                payload.get("result_path"),
                json.dumps(payload.get("summary") or {}, ensure_ascii=False),
                payload.get("error"),
                now,
                now,
            ),
        )
        self.conn.commit()

    def get_agent_run(self, run_id: str) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM agent_run WHERE run_id = ?", (run_id,)).fetchone()

    def resolve_recent_run(
        self,
        *,
        chat_id: str = "",
        thread_id: str = "",
        user_id: str = "",
        project_slug: str = "",
        action_prefix: str = "scan.",
    ) -> Optional[sqlite3.Row]:
        queries = [
            (
                "chat_id = ? AND thread_id = ? AND user_id = ?",
                [chat_id, thread_id, user_id],
                chat_id and thread_id and user_id,
            ),
            (
                "chat_id = ? AND thread_id = ?",
                [chat_id, thread_id],
                chat_id and thread_id,
            ),
            (
                "chat_id = ? AND user_id = ?",
                [chat_id, user_id],
                chat_id and user_id,
            ),
            (
                "chat_id = ? AND project_slug = ?",
                [chat_id, project_slug],
                chat_id and project_slug,
            ),
            (
                "project_slug = ?",
                [project_slug],
                bool(project_slug),
            ),
        ]
        for where, params, ok in queries:
            if not ok:
                continue
            row = self.conn.execute(
                f"""
                SELECT * FROM agent_run
                WHERE {where} AND action LIKE ?
                ORDER BY updated_at DESC LIMIT 1
                """,
                [*params, f"{action_prefix}%"],
            ).fetchone()
            if row is not None:
                return row
        return None

    def get_conversation_context(
        self,
        *,
        chat_id: str,
        thread_id: str = "",
        user_id: str = "",
    ) -> Optional[sqlite3.Row]:
        if chat_id and thread_id and user_id:
            return self.conn.execute(
                """
                SELECT * FROM conversation_context
                WHERE chat_id = ? AND thread_id = ? AND user_id = ?
                ORDER BY updated_at DESC LIMIT 1
                """,
                (chat_id, thread_id, user_id),
            ).fetchone()
        if chat_id and user_id and not thread_id:
            return self.conn.execute(
                """
                SELECT * FROM conversation_context
                WHERE chat_id = ? AND user_id = ?
                ORDER BY updated_at DESC LIMIT 1
                """,
                (chat_id, user_id),
            ).fetchone()
        return None

    def upsert_conversation_context(self, payload: dict[str, Any]) -> None:
        now = utc_now()
        expires = (
            datetime.now(timezone.utc) + timedelta(days=7)
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        chat_id = str(payload.get("chat_id") or "")
        thread_id = str(payload.get("thread_id") or "")
        user_id = str(payload.get("user_id") or "")
        existing = self.get_conversation_context(chat_id=chat_id, thread_id=thread_id, user_id=user_id)
        values = (
            chat_id,
            thread_id,
            user_id,
            payload.get("project_slug"),
            payload.get("last_intent"),
            payload.get("last_run_id"),
            payload.get("last_finding_id"),
            json.dumps(payload.get("last_result_ids") or [], ensure_ascii=False),
            json.dumps(payload.get("recent_entities") or {}, ensure_ascii=False),
            payload.get("original_language"),
            expires,
            now,
        )
        if existing is None:
            self.conn.execute(
                """
                INSERT INTO conversation_context(
                    chat_id, thread_id, user_id, project_slug, last_intent, last_run_id,
                    last_finding_id, last_result_ids_json, recent_entities_json,
                    original_language, expires_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (*values, now),
            )
        else:
            self.conn.execute(
                """
                UPDATE conversation_context SET
                    project_slug = COALESCE(?, project_slug),
                    last_intent = COALESCE(?, last_intent),
                    last_run_id = COALESCE(?, last_run_id),
                    last_finding_id = COALESCE(?, last_finding_id),
                    last_result_ids_json = COALESCE(?, last_result_ids_json),
                    recent_entities_json = COALESCE(?, recent_entities_json),
                    original_language = COALESCE(?, original_language),
                    expires_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    payload.get("project_slug"),
                    payload.get("last_intent"),
                    payload.get("last_run_id"),
                    payload.get("last_finding_id"),
                    json.dumps(payload.get("last_result_ids") or [], ensure_ascii=False)
                    if "last_result_ids" in payload
                    else None,
                    json.dumps(payload.get("recent_entities") or {}, ensure_ascii=False)
                    if "recent_entities" in payload
                    else None,
                    payload.get("original_language"),
                    expires,
                    now,
                    existing["id"],
                ),
            )
        self.conn.commit()

    def log_conversation(self, payload: dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT INTO conversation_log(
                message_id, chat_id, thread_id, user_id, agent_id, original_text_hash,
                normalized_text, resolved_project, router_source, intent, confidence,
                tool_calls, response_mode, validation_result, latency_ms, error_code, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.get("message_id"),
                payload.get("chat_id"),
                payload.get("thread_id"),
                payload.get("user_id"),
                payload.get("agent_id", "dylan"),
                payload.get("original_text_hash"),
                payload.get("normalized_text"),
                payload.get("resolved_project"),
                payload.get("router_source"),
                payload.get("intent"),
                payload.get("confidence"),
                json.dumps(payload.get("tool_calls") or [], ensure_ascii=False),
                payload.get("response_mode"),
                json.dumps(payload.get("validation_result") or {}, ensure_ascii=False),
                payload.get("latency_ms"),
                payload.get("error_code"),
                utc_now(),
            ),
        )
        self.conn.commit()

    def list_recent_feishu_ids(self, *, limit: int = 20) -> dict[str, list[str]]:
        cap = max(1, min(int(limit or 20), 50))
        users: list[str] = []
        chats: list[str] = []
        seen_users: set[str] = set()
        seen_chats: set[str] = set()
        queries = (
            ("user_id", "SELECT user_id AS value FROM conversation_context WHERE user_id != '' ORDER BY updated_at DESC LIMIT ?"),
            ("user_id", "SELECT user_id AS value FROM agent_run WHERE user_id != '' ORDER BY updated_at DESC LIMIT ?"),
            ("user_id", "SELECT user_id AS value FROM conversation_log WHERE user_id != '' ORDER BY created_at DESC LIMIT ?"),
            (
                "user_id",
                "SELECT identity_id AS value FROM feishu_identity "
                "WHERE identity_type = 'user' AND identity_id LIKE 'ou_%' "
                "ORDER BY updated_at DESC LIMIT ?",
            ),
            ("chat_id", "SELECT chat_id AS value FROM conversation_context WHERE chat_id != '' ORDER BY updated_at DESC LIMIT ?"),
            ("chat_id", "SELECT chat_id AS value FROM agent_run WHERE chat_id != '' ORDER BY updated_at DESC LIMIT ?"),
            ("chat_id", "SELECT chat_id AS value FROM chat_project_map WHERE chat_id != '' ORDER BY updated_at DESC LIMIT ?"),
            (
                "chat_id",
                "SELECT identity_id AS value FROM feishu_identity WHERE identity_type = 'chat' AND identity_id LIKE 'oc_%' ORDER BY updated_at DESC LIMIT ?",
            ),
        )
        for kind, sql in queries:
            try:
                rows = self.conn.execute(sql, (cap,)).fetchall()
            except Exception:
                continue
            for row in rows:
                value = str(row["value"] if isinstance(row, sqlite3.Row) else row[0] or "").strip()
                if not value:
                    continue
                if kind == "user_id":
                    if not value.startswith("ou_") or len(value) < 20 or value in seen_users:
                        continue
                    seen_users.add(value)
                    users.append(value)
                elif kind == "chat_id":
                    # Real Feishu open_chat_id is oc_ + long hex. Skip project aliases like oc_mbpass.
                    if not value.startswith("oc_") or len(value) < 20 or value in seen_chats:
                        continue
                    seen_chats.add(value)
                    chats.append(value)
        return {"user_ids": users[:cap], "chat_ids": chats[:cap]}

    def record_feishu_user_context(
        self,
        *,
        user_id: str,
        chat_id: str = "",
        chat_type: str = "",
    ) -> None:
        """Remember whether a human identity was observed in a DM or group."""
        uid = str(user_id or "").strip()
        if not uid:
            return
        kind = str(chat_type or "").strip().lower()
        context_type = "dm" if kind in {"p2p", "private", "dm"} else "group"
        self.conn.execute(
            """
            INSERT INTO feishu_user_context(user_id, chat_id, context_type, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, chat_id, context_type) DO UPDATE SET
                updated_at = excluded.updated_at
            """,
            (uid, str(chat_id or "").strip(), context_type, utc_now()),
        )
        self.conn.commit()

    def record_feishu_chat_context(self, *, chat_id: str, chat_type: str = "") -> None:
        """Remember whether a Feishu chat is a group or one-to-one conversation."""
        cid = str(chat_id or "").strip()
        if not cid:
            return
        kind = str(chat_type or "").strip().lower()
        context_type = "dm" if kind in {"p2p", "private", "dm"} else "group"
        self.conn.execute(
            """
            INSERT INTO feishu_chat_context(chat_id, context_type, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                context_type = excluded.context_type,
                updated_at = excluded.updated_at
            """,
            (cid, context_type, utc_now()),
        )
        self.conn.commit()

    def get_feishu_chat_context(self, chat_id: str) -> str:
        """Return the last observed chat context, falling back to sender context."""
        cid = str(chat_id or "").strip()
        if not cid:
            return ""
        try:
            row = self.conn.execute(
                "SELECT context_type FROM feishu_chat_context WHERE chat_id = ?",
                (cid,),
            ).fetchone()
            if row:
                return str(row["context_type"] if isinstance(row, sqlite3.Row) else row[0] or "").strip().lower()
            row = self.conn.execute(
                """
                SELECT context_type
                FROM feishu_user_context
                WHERE chat_id = ? AND chat_id != ''
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (cid,),
            ).fetchone()
            if row:
                return str(row["context_type"] if isinstance(row, sqlite3.Row) else row[0] or "").strip().lower()
        except Exception:
            return ""
        return ""

    def _list_recent_feishu_chat_ids(self, *, context_type: str, limit: int = 100) -> list[str]:
        cap = max(1, min(int(limit or 100), 500))
        kind = str(context_type or "").strip().lower()
        if kind not in {"group", "dm"}:
            return []
        try:
            rows = self.conn.execute(
                """
                SELECT chat_id, MAX(updated_at) AS last_seen
                FROM (
                    SELECT chat_id, updated_at
                    FROM feishu_chat_context
                    WHERE context_type = ? AND chat_id != ''
                    UNION ALL
                    SELECT chat_id, updated_at
                    FROM feishu_user_context
                    WHERE context_type = ? AND chat_id != ''
                )
                GROUP BY chat_id
                ORDER BY last_seen DESC
                LIMIT ?
                """,
                (kind, kind, cap),
            ).fetchall()
        except Exception:
            return []
        return [
            str(row["chat_id"] if isinstance(row, sqlite3.Row) else row[0] or "").strip()
            for row in rows
            if str(row["chat_id"] if isinstance(row, sqlite3.Row) else row[0] or "").strip()
        ]

    def list_recent_feishu_group_chat_ids(self, *, limit: int = 100) -> list[str]:
        """Return chat IDs observed as groups, never untyped identity rows."""
        return self._list_recent_feishu_chat_ids(context_type="group", limit=limit)

    def list_recent_feishu_dm_chat_ids(self, *, limit: int = 100) -> list[str]:
        """Return chat IDs observed as one-to-one conversations."""
        return self._list_recent_feishu_chat_ids(context_type="dm", limit=limit)

    def list_recent_feishu_dm_user_ids(self, *, limit: int = 50) -> list[str]:
        """Return human identities observed in one-to-one Feishu chats."""
        cap = max(1, min(int(limit or 50), 200))
        try:
            rows = self.conn.execute(
                """
                SELECT user_id, MAX(updated_at) AS last_seen
                FROM feishu_user_context
                WHERE context_type = 'dm' AND user_id != ''
                GROUP BY user_id
                ORDER BY last_seen DESC
                LIMIT ?
                """,
                (cap,),
            ).fetchall()
        except Exception:
            return []
        return [
            str(row["user_id"] if isinstance(row, sqlite3.Row) else row[0] or "").strip()
            for row in rows
            if str(row["user_id"] if isinstance(row, sqlite3.Row) else row[0] or "").strip()
        ]

    def upsert_feishu_identity(
        self,
        *,
        identity_id: str,
        identity_type: str,
        display_name: str,
        union_id: str = "",
    ) -> None:
        iid = str(identity_id or "").strip()
        name = str(display_name or "").strip()
        kind = str(identity_type or "").strip().lower() or "user"
        union = str(union_id or "").strip()
        if not iid:
            return
        self.conn.execute(
            """
            INSERT INTO feishu_identity(identity_id, identity_type, display_name, union_id, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(identity_id) DO UPDATE SET
                identity_type = excluded.identity_type,
                display_name = excluded.display_name,
                union_id = CASE
                    WHEN excluded.union_id != '' THEN excluded.union_id
                    ELSE feishu_identity.union_id
                END,
                updated_at = excluded.updated_at
            """,
            (iid, kind, name, union, utc_now()),
        )
        self.conn.commit()

    def get_feishu_display_name(self, identity_id: str) -> str:
        iid = str(identity_id or "").strip()
        if not iid:
            return ""
        try:
            row = self.conn.execute(
                "SELECT display_name FROM feishu_identity WHERE identity_id = ?",
                (iid,),
            ).fetchone()
        except Exception:
            return ""
        if row is None:
            return ""
        return str(row["display_name"] if isinstance(row, sqlite3.Row) else row[0] or "").strip()

    def get_feishu_union_id(self, identity_id: str) -> str:
        iid = str(identity_id or "").strip()
        if not iid:
            return ""
        try:
            row = self.conn.execute(
                "SELECT union_id FROM feishu_identity WHERE identity_id = ?",
                (iid,),
            ).fetchone()
        except Exception:
            return ""
        if row is None:
            return ""
        return str(row["union_id"] if isinstance(row, sqlite3.Row) else row[0] or "").strip()

    def expand_feishu_open_ids(self, identity_ids: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        unions: set[str] = set()
        for identity_id in identity_ids:
            iid = str(identity_id or "").strip()
            if not iid or iid in seen:
                continue
            seen.add(iid)
            out.append(iid)
            union = self.get_feishu_union_id(iid)
            if union:
                unions.add(union)
        for union in unions:
            try:
                rows = self.conn.execute(
                    "SELECT identity_id FROM feishu_identity WHERE union_id = ?",
                    (union,),
                ).fetchall()
            except Exception:
                continue
            for row in rows:
                iid = str(row["identity_id"] if isinstance(row, sqlite3.Row) else row[0] or "").strip()
                if not iid or iid in seen:
                    continue
                seen.add(iid)
                out.append(iid)
        return out

    def list_feishu_identities(self, identity_ids: list[str]) -> dict[str, str]:
        out: dict[str, str] = {}
        for identity_id in identity_ids:
            name = self.get_feishu_display_name(identity_id)
            if name:
                out[str(identity_id).strip()] = name
        return out
