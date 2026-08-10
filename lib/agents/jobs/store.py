from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_job_id(prefix: str = "job") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class AgentJob:
    job_id: str
    type: str
    status: str
    project: str = ""
    requested_by: str = ""
    delegated_by: str = ""
    target_agent: str = ""
    capability: str = ""
    parent_job_id: str = ""
    depends_on: list[str] = field(default_factory=list)
    input: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    source_message_id: str = ""
    chat_id: str = ""
    thread_id: str = ""
    trace_id: str = ""
    error: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AgentJobStore:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            home = Path.home() / ".lumon" / "agents"
            home.mkdir(parents=True, exist_ok=True)
            path = home / "agent_jobs.sqlite3"
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self._migrate()

    def close(self) -> None:
        self.conn.close()

    def _migrate(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_job (
                job_id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                status TEXT NOT NULL,
                project TEXT,
                requested_by TEXT,
                delegated_by TEXT,
                target_agent TEXT,
                capability TEXT,
                parent_job_id TEXT,
                depends_on_json TEXT,
                input_json TEXT,
                result_json TEXT,
                source_message_id TEXT,
                chat_id TEXT,
                thread_id TEXT,
                trace_id TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def _row_to_job(self, row: sqlite3.Row) -> AgentJob:
        return AgentJob(
            job_id=row["job_id"],
            type=row["type"],
            status=row["status"],
            project=row["project"] or "",
            requested_by=row["requested_by"] or "",
            delegated_by=row["delegated_by"] or "",
            target_agent=row["target_agent"] or "",
            capability=row["capability"] or "",
            parent_job_id=row["parent_job_id"] or "",
            depends_on=json.loads(row["depends_on_json"] or "[]"),
            input=json.loads(row["input_json"] or "{}"),
            result=json.loads(row["result_json"] or "{}"),
            source_message_id=row["source_message_id"] or "",
            chat_id=row["chat_id"] or "",
            thread_id=row["thread_id"] or "",
            trace_id=row["trace_id"] or "",
            error=row["error"] or "",
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or "",
        )

    def save(self, job: AgentJob) -> AgentJob:
        now = utc_now()
        if not job.created_at:
            job.created_at = now
        job.updated_at = now
        self.conn.execute(
            """
            INSERT INTO agent_job (
                job_id, type, status, project, requested_by, delegated_by, target_agent, capability,
                parent_job_id, depends_on_json, input_json, result_json, source_message_id, chat_id,
                thread_id, trace_id, error, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                status=excluded.status,
                result_json=excluded.result_json,
                error=excluded.error,
                updated_at=excluded.updated_at,
                depends_on_json=excluded.depends_on_json,
                input_json=excluded.input_json
            """,
            (
                job.job_id,
                job.type,
                job.status,
                job.project,
                job.requested_by,
                job.delegated_by,
                job.target_agent,
                job.capability,
                job.parent_job_id,
                json.dumps(job.depends_on, ensure_ascii=False),
                json.dumps(job.input, ensure_ascii=False),
                json.dumps(job.result, ensure_ascii=False),
                job.source_message_id,
                job.chat_id,
                job.thread_id,
                job.trace_id,
                job.error,
                job.created_at,
                job.updated_at,
            ),
        )
        self.conn.commit()
        return job

    def get(self, job_id: str) -> Optional[AgentJob]:
        row = self.conn.execute("SELECT * FROM agent_job WHERE job_id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def list_jobs(
        self,
        *,
        parent_job_id: str = "",
        project: str = "",
        limit: int = 50,
    ) -> list[AgentJob]:
        sql = "SELECT * FROM agent_job WHERE 1=1"
        args: list[Any] = []
        if parent_job_id:
            sql += " AND parent_job_id = ?"
            args.append(parent_job_id)
        if project:
            sql += " AND project = ?"
            args.append(project)
        sql += " ORDER BY created_at DESC LIMIT ?"
        args.append(int(limit))
        return [self._row_to_job(row) for row in self.conn.execute(sql, args).fetchall()]

    def children(self, parent_job_id: str) -> list[AgentJob]:
        return self.list_jobs(parent_job_id=parent_job_id, limit=200)
