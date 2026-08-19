from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 6

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scan_run (
    id TEXT PRIMARY KEY,
    project_slug TEXT NOT NULL,
    source TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    status TEXT NOT NULL,
    window_days INTEGER,
    result_path TEXT,
    finding_count INTEGER DEFAULT 0,
    high_count INTEGER DEFAULT 0,
    data_freshness TEXT DEFAULT 'fresh'
);

CREATE TABLE IF NOT EXISTS finding (
    id TEXT PRIMARY KEY,
    project_slug TEXT NOT NULL,
    canonical_fingerprint TEXT NOT NULL,
    registry_issue_id TEXT,
    repository TEXT,
    module TEXT,
    title TEXT,
    category TEXT,
    source_severity TEXT,
    effective_severity TEXT,
    status TEXT NOT NULL,
    first_seen_at TEXT,
    last_seen_at TEXT,
    resolved_at TEXT,
    reopened_count INTEGER DEFAULT 0,
    recurrence_count INTEGER DEFAULT 0,
    occurrence_count INTEGER NOT NULL DEFAULT 0,
    consecutive_seen_count INTEGER NOT NULL DEFAULT 0,
    verification_status TEXT NOT NULL DEFAULT 'observed',
    remediation_status TEXT NOT NULL DEFAULT 'none',
    last_verified_at TEXT,
    last_verification_run_id TEXT,
    last_seen_scan_run_id TEXT,
    current_risk_score REAL DEFAULT 0,
    current_risk_band TEXT DEFAULT 'Low',
    UNIQUE(project_slug, canonical_fingerprint)
);

CREATE TABLE IF NOT EXISTS finding_occurrence (
    id TEXT PRIMARY KEY,
    finding_id TEXT NOT NULL,
    scan_run_id TEXT NOT NULL,
    file TEXT,
    line_range TEXT,
    trigger_signature TEXT,
    evidence_hash TEXT,
    commit_sha TEXT,
    detected_at TEXT,
    FOREIGN KEY(finding_id) REFERENCES finding(id),
    FOREIGN KEY(scan_run_id) REFERENCES scan_run(id)
);

CREATE TABLE IF NOT EXISTS severity_adjustment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id TEXT NOT NULL,
    source_severity TEXT,
    effective_severity TEXT,
    direction TEXT,
    reason_codes TEXT,
    rule_version TEXT,
    adjusted_at TEXT,
    confirmed_by TEXT,
    FOREIGN KEY(finding_id) REFERENCES finding(id)
);

CREATE TABLE IF NOT EXISTS external_link (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id TEXT NOT NULL,
    type TEXT NOT NULL,
    external_id TEXT,
    url TEXT,
    status TEXT,
    owner TEXT,
    last_synced_at TEXT,
    FOREIGN KEY(finding_id) REFERENCES finding(id)
);

CREATE TABLE IF NOT EXISTS finding_event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    previous_status TEXT,
    new_status TEXT,
    actor_type TEXT,
    actor_id TEXT,
    reason TEXT,
    occurred_at TEXT,
    FOREIGN KEY(finding_id) REFERENCES finding(id)
);

CREATE TABLE IF NOT EXISTS ignore_policy (
    finding_id TEXT PRIMARY KEY,
    ignored_by TEXT,
    ignored_at TEXT,
    expires_at TEXT,
    invalidation_rules TEXT,
    reason TEXT,
    FOREIGN KEY(finding_id) REFERENCES finding(id)
);

CREATE TABLE IF NOT EXISTS project_risk_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_slug TEXT NOT NULL,
    scan_run_id TEXT,
    score REAL NOT NULL,
    band TEXT NOT NULL,
    open_high INTEGER DEFAULT 0,
    reopened INTEGER DEFAULT 0,
    overdue_high INTEGER DEFAULT 0,
    payload_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alert_delivery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_slug TEXT NOT NULL,
    finding_id TEXT,
    event_key TEXT NOT NULL,
    event_type TEXT NOT NULL,
    delivered_at TEXT,
    message_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TEXT,
    next_retry_at TEXT,
    last_error TEXT,
    UNIQUE(project_slug, event_key)
);

CREATE TABLE IF NOT EXISTS verification_request (
    id TEXT PRIMARY KEY,
    finding_id TEXT NOT NULL,
    project_slug TEXT NOT NULL,
    requested_by TEXT,
    source_message_id TEXT,
    trace_id TEXT,
    requested_at TEXT NOT NULL,
    status TEXT NOT NULL,
    policy_json TEXT,
    scope_json TEXT,
    remediation_snapshot_json TEXT,
    FOREIGN KEY(finding_id) REFERENCES finding(id)
);

