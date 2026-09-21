"""Tests for Agent SQLite persistence and event recovery."""

from __future__ import annotations

import sqlite3
import stat
from pathlib import Path
from uuid import uuid4

from lumon.agents.agent.model import AgentRunResult, InboundMessage, Message
from lumon.agents.agent.session_store import AgentSessionStore


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
    store = AgentSessionStore(db_path=tmp_path / "state" / "agent.sqlite3")
    message = _message()
    workspace_id = uuid4()

    assert store.claim_event(message.event_id, message)
    assert not store.claim_event(message.event_id, message)
    session_id = store.get_or_create_session(message).session_id
    store.record_message(
        Message(
            conversation_key=message.conversation_key,
            direction="inbound",
            message_id=message.message_id,
            text="hello",
            created_at="2026-01-01T00:00:00+00:00",
            workspace_id=workspace_id,
            session_id=session_id,
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

    history = store.load_history(session_id, conversation_key=message.conversation_key)
    assert [item.text for item in history] == ["hello", "world"]
    assert stat.S_IMODE(store.path.stat().st_mode) == 0o600

    store.mark_event_status(message.event_id, "processing")
    pending = store.recover_pending()
    assert pending == (message,)


def test_deferred_cards_are_merged_into_a_follow_up(tmp_path: Path) -> None:
    store = AgentSessionStore(db_path=tmp_path / "agent.sqlite3")
    card = InboundMessage(
        event_id="card-event",
        message_id="card-message",
        chat_id="chat-1",
        chat_type="p2p",
        text="Forwarded email preview",
        sender_id="user-1",
        sender_type="user",
        card_only=True,
    )
    follow_up = _message("follow-up-event")

    assert store.defer_card(card)
    assert store.event_status(card.event_id) == "deferred"
    assert store.deferred_cards(card.conversation_key) == (card,)
    assert store.claim_event(follow_up.event_id, follow_up)
    merged_text = "<feishu-card-context>\nForwarded email preview\n</feishu-card-context>\n\nhello"
    store.merge_deferred_cards(
        event_id=follow_up.event_id,
        conversation_key=follow_up.conversation_key,
        merged_text=merged_text,
    )

    assert store.deferred_cards(card.conversation_key) == ()
    assert store.event_status(card.event_id) == "merged"
    with sqlite3.connect(store.path) as connection:
        row = connection.execute(
            "SELECT text FROM events WHERE event_id = ?",
            (follow_up.event_id,),
        ).fetchone()
    assert row == (merged_text,)


def test_sessions_are_stable_for_direct_chats_and_group_threads(tmp_path: Path) -> None:
    store = AgentSessionStore(db_path=tmp_path / "agent.sqlite3")
    direct = _message()
    direct_reply = InboundMessage(
        event_id="evt-2",
        message_id="evt-2",
        chat_id="chat-1",
        chat_type="p2p",
        text="follow-up",
        sender_id="user-1",
        sender_type="user",
        thread_id="thread-that-must-not-split-a-dm",
    )
    group_first = InboundMessage(
        event_id="group-1",
        message_id="group-1",
        chat_id="group-1",
        chat_type="group",
        text="@Agent first",
        sender_id="user-1",
        sender_type="user",
        mentioned_agent=True,
        thread_id="thread-a",
        root_id="root-message-1",
    )
    group_reply = InboundMessage(
        event_id="group-2",
        message_id="group-2",
        chat_id="group-1",
        chat_type="group",
        text="@Agent follow-up",
        sender_id="user-1",
        sender_type="user",
        mentioned_agent=True,
        thread_id="thread-a",
        root_id="root-message-2",
    )
    other_group_thread = InboundMessage(
        event_id="group-3",
        message_id="group-3",
        chat_id="group-1",
        chat_type="group",
        text="@Agent another",
        sender_id="user-1",
        sender_type="user",
        mentioned_agent=True,
        thread_id="thread-b",
    )

    assert (
        store.get_or_create_session(direct).session_id
        == store.get_or_create_session(direct_reply).session_id
    )
    assert (
        store.get_or_create_session(group_first).session_id
        == store.get_or_create_session(group_reply).session_id
    )
    assert (
        store.get_or_create_session(group_first).session_id
        != store.get_or_create_session(other_group_thread).session_id
    )


def test_provider_session_binding_is_durable_and_clearable(tmp_path: Path) -> None:
    store = AgentSessionStore(db_path=tmp_path / "agent.sqlite3")
    session_id = store.get_or_create_session(_message()).session_id

    store.bind_agent_session(session_id, "codex-thread-1")
    session = store.get_session(session_id)
    assert session is not None
    assert session.agent_session_id == "codex-thread-1"

    store.clear_agent_session(session_id)
    session = store.get_session(session_id)
    assert session is not None
    assert session.agent_session_id is None


def test_full_prompt_is_stored_with_the_run_before_execution(tmp_path: Path) -> None:
    store = AgentSessionStore(db_path=tmp_path / "agent.sqlite3")
    message = _message()
    assert store.claim_event(message.event_id, message)
    session_id = store.get_or_create_session(message).session_id
    workspace_id = uuid4()
    prompt = "<agent-soul>private context</agent-soul>\n<user-message>hello</user-message>"

    store.record_run_started(
        run_id="run-prompt",
        event_id=message.event_id,
        session_id=session_id,
        conversation_key=message.conversation_key,
        workspace_id=workspace_id,
        agent_provider="test-agent",
        prompt_text=prompt,
        started_at="start",
    )

    with sqlite3.connect(store.path) as connection:
        row = connection.execute(
            "SELECT session_id, status, prompt_text FROM runs WHERE run_id = ?",
            ("run-prompt",),
        ).fetchone()
    assert row == (session_id, "running", prompt)


def test_recalled_event_is_cancelled_and_removed_from_future_history(tmp_path: Path) -> None:
    store = AgentSessionStore(db_path=tmp_path / "agent.sqlite3")
    message = _message()
    assert store.claim_event(message.event_id, message)
    session_id = store.get_or_create_session(message).session_id
    store.record_message(
        Message(
            conversation_key=message.conversation_key,
            direction="inbound",
            message_id=message.message_id,
            text=message.text,
            created_at="2026-01-01T00:00:00+00:00",
            session_id=session_id,
        )
    )

    assert store.request_message_cancellation(message.message_id) == message.event_id
    store.mark_event_cancelled(message.event_id)

    assert store.event_status(message.event_id) == "cancelled"
    assert store.load_history(session_id, conversation_key=message.conversation_key) == ()
    assert store.request_message_cancellation(message.message_id) == message.event_id


def test_existing_legacy_database_is_used_before_new_indexes_are_created(
    tmp_path: Path,
) -> None:
    database = tmp_path / "mark.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE events (
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
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_key TEXT NOT NULL,
                direction TEXT NOT NULL,
                message_id TEXT,
                workspace_id TEXT,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE runs (
                run_id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                conversation_key TEXT NOT NULL,
                workspace_id TEXT,
                agent_provider TEXT,
                status TEXT NOT NULL,
                error_code TEXT,
                started_at TEXT NOT NULL,
                ended_at TEXT NOT NULL,
                final_text TEXT
            );
            """
        )

    store = AgentSessionStore(state_root=tmp_path)

    with sqlite3.connect(database) as connection:
        session_columns = {row[1] for row in connection.execute("PRAGMA table_info(sessions)")}
        event_columns = {row[1] for row in connection.execute("PRAGMA table_info(events)")}
        message_columns = {row[1] for row in connection.execute("PRAGMA table_info(messages)")}
        run_columns = {row[1] for row in connection.execute("PRAGMA table_info(runs)")}

    assert {"session_id", "session_key"} <= session_columns
    assert "session_id" in event_columns
    assert "session_id" in message_columns
    assert {"session_id", "prompt_text", "failure_diagnostic", "flow_id"} <= run_columns
    assert "recalled" in message_columns
    assert store.path == database.resolve()


def test_record_result_closes_event_without_storing_provider_stderr(tmp_path: Path) -> None:
    store = AgentSessionStore(db_path=tmp_path / "agent.sqlite3")
    message = _message()
    store.claim_event(message.event_id, message)
    result = AgentRunResult(
        run_id="run-1",
        event_id=message.event_id,
        conversation_key=message.conversation_key,
        status="failed",
        started_at="start",
        ended_at="end",
        agent_provider="codex",
        error_code="execution_failed",
        failure_diagnostic="run_agent:RuntimeError:runner.py:run:42",
        flow_id="test-case-generation",
    )

    store.record_result(result)

    assert store.event_status(message.event_id) == "failed"
    with sqlite3.connect(store.path) as connection:
        diagnostic = connection.execute(
            "SELECT failure_diagnostic, flow_id FROM runs WHERE run_id = ?", ("run-1",)
        ).fetchone()
    assert diagnostic == ("run_agent:RuntimeError:runner.py:run:42", "test-case-generation")
    database_text = store.path.read_bytes()
    assert b"stderr" not in database_text


def test_record_result_sanitizes_final_text(tmp_path: Path) -> None:
    store = AgentSessionStore(db_path=tmp_path / "agent.sqlite3")
    message = _message()
    store.claim_event(message.event_id, message)
    result = AgentRunResult(
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
