from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from risk.store import GlobalAgentStore, utc_now

_LOG = logging.getLogger("lumen.agent.obs")


def new_trace_id() -> str:
    return f"tr_{uuid.uuid4().hex[:20]}"


def hash_id(value: str) -> str:
    raw = str(value or "").encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()[:16]


def prompt_hash(text: str) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()[:16]


@dataclass
class TraceContext:
    trace_id: str
    message_id: str = ""
    chat_id: str = ""
    thread_id: str = ""
    user_id: str = ""
    project_slug: str = ""
    provider: str = ""
    model: str = ""
    agent_id: str = ""
    role: str = ""
    workflow: str = ""
    started_at: float = field(default_factory=time.time)


class Observability:
    def __init__(self, store: Optional[GlobalAgentStore] = None, *, agent_id: str = "dylan") -> None:
        self._owned = store is None
        self.store = store or GlobalAgentStore()
        self.agent_id = str(agent_id or "dylan").strip().lower() or "dylan"
        self.jsonl_path = Path(self.store.path).parent / f"{self.agent_id}.jsonl"
        self.traces_dir = Path(self.store.path).parent / "traces"
        self.traces_dir.mkdir(parents=True, exist_ok=True)

    def close(self) -> None:
        if self._owned:
            self.store.close()

    def emit(self, ctx: TraceContext, event: str, **payload: Any) -> None:
        now = utc_now()
        record = {
            "timestamp": now,
            "level": str(payload.pop("level", "INFO")),
            "event": event,
            "trace_id": ctx.trace_id,
            "message_id": ctx.message_id,
            "chat_id_hash": hash_id(ctx.chat_id) if ctx.chat_id else "",
            "thread_id": ctx.thread_id,
            "user_id_hash": hash_id(ctx.user_id) if ctx.user_id else "",
            "project_slug": ctx.project_slug,
            "provider": ctx.provider,
            "model": ctx.model,
            "agent_id": ctx.agent_id or self.agent_id,
            "role": ctx.role,
            "workflow": ctx.workflow,
            **payload,
        }
        line = json.dumps(record, ensure_ascii=False, default=str)
        _LOG.info("%s", line)
        try:
            with self.jsonl_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except Exception:
            pass
        try:
            event_payload = {
                "agent_id": ctx.agent_id or self.agent_id,
                "role": ctx.role,
                "workflow": ctx.workflow,
                **payload,
            }
            self.store.conn.execute(
                """
                INSERT INTO conversation_event(trace_id, event, payload_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (ctx.trace_id, event, json.dumps(event_payload, ensure_ascii=False, default=str), now),
            )
            self.store.conn.commit()
        except Exception:
            pass

    def upsert_trace(self, ctx: TraceContext, **fields: Any) -> None:
        existing = self.store.conn.execute(
            "SELECT trace_id FROM conversation_trace WHERE trace_id = ?",
            (ctx.trace_id,),
        ).fetchone()
        now = utc_now()
        if existing is None:
            self.store.conn.execute(
                """
                INSERT INTO conversation_trace(
                    trace_id, message_id, chat_id_hash, thread_id, user_id_hash, project_slug,
                    state, provider, model, started_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ctx.trace_id,
                    ctx.message_id,
                    hash_id(ctx.chat_id) if ctx.chat_id else "",
                    ctx.thread_id,
                    hash_id(ctx.user_id) if ctx.user_id else "",
                    ctx.project_slug,
                    fields.get("state", "received"),
                    ctx.provider,
                    ctx.model,
                    now,
                ),
            )
        else:
            sets = []
            values: list[Any] = []
            for key in (
                "state",
                "project_slug",
                "provider",
                "model",
                "planner_status",
                "responder_status",
                "reply_status",
                "reaction_status",
                "completed_at",
                "latency_ms",
                "error_code",
            ):
                if key in fields:
                    sets.append(f"{key} = ?")
                    values.append(fields[key])
            if sets:
                values.append(ctx.trace_id)
                self.store.conn.execute(
                    f"UPDATE conversation_trace SET {', '.join(sets)} WHERE trace_id = ?",
                    values,
                )
        self.store.conn.commit()

    def record_agent_invocation(self, ctx: TraceContext, **fields: Any) -> None:
        self.store.conn.execute(
            """
            INSERT INTO agent_invocation(
                trace_id, phase, provider, model, latency_ms, exit_code, timed_out,
                retry_count, prompt_hash, response_hash, parse_status, error_code, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ctx.trace_id,
                fields.get("phase"),
                fields.get("provider") or ctx.provider,
                fields.get("model") or ctx.model,
                fields.get("latency_ms"),
                fields.get("exit_code"),
                1 if fields.get("timed_out") else 0,
                fields.get("retry_count", 0),
                fields.get("prompt_hash"),
                fields.get("response_hash"),
                fields.get("parse_status"),
                fields.get("error_code"),
                utc_now(),
            ),
        )
        self.store.conn.commit()

    def record_tool_invocation(self, ctx: TraceContext, **fields: Any) -> None:
        self.store.conn.execute(
            """
            INSERT INTO tool_invocation(
                trace_id, task_id, tool_name, arguments_summary, status, result_count,
                freshness, latency_ms, error_code, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ctx.trace_id,
                fields.get("task_id"),
                fields.get("tool_name"),
                fields.get("arguments_summary"),
                fields.get("status"),
                fields.get("result_count"),
                fields.get("freshness"),
                fields.get("latency_ms"),
                fields.get("error_code"),
                utc_now(),
            ),
        )
        self.store.conn.commit()

    def record_reaction(self, ctx: TraceContext, **fields: Any) -> None:
        self.store.conn.execute(
            """
            INSERT INTO reaction_session(
                trace_id, source_message_id, reaction_id, emoji_type, status,
                add_attempts, remove_attempts, added_at, removed_at, last_error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ctx.trace_id,
                fields.get("source_message_id"),
                fields.get("reaction_id"),
                fields.get("emoji_type"),
                fields.get("status"),
                fields.get("add_attempts", 0),
                fields.get("remove_attempts", 0),
                fields.get("added_at"),
                fields.get("removed_at"),
                fields.get("last_error"),
            ),
        )
        self.store.conn.commit()

    def get_trace(self, trace_id: str) -> Optional[dict[str, Any]]:
        row = self.store.conn.execute(
            "SELECT * FROM conversation_trace WHERE trace_id = ?",
            (trace_id,),
        ).fetchone()
        return dict(row) if row is not None else None

    def latest_trace(self) -> Optional[dict[str, Any]]:
        row = self.store.conn.execute(
            "SELECT * FROM conversation_trace ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row is not None else None

    def events_for_trace(self, trace_id: str) -> list[dict[str, Any]]:
        rows = self.store.conn.execute(
            "SELECT * FROM conversation_event WHERE trace_id = ? ORDER BY id ASC",
            (trace_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_trace_by_message_id(self, message_id: str) -> Optional[dict[str, Any]]:
        row = self.store.conn.execute(
            "SELECT * FROM conversation_trace WHERE message_id = ? ORDER BY started_at DESC LIMIT 1",
            (message_id,),
        ).fetchone()
        return dict(row) if row is not None else None

    def list_stale_reactions(self, older_than_seconds: int = 120) -> list[dict[str, Any]]:
        rows = self.store.conn.execute(
            """
            SELECT * FROM reaction_session
            WHERE status IN ('active', 'add_succeeded', 'remove_failed')
              AND COALESCE(removed_at, '') = ''
              AND COALESCE(reaction_id, '') != ''
              AND COALESCE(remove_attempts, 0) < 5
            ORDER BY id ASC
            LIMIT 20
            """
        ).fetchall()
        return [dict(row) for row in rows]
