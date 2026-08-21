"""Agent Session Host: serialized provider sessions inside a shared Thread."""

from __future__ import annotations

import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from agents.conversation.event_bus import EventBus
from agents.conversation.events import ConversationEvent
from agents.runtime.session_store import SessionStore


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class SessionState:
    session_id: str
    agent_id: str
    thread_id: str = ""
    chat_id: str = ""
    conversation_scope_id: str = ""
    state: str = "idle"
    provider_session_id: str = ""
    queued_events: int = 0
    updated_at: str = field(default_factory=_now)

    @property
    def waiting_for_human(self) -> bool:
        return self.state == "waiting_human"

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "thread_id": self.thread_id,
            "chat_id": self.chat_id,
            "conversation_scope_id": self.conversation_scope_id,
            "state": self.state,
            "provider_session_id": self.provider_session_id,
            "queued_events": self.queued_events,
            "updated_at": self.updated_at,
            "waiting_for_human": self.waiting_for_human,
        }


Runner = Callable[[Mapping[str, Any], SessionState], Any]


class AgentSessionHost:
    """Own lifecycle and ordering for one Agent's private Harness session.

    The host serializes events per session, not per Feishu Thread.  Mark can
    therefore run while Dylan is waiting, while each provider session still
    has a single writer and ordered inputs.
    """

    def __init__(
        self,
        *,
        session_store: SessionStore | None = None,
        event_bus: EventBus | None = None,
        executor: ThreadPoolExecutor | None = None,
    ) -> None:
        self.session_store = session_store or SessionStore()
        self._owned_store = session_store is None
        self.event_bus = event_bus or EventBus()
        self._owned_bus = event_bus is None
        self.executor = executor or ThreadPoolExecutor(max_workers=8, thread_name_prefix="lumon-session")
        self._owned_executor = executor is None
        self._guard = threading.RLock()
        self._states: dict[str, SessionState] = {}
        self._locks: dict[str, threading.RLock] = {}
        self._runners: dict[str, Runner] = {}
        self._futures: dict[str, Future[Any]] = {}

    def close(self) -> None:
        if self._owned_executor:
            self.executor.shutdown(wait=False, cancel_futures=False)
        if self._owned_bus:
            self.event_bus.close()
        if self._owned_store:
            self.session_store.close()

    def register(
        self,
        session: Mapping[str, Any] | None = None,
        *,
        session_id: str = "",
        agent_id: str = "",
        thread_id: str = "",
        chat_id: str = "",
        conversation_scope_id: str = "",
        provider_session_id: str = "",
        runner: Runner | None = None,
    ) -> SessionState:
        data = dict(session or {})
        sid = str(session_id or data.get("session_id") or "").strip()
        if not sid:
            raise ValueError("session_id is required")
        with self._guard:
            state = self._states.get(sid)
            if state is None:
                state = SessionState(
                    session_id=sid,
                    agent_id=str(agent_id or data.get("agent_id") or "").strip().lower(),
                    thread_id=str(thread_id or data.get("thread_id") or "").strip(),
                    chat_id=str(chat_id or data.get("chat_id") or "").strip(),
                    conversation_scope_id=str(conversation_scope_id or data.get("conversation_scope_id") or "").strip(),
                    provider_session_id=str(provider_session_id or data.get("provider_session_id") or "").strip(),
                    state=str(data.get("runtime_state") or data.get("state") or data.get("status") or "idle").strip().lower(),
                )
                if state.state in {"active", "running"}:
                    state.state = "idle"
                self._states[sid] = state
                self._locks[sid] = threading.RLock()
            if runner is not None:
                self._runners[sid] = runner
            return state

    def state(self, session_id: str) -> SessionState | None:
        with self._guard:
            item = self._states.get(str(session_id or "").strip())
            if item is None:
                return None
            return replace(item)

    def _state_for(self, session_id: str) -> SessionState:
        value = self.state(session_id)
        if value is None:
            raise KeyError(f"unknown session: {session_id}")
        return value

    def _set_state(self, session_id: str, value: str, *, provider_session_id: str = "") -> SessionState:
        with self._guard:
            state = self._states[str(session_id).strip()]
            state.state = str(value or "idle").strip().lower()
            state.updated_at = _now()
            if provider_session_id:
                state.provider_session_id = str(provider_session_id).strip()
            try:
                self.session_store.update(session_id, status=state.state)
            except Exception:
                pass
            return state

    def _publish_lifecycle(self, state: SessionState, event_type: str, *, payload: Mapping[str, Any] | None = None) -> None:
        thread_id = state.thread_id or state.conversation_scope_id
        if not thread_id:
            return
        self.event_bus.publish(
            ConversationEvent.create(
                thread_id=thread_id,
                chat_id=state.chat_id,
                agent_id=state.agent_id,
                type=event_type,
                visibility="internal",
                session_id=state.session_id,
                payload=dict(payload or {}),
                dedupe_key=f"{state.session_id}:{event_type}:{state.updated_at}",
            )
        )

    def start(
        self,
        session_id: str,
        *,
        event: Mapping[str, Any] | None = None,
        runner: Runner | None = None,
        asynchronous: bool = False,
    ) -> Any:
        sid = str(session_id or "").strip()
        state = self._state_for(sid)
        if runner is not None:
            self._runners[sid] = runner
        self._set_state(sid, "running")
        self._publish_lifecycle(state, "session.started", payload={"asynchronous": asynchronous})
        if event is None:
            return state.to_dict()
        return self.enqueue(sid, event, runner=runner, asynchronous=asynchronous)

    def enqueue(
        self,
        session_id: str,
        event: Mapping[str, Any],
        *,
        runner: Runner | None = None,
        asynchronous: bool = False,
    ) -> Any:
        sid = str(session_id or "").strip()
        self._state_for(sid)
        if runner is not None:
            self._runners[sid] = runner
        callback = runner or self._runners.get(sid)
        if callback is None:
            raise ValueError("a session runner is required")
        with self._guard:
            state = self._states[sid]
            state.queued_events += 1
            state.updated_at = _now()
        if asynchronous:
            future = self.executor.submit(self._run_one, sid, dict(event), callback)
            self._futures[sid] = future
            return future
        return self._run_one(sid, dict(event), callback)

    def _run_one(self, session_id: str, event: dict[str, Any], runner: Runner) -> Any:
        lock = self._locks[session_id]
        with lock:
            with self._guard:
                state = self._states[session_id]
                state.queued_events = max(0, state.queued_events - 1)
                state.state = "running"
                state.updated_at = _now()
            try:
                result = runner(event, state)
            except Exception as exc:
                self._set_state(session_id, "failed")
                self._publish_lifecycle(state, "session.completed", payload={"status": "failed", "error": str(exc)[:300]})
                raise
            payload = result if isinstance(result, Mapping) else {}
            status = str(payload.get("session_state") or payload.get("state") or payload.get("status") or "completed").strip().lower()
            if payload.get("waiting_for_human") or status in {"waiting", "waiting_human", "question"}:
                self._set_state(session_id, "waiting_human", provider_session_id=str(payload.get("provider_session_id") or ""))
                self._publish_lifecycle(state, "session.waiting", payload={"question": str(payload.get("question") or "")[:1000]})
            elif status in {"paused", "pause"}:
                self._set_state(session_id, "paused")
            elif status in {"failed", "error"}:
                self._set_state(session_id, "failed")
                self._publish_lifecycle(state, "session.completed", payload={"status": "failed"})
            elif status in {"stopped", "stop"}:
                self._set_state(session_id, "stopped")
            else:
                self._set_state(session_id, "completed", provider_session_id=str(payload.get("provider_session_id") or ""))
                self._publish_lifecycle(state, "session.completed", payload={"status": "completed"})
            return result

    def resume(
        self,
        session_id: str,
        event: Mapping[str, Any],
        *,
        runner: Runner | None = None,
        asynchronous: bool = False,
    ) -> Any:
        state = self._state_for(session_id)
        self._set_state(session_id, "running")
        self._publish_lifecycle(state, "session.resumed")
        return self.enqueue(session_id, event, runner=runner, asynchronous=asynchronous)

    def pause(self, session_id: str, *, waiting_for_human: bool = False) -> SessionState:
        state = self._set_state(session_id, "waiting_human" if waiting_for_human else "paused")
        self._publish_lifecycle(state, "session.waiting" if waiting_for_human else "session.paused")
        return state

    def stop(self, session_id: str) -> SessionState:
        state = self._set_state(session_id, "stopped")
        future = self._futures.get(str(session_id or "").strip())
        if future is not None:
            future.cancel()
        self._publish_lifecycle(state, "session.completed", payload={"status": "stopped"})
        return state

    def finish(self, session_id: str, *, status: str = "completed", keep_session: bool = True) -> SessionState:
        """Close one turn while optionally keeping the provider session resumable."""

        sid = str(session_id or "").strip()
        state = self._state_for(sid)
        with self._guard:
            state.state = str(status or "completed").strip().lower()
            state.updated_at = _now()
            persisted = "active" if keep_session and state.state == "completed" else state.state
            try:
                self.session_store.update(sid, status=persisted)
            except Exception:
                pass
        self._publish_lifecycle(state, "session.completed", payload={"status": state.state})
        return state