CREATE TABLE IF NOT EXISTS verification_run (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    finding_id TEXT NOT NULL,
    scan_run_id TEXT,
    detector TEXT,
    started_at TEXT,
    completed_at TEXT,
    result TEXT NOT NULL,
    observed INTEGER,
    coverage_json TEXT,
    evidence_json TEXT,
    result_path TEXT,
    error_code TEXT,
    FOREIGN KEY(request_id) REFERENCES verification_request(id),
    FOREIGN KEY(finding_id) REFERENCES finding(id)
);
"""

GLOBAL_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_project_map (
    chat_id TEXT PRIMARY KEY,
    project_slug TEXT NOT NULL,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS conversation_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT,
    thread_id TEXT,
    user_id TEXT,
    project_slug TEXT,
    last_intent TEXT,
    last_run_id TEXT,
    last_finding_id TEXT,
    last_result_ids_json TEXT,
    recent_entities_json TEXT,
    original_language TEXT,
    expires_at TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS agent_run (
    run_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    project_slug TEXT,
    chat_id TEXT,
    thread_id TEXT,
    user_id TEXT,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    result_path TEXT,
    summary_json TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversation_trace (
    trace_id TEXT PRIMARY KEY,
    message_id TEXT,
    chat_id_hash TEXT,
    thread_id TEXT,
    user_id_hash TEXT,
    project_slug TEXT,
    state TEXT,
    provider TEXT,
    model TEXT,
    planner_status TEXT,
    responder_status TEXT,
    reply_status TEXT,
    reaction_status TEXT,
    started_at TEXT,
    completed_at TEXT,
    latency_ms INTEGER,
    error_code TEXT
);

CREATE TABLE IF NOT EXISTS agent_invocation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT NOT NULL,
    phase TEXT NOT NULL,
    provider TEXT,
    model TEXT,
    latency_ms INTEGER,
    exit_code INTEGER,
    timed_out INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    prompt_hash TEXT,
    response_hash TEXT,
    parse_status TEXT,
    error_code TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS tool_invocation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT NOT NULL,
    task_id TEXT,
    tool_name TEXT NOT NULL,
    arguments_summary TEXT,
    status TEXT,
    result_count INTEGER,
    freshness TEXT,
    latency_ms INTEGER,
    error_code TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS reaction_session (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT NOT NULL,
    source_message_id TEXT NOT NULL,
    reaction_id TEXT,
    emoji_type TEXT,
    status TEXT,
    add_attempts INTEGER DEFAULT 0,
    remove_attempts INTEGER DEFAULT 0,
    added_at TEXT,
    removed_at TEXT,
    last_error TEXT
);

CREATE TABLE IF NOT EXISTS conversation_event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT NOT NULL,
    event TEXT NOT NULL,
    payload_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_session (
    session_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_session_id TEXT,
    chat_id TEXT NOT NULL,
    conversation_scope_id TEXT NOT NULL,
    user_id TEXT,
    project_slug TEXT,
    workspace_path TEXT NOT NULL,
    soul_version TEXT NOT NULL,
    protocol_version TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_active_at TEXT NOT NULL,
    expires_at TEXT,
    last_trace_id TEXT,
    last_request_id TEXT,
    failure_count INTEGER NOT NULL DEFAULT 0,
    checkpoint_json TEXT
);

CREATE TABLE IF NOT EXISTS conversation_job (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL UNIQUE,
    chat_id TEXT,
    thread_id TEXT,
    user_id TEXT,
    project_slug TEXT,
    state TEXT NOT NULL,
    intent TEXT,
    placeholder_message_id TEXT,
    started_at TEXT,
    updated_at TEXT,
    completed_at TEXT,
    error_code TEXT,
    error_detail TEXT
);

CREATE TABLE IF NOT EXISTS conversation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT,
    chat_id TEXT,
    thread_id TEXT,
    user_id TEXT,
    agent_id TEXT,
    original_text_hash TEXT,
    normalized_text TEXT,
    resolved_project TEXT,
    router_source TEXT,
    intent TEXT,
    confidence REAL,
    tool_calls TEXT,
    response_mode TEXT,
    validation_result TEXT,
    latency_ms INTEGER,
    error_code TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alert_delivery_global (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_slug TEXT NOT NULL,
    finding_id TEXT,
    event_key TEXT NOT NULL,
    delivered_at TEXT NOT NULL,
    UNIQUE(project_slug, event_key)
);

CREATE TABLE IF NOT EXISTS weekly_brief_delivery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_slug TEXT NOT NULL,
    week_key TEXT NOT NULL,
    delivered_at TEXT NOT NULL,
    payload_json TEXT,
    UNIQUE(project_slug, week_key)
);

CREATE TABLE IF NOT EXISTS project_summary_cache (
    project_slug TEXT PRIMARY KEY,
    summary_json TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS feishu_identity (
    identity_id TEXT PRIMARY KEY,
    identity_type TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    union_id TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);

-- Keep the origin of a Feishu identity separate from the identity itself.
-- The same person can speak in a group and in a private chat; Dashboard
-- authorization must only offer the latter as a one-to-one contact.
CREATE TABLE IF NOT EXISTS feishu_user_context (
    user_id TEXT NOT NULL,
    chat_id TEXT NOT NULL DEFAULT '',
    context_type TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, chat_id, context_type)
);
"""

