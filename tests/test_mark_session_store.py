"""Tests for Mark SQLite persistence and event recovery."""

from __future__ import annotations

import stat
from pathlib import Path
from uuid import uuid4

from lumon.agents.mark.model import InboundMessage, MarkRunResult, Message
from lumon.agents.mark.session_store import MarkSessionStore


def _message(event_id: str = "evt-1") -> InboundMessage:
    return InboundMessage(
        event_id=event_id,
        message_id=event_id,
        chat_id="chat-1",
        chat_type="p2p",
        text="hello",
        sender_id="user-1",
        sender_type="user",
    )


def test_event_claim_is_idempotent_and_history_is_chronological(tmp_path: Path) -> None:
    store = MarkSessionStore(db_path=tmp_path / "state" / "mark.sqlite3")
    message = _message()
    workspace_id = uuid4()

    assert store.claim_event(message.event_id, message)
    assert not store.claim_event(message.event_id, message)
    store.record_message(
        Message(
            conversation_key=message.conversation_key,
            direction="inbound",
            message_id=message.message_id,
            text="hello",
            created_at="2026-01-01T00:00:00+00:00",
            workspace_id=workspace_id,
        )
    )
    store.record_message(
        Message(
            conversation_key=message.conversation_key,
            direction="inbound",
            message_id=message.message_id,
            text="duplicate after recovery",
            created_at="2026-01-01T00:00:02+00:00",
        )
    )
    store.record_message(
        Message(
            conversation_key=message.conversation_key,
            direction="outbound",
            text="world",
            created_at="2026-01-01T00:00:01+00:00",
        )
    )

    history = store.load_history(message.conversation_key)
    assert [item.text for item in history] == ["hello", "world"]
    assert stat.S_IMODE(store.path.stat().st_mode) == 0o600

    store.mark_event_status(message.event_id, "processing")
    pending = store.recover_pending()
    assert pending == (message,)


def test_record_result_closes_event_without_storing_provider_stderr(tmp_path: Path) -> None:
    store = MarkSessionStore(db_path=tmp_path / "mark.sqlite3")
    message = _message()
    store.claim_event(message.event_id, message)
    result = MarkRunResult(
        run_id="run-1",
        event_id=message.event_id,
        conversation_key=message.conversation_key,
        status="failed",
        started_at="start",
        ended_at="end",
        error_code="codex_execution_failed",
    )

    store.record_result(result)

    assert store.event_status(message.event_id) == "failed"
    database_text = store.path.read_bytes()
    assert b"stderr" not in database_text


def test_record_result_sanitizes_final_text(tmp_path: Path) -> None:
    store = MarkSessionStore(db_path=tmp_path / "mark.sqlite3")
    message = _message()
    store.claim_event(message.event_id, message)
    result = MarkRunResult(
        run_id="run-1",
        event_id=message.event_id,
        conversation_key=message.conversation_key,
        status="succeeded",
        started_at="start",
        ended_at="end",
        final_text="app_secret=secret-value",
    )

    store.record_result(result)

    assert b"secret-value" not in store.path.read_bytes()
