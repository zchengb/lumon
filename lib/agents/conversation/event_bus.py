"""Durable event bus for Thread-native Agent collaboration."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from typing import Any

from agents.conversation.events import ConversationEvent
from agents.conversation.thread_store import ThreadTranscriptStore


EventSubscriber = Callable[[ConversationEvent], Any]


class EventBus:
    """Persist, deduplicate, and fan out conversation events.

    Persistence is the source of truth. Subscribers are best-effort observers
    used by transports and dashboards; a failing subscriber never rolls back a
    recorded event.
    """

    def __init__(self, store: ThreadTranscriptStore | None = None) -> None:
        self.store = store or ThreadTranscriptStore()
        self._owned = store is None
        self._lock = threading.RLock()
        self._subscribers: dict[int, tuple[EventSubscriber, frozenset[str] | None]] = {}
        self._next_subscription = 0

    def close(self) -> None:
        if self._owned:
            self.store.close()

    def subscribe(
        self,
        callback: EventSubscriber,
        *,
        event_types: Iterable[str] | None = None,
    ) -> Callable[[], None]:
        types = frozenset(str(item or "").strip() for item in event_types or () if str(item or "").strip())
        with self._lock:
            self._next_subscription += 1
            token = self._next_subscription
            self._subscribers[token] = (callback, types or None)

        def unsubscribe() -> None:
            with self._lock:
                self._subscribers.pop(token, None)

        return unsubscribe

    def publish(self, event: ConversationEvent) -> ConversationEvent | None:
        with self._lock:
            stored = self.store.record_event(event)
            if stored is None:
                return None
            subscribers = list(self._subscribers.values())
        for callback, event_types in subscribers:
            if event_types is not None and stored.type not in event_types:
                continue
            try:
                callback(stored)
            except Exception:
                continue
        return stored

    def has_dedupe(self, dedupe_key: str) -> bool:
        """Check an output idempotency key without publishing or notifying."""

        return self.store.get_event_by_dedupe(dedupe_key) is not None

    def publish_many(self, events: Iterable[ConversationEvent]) -> list[ConversationEvent]:
        published: list[ConversationEvent] = []
        for event in events:
            item = self.publish(event)
            if item is not None:
                published.append(item)
        return published

    def replay(
        self,
        *,
        chat_id: str = "",
        thread_id: str = "",
        after_event_id: str = "",
        limit: int = 200,
        visibility: str = "",
    ) -> list[ConversationEvent]:
        return self.store.list_events(
            chat_id=chat_id,
            thread_id=thread_id,
            after_event_id=after_event_id,
            limit=limit,
            visibility=visibility,
        )