_FEISHU_IDENTITY_COLUMNS = {
    "union_id": "TEXT NOT NULL DEFAULT ''",
}
_FINDING_V2_COLUMNS = {
    "occurrence_count": "INTEGER NOT NULL DEFAULT 0",
    "consecutive_seen_count": "INTEGER NOT NULL DEFAULT 0",
    "verification_status": "TEXT NOT NULL DEFAULT 'observed'",
    "remediation_status": "TEXT NOT NULL DEFAULT 'none'",
    "last_verified_at": "TEXT",
    "last_verification_run_id": "TEXT",
    "last_seen_scan_run_id": "TEXT",
    "resolution_basis": "TEXT",
    "resolved_by": "TEXT",
    "resolved_source_message_id": "TEXT",
    "resolved_trace_id": "TEXT",
    "owner_resolved_at": "TEXT",
    "remediation_reported_at": "TEXT",
    "remediation_commit_sha": "TEXT",
}

_FINDING_EVENT_V2_COLUMNS = {
    "source_message_id": "TEXT",
    "trace_id": "TEXT",
    "metadata_json": "TEXT",
    "idempotency_key": "TEXT",
}

_ALERT_V2_COLUMNS = {
    "status": "TEXT NOT NULL DEFAULT 'pending'",
    "attempt_count": "INTEGER NOT NULL DEFAULT 0",
    "last_attempt_at": "TEXT",
    "next_retry_at": "TEXT",
    "last_error": "TEXT",
}

_CONTEXT_V2_COLUMNS = {
    "pending_intent": "TEXT",
    "pending_tool": "TEXT",
    "pending_reference_type": "TEXT",
    "last_intent": "TEXT",
    "last_run_id": "TEXT",
    "last_result_ids_json": "TEXT",
    "recent_entities_json": "TEXT",
    "original_language": "TEXT",
    "expires_at": "TEXT",
    "created_at": "TEXT",
}

_AGENT_SESSION_COLUMNS = {
    "pending_json": "TEXT",
}


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _add_missing_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    existing = _table_columns(conn, table)
    for name, decl in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")


def _schema_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    if row is None:
        return 0
    try:
        return int(row[0] if not isinstance(row, sqlite3.Row) else row["value"])
    except (TypeError, ValueError):
        return 0


def _set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(
        """
        INSERT INTO meta(key, value) VALUES ('schema_version', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (str(version),),
    )


def migrate(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    _add_missing_columns(conn, "finding", _FINDING_V2_COLUMNS)
    _add_missing_columns(conn, "finding_event", _FINDING_EVENT_V2_COLUMNS)
    _add_missing_columns(conn, "alert_delivery", _ALERT_V2_COLUMNS)
    if "delivered_at" in _table_columns(conn, "alert_delivery"):
        conn.execute(
            """
            UPDATE alert_delivery
            SET status = 'sent', attempt_count = CASE WHEN COALESCE(attempt_count, 0) < 1 THEN 1 ELSE attempt_count END
            WHERE delivered_at IS NOT NULL
              AND COALESCE(last_error, '') = ''
              AND COALESCE(status, 'pending') IN ('', 'pending', 'sent')
            """
        )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_finding_event_idempotency
        ON finding_event(finding_id, event_type, idempotency_key)
        WHERE idempotency_key IS NOT NULL
        """
    )
    _set_schema_version(conn, SCHEMA_VERSION)
    conn.commit()


def migrate_global(conn: sqlite3.Connection) -> None:
    conn.executescript(GLOBAL_SCHEMA_SQL)
    _add_missing_columns(conn, "agent_session", _AGENT_SESSION_COLUMNS)
    if "conversation_context" in {
        str(row[0]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }:
        _add_missing_columns(conn, "conversation_context", _CONTEXT_V2_COLUMNS)
    if "feishu_identity" in {
        str(row[0]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }:
        _add_missing_columns(conn, "feishu_identity", _FEISHU_IDENTITY_COLUMNS)
    _set_schema_version(conn, SCHEMA_VERSION)
    conn.commit()


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    migrate(conn)
    return conn


def connect_global(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # Gateway workers share agents.sqlite3 across threads; allow cross-thread use.
    conn = sqlite3.connect(str(db_path), timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    migrate_global(conn)
    return conn
