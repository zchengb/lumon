"""Read-only execution summaries must not mutate or mix Agent conversations."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from lumon.agents.agent.model import AgentRunResult, InboundMessage, Message
from lumon.agents.agent.session_store import AgentSessionStore
from lumon.dashboard.chat_history import AgentChatHistory
from lumon.errors import AgentRuntimeError


def _turn(
    store: AgentSessionStore,
    workspace_id: UUID,
    *,
    chat_id: str,
    sender_id: str = "user-one",
    thread_id: str | None = None,
    minute: int = 0,
    trace_url: str | None = None,
) -> str:
    message_id = str(uuid4())
    inbound = InboundMessage(
        event_id=message_id,
        message_id=message_id,
        chat_id=chat_id,
        chat_type="group" if thread_id else "p2p",
        thread_id=thread_id,
        text=f"Review turn {minute}. password=example-secret",
        sender_id=sender_id,
        sender_type="user",
        mentioned_agent=True,
    )
    session = store.get_or_create_session(inbound)
    assert store.claim_event(inbound.event_id, inbound)
    started = datetime.fromisoformat(f"2026-09-30T04:{minute:02d}:00+00:00")
    store.record_message(
        Message(
            conversation_key=inbound.conversation_key,
            direction="inbound",
            text=inbound.text,
            created_at=started.isoformat(),
            message_id=message_id,
            session_id=session.session_id,
        )
    )
    store.attach_workspace(inbound.event_id, workspace_id)
    run_id = str(uuid4())
    store.record_result(
        AgentRunResult(
            run_id=run_id,
            event_id=inbound.event_id,
            conversation_key=inbound.conversation_key,
            status="succeeded",
            started_at=started.isoformat(),
            ended_at=(started + timedelta(seconds=733)).isoformat(),
            final_text=f"Turn {minute} complete. token=output-secret",
            workspace_id=workspace_id,
            session_id=session.session_id,
            prompt_text="PRIVATE INITIAL PROMPT",
            failure_diagnostic="PRIVATE PROVIDER DIAGNOSTIC",
            trace_url=trace_url,
        )
    )
    return run_id


def test_history_pairs_each_execution_and_scopes_workspaces_users_and_threads(
    tmp_path: Path,
) -> None:
    store = AgentSessionStore(tmp_path)
    workspace = uuid4()
    other_workspace = uuid4()
    direct = _turn(store, workspace, chat_id="direct-one")
    group = _turn(store, workspace, chat_id="group-one", thread_id="thread-one", minute=1)
    next_turn = _turn(
        store,
        workspace,
        chat_id="group-one",
        thread_id="thread-one",
        sender_id="user-two",
        minute=2,
    )
    other_thread = _turn(store, workspace, chat_id="group-one", thread_id="thread-two", minute=3)
    _turn(store, other_workspace, chat_id="other-workspace", sender_id="private-user")
    # Moving a session must not reassign earlier executions to the latest Workspace.
    _turn(store, other_workspace, chat_id="direct-one", sender_id="moved-user", minute=4)
    history = AgentChatHistory(tmp_path)
    snapshot = store.path.read_bytes()

    page = history.conversations(workspace)
    assert page.total == 4
    assert [item.run_id for item in page.items] == [other_thread, next_turn, group, direct]
    for item, minute in zip(page.items, [3, 2, 1, 0], strict=True):
        assert item.input_preview.startswith(f"Review turn {minute}.")
        assert item.output_preview.startswith(f"Turn {minute} complete.")
        assert item.duration_seconds == 733
        detail = history.interaction(workspace, item.run_id)
        assert detail is not None
        assert detail.input_text == f"Review turn {minute}. password=[REDACTED]"
        assert detail.output_text == f"Turn {minute} complete. token=[REDACTED]"
        assert "PRIVATE" not in repr(detail)
    assert history.conversations(workspace, kind="direct").total == 1
    assert history.conversations(workspace, kind="group").total == 3
    assert history.conversations(workspace, search="USER-TWO").items == (page.items[1],)
    assert history.conversations(workspace, search="thread-two").total == 1
    assert history.conversations(workspace, search="private-user").total == 0
    assert history.interaction(other_workspace, direct) is None
    assert history.interaction(workspace, "' OR 1=1 --") is None
    assert history.conversations(workspace, limit=1, offset=1).items == (page.items[1],)
    assert "example-secret" not in repr(page)
    assert "output-secret" not in repr(page)
    assert "PRIVATE" not in repr(page)
    assert store.path.read_bytes() == snapshot


def test_legacy_file_and_null_session_links_remain_readable(tmp_path: Path) -> None:
    store = AgentSessionStore(db_path=tmp_path / "mark.sqlite3")
    workspace = uuid4()
    _turn(store, workspace, chat_id="old-direct")
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE messages SET session_id = NULL")
        connection.execute("UPDATE events SET session_id = NULL")
        connection.execute("UPDATE runs SET session_id = NULL")
        connection.execute("ALTER TABLE runs DROP COLUMN trace_url")
    snapshot = store.path.read_bytes()
    assert AgentChatHistory(tmp_path).conversations(workspace, search="user-one").total == 1
    assert AgentChatHistory(tmp_path).conversations(workspace).items[0].trace_url is None
    assert store.path.read_bytes() == snapshot
    assert not (tmp_path / "agent.sqlite3").exists()


def test_trace_links_belong_to_each_run_and_do_not_require_current_configuration(
    tmp_path: Path,
) -> None:
    store = AgentSessionStore(tmp_path)
    workspace = uuid4()
    other_workspace = uuid4()
    old_url = "https://jp.cloud.langfuse.com/project/old-project/traces/" + "a" * 32
    new_url = "http://localhost:3000/langfuse/project/new-project/traces/" + "b" * 32
    first = _turn(store, workspace, chat_id="same-chat", trace_url=old_url)
    second = _turn(store, workspace, chat_id="same-chat", minute=1, trace_url=new_url)
    _turn(store, other_workspace, chat_id="other-chat", trace_url=old_url)
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE runs SET status = 'running' WHERE run_id = ?", (second,))
        connection.execute("UPDATE runs SET status = 'timed_out' WHERE run_id = ?", (first,))
    snapshot = store.path.read_bytes()
    page = AgentChatHistory(tmp_path).conversations(workspace)
    assert [(item.run_id, item.trace_url) for item in page.items] == [
        (second, new_url),
        (first, old_url),
    ]
    assert store.path.read_bytes() == snapshot


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "https://user:private-secret@cloud.langfuse.com/project/test/traces/" + "a" * 32,
        "https://cloud.langfuse.com/project/test/traces/" + "a" * 32 + "?token=private-secret",
        "https://cloud.langfuse.com/project/test/traces/" + "a" * 32 + "#private-secret",
        "https://cloud.langfuse.com/project/test/traces/invalid-id",
        "https://[invalid-host/project/test/traces/" + "a" * 32,
        "https://cloud.langfuse.com\n/project/test/traces/" + "a" * 32,
        "https://cloud.langfuse.com:bad-port/project/test/traces/" + "a" * 32,
    ],
)
def test_untrusted_trace_links_are_omitted_at_write_and_read_boundaries(
    tmp_path: Path, url: str
) -> None:
    store = AgentSessionStore(tmp_path)
    workspace = uuid4()
    _turn(store, workspace, chat_id="same-chat", trace_url=url)
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("SELECT trace_url FROM runs").fetchone() == (None,)
        # An externally edited local database must not bypass API validation.
        connection.execute("UPDATE runs SET trace_url = ?", (url,))
    assert AgentChatHistory(tmp_path).conversations(workspace).items[0].trace_url is None


def test_recalled_messages_and_cancelled_events_are_hidden(tmp_path: Path) -> None:
    store = AgentSessionStore(tmp_path)
    workspace = uuid4()
    run_id = _turn(store, workspace, chat_id="direct-one")
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE messages SET recalled = 1")
    assert AgentChatHistory(tmp_path).conversations(workspace).total == 0
    assert AgentChatHistory(tmp_path).interaction(workspace, run_id) is None
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE messages SET recalled = 0")
        connection.execute("UPDATE events SET status = 'cancelled'")
    assert AgentChatHistory(tmp_path).conversations(workspace).total == 0
    assert AgentChatHistory(tmp_path).interaction(workspace, run_id) is None


@pytest.mark.parametrize(
    ("status", "started", "ended", "expected"),
    [
        ("running", "2026-09-30T04:00:00Z", "2026-09-30T04:00:00Z", None),
        ("failed", "2026-09-30T04:00:00Z", "2026-09-30T04:00:42Z", 42),
        ("timed_out", "2026-09-30T04:00:00Z", "2026-09-30T04:30:00Z", 1800),
        ("interrupted", "invalid", "invalid", None),
        ("succeeded", "2026-09-30T04:00:00Z", "2026-09-30T03:59:00Z", None),
        ("succeeded", "2026-09-30T04:00:00Z", "2026-09-30T04:00:00Z", 0),
        ("failed", "2026-09-30T04:00:00", "2026-09-30T04:00:00Z", None),
    ],
)
def test_duration_and_bounded_previews(
    tmp_path: Path, status: str, started: str, ended: str, expected: int | None
) -> None:
    store = AgentSessionStore(tmp_path)
    workspace = uuid4()
    _turn(store, workspace, chat_id="direct-one")
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            "UPDATE runs SET status = ?, started_at = ?, ended_at = ?, final_text = ?",
            (status, started, ended, "Output " * 100),
        )
        connection.execute("UPDATE events SET text = ?", ("Input\n" * 100,))
    item = AgentChatHistory(tmp_path).conversations(workspace).items[0]
    assert item.status == status
    assert item.duration_seconds == expected
    assert len(item.input_preview) == len(item.output_preview) == 240
    assert item.input_preview.endswith("…") and "\n" not in item.input_preview


def test_missing_and_incomplete_databases_are_not_created_or_upgraded(tmp_path: Path) -> None:
    root = tmp_path / "missing"
    assert AgentChatHistory(root).conversations(uuid4()).total == 0
    assert AgentChatHistory(root).interaction(uuid4(), "missing-run") is None
    assert not root.exists()
    with sqlite3.connect(tmp_path / "agent.sqlite3") as connection:
        connection.execute("CREATE TABLE messages (text TEXT)")
    snapshot = (tmp_path / "agent.sqlite3").read_bytes()
    assert AgentChatHistory(tmp_path).conversations(uuid4()).total == 0
    assert AgentChatHistory(tmp_path).interaction(uuid4(), "missing-run") is None
    assert (tmp_path / "agent.sqlite3").read_bytes() == snapshot


def test_output_preview_preserves_markdown_structure_and_redaction(tmp_path: Path) -> None:
    store = AgentSessionStore(tmp_path)
    workspace = uuid4()
    _turn(store, workspace, chat_id="direct-one")
    markdown = "**Result**\n\n1. `Ready`\n2. token=private-value\n"
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE runs SET final_text = ?", (markdown,))
    item = AgentChatHistory(tmp_path).conversations(workspace).items[0]
    assert item.output_preview == "**Result**\n\n1. `Ready`\n2. token=[REDACTED]"
    assert item.chat_name is None and item.sender_name is None


def test_message_details_preserve_full_user_text_and_markdown_without_prompts(
    tmp_path: Path,
) -> None:
    store = AgentSessionStore(tmp_path)
    workspace = uuid4()
    run_id = _turn(store, workspace, chat_id="direct-one")
    input_text = "Question\n" * 100 + "password=private-secret\nEND OF INPUT"
    output_text = "**Result**\n\n" + "1. `Ready`\n" * 100 + "token=private-secret\nEND OF OUTPUT"
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE events SET text = ?", (input_text,))
        connection.execute("UPDATE runs SET final_text = ?", (output_text,))
    snapshot = store.path.read_bytes()
    history = AgentChatHistory(tmp_path)
    assert len(history.conversations(workspace).items[0].input_preview) == 240
    detail = history.interaction(workspace, run_id)
    assert detail is not None and detail.run_id == run_id
    assert detail.input_text == input_text.replace("private-secret", "[REDACTED]")
    assert detail.output_text == output_text.replace("private-secret", "[REDACTED]")
    assert "PRIVATE" not in repr(detail) and "private-secret" not in repr(detail)
    assert store.path.read_bytes() == snapshot


def test_database_errors_do_not_disclose_paths_or_content(tmp_path: Path) -> None:
    database = tmp_path / "agent.sqlite3"
    database.write_text("not sqlite: password=private-credential")
    with pytest.raises(AgentRuntimeError, match="^Cannot read local Agent chat history\\.$"):
        AgentChatHistory(tmp_path).conversations(uuid4())
