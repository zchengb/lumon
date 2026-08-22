"""User-visible conversation output for native Harness events."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from agents.conversation.config import ThreadNativeConfig, thread_native_config
from agents.conversation.event_bus import EventBus
from agents.conversation.events import ConversationEvent
from agents.conversation.quality import ConversationQualityMetrics
from agents.compat.legacy_envelopes import sanitize_public_text
from feishu.messenger import FeishuMessenger, extract_message_id, should_reply_in_thread


@dataclass(frozen=True)
class OutputReceipt:
    status: str
    event: ConversationEvent | None = None
    response: dict[str, Any] | None = None
    message_id: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "event": self.event.to_dict() if self.event else None,
            "response": self.response,
            "message_id": self.message_id,
            "error": self.error,
        }


class ConversationOutput:
    """Small, deep interface for Agent-visible messages and artifacts."""

    def __init__(
        self,
        *,
        agent_id: str,
        meta: Mapping[str, Any],
        common: Mapping[str, Any] | None = None,
        messenger: FeishuMessenger | None = None,
        event_bus: EventBus | None = None,
        config: ThreadNativeConfig | None = None,
    ) -> None:
        self.agent_id = str(agent_id or "").strip().lower()
        self.meta = dict(meta or {})
        self.common = dict(common or {})
        self.messenger = messenger or FeishuMessenger(self.agent_id)
        self.event_bus = event_bus or EventBus()
        self._owned_bus = event_bus is None
        self.config = config or thread_native_config(self.common, self.meta)
        self._last_public_event: dict[str, float] = {}
        self.quality = ConversationQualityMetrics(default_language=self.config.default_language)
        for key in ("_human_interrupt_count", "human_interrupt_count"):
            try:
                self.quality.record_human_interrupt(int(self.meta.get(key) or 0))
                break
            except (TypeError, ValueError):
                continue

    def close(self) -> None:
        if self._owned_bus:
            self.event_bus.close()

    @property
    def thread_id(self) -> str:
        return str(
            self.meta.get("thread_id")
            or self.meta.get("root_id")
            or self.meta.get("parent_id")
            or self.meta.get("message_id")
            or ""
        ).strip()

    def _dedupe_key(self, event_type: str, text: str, payload: Mapping[str, Any]) -> str:
        try:
            payload_text = json.dumps(dict(payload), ensure_ascii=False, sort_keys=True, default=str)
        except (TypeError, ValueError):
            payload_text = str(dict(payload))
        digest = hashlib.sha256(
            f"{self.agent_id}\0{self.thread_id}\0{event_type}\0{text}\0{payload_text}".encode("utf-8")
        ).hexdigest()[:24]
        return f"output:{digest}"

    def _event(
        self,
        event_type: str,
        text: str,
        payload: Mapping[str, Any] | None,
        *,
        visibility: str = "public",
    ) -> ConversationEvent:
        values = dict(payload or {})
        return ConversationEvent.create(
            thread_id=self.thread_id,
            chat_id=str(self.meta.get("chat_id") or ""),
            agent_id=self.agent_id,
            type=event_type,
            text=text,
            payload=values,
            visibility=visibility,
            source_message_id=str(self.meta.get("message_id") or ""),
            session_id=str(self.meta.get("session_id") or ""),
            dedupe_key=self._dedupe_key(event_type, text, values),
        )

    def _send_text(self, text: str, *, allow_pdf: bool = False) -> dict[str, Any] | None:
        message_id = str(self.meta.get("message_id") or "").strip()
        reply_in_thread = should_reply_in_thread(self.meta)
        if message_id:
            return self.messenger.reply_agent_text(
                message_id,
                text,
                reply_in_thread=reply_in_thread,
                allow_pdf=allow_pdf,
                conversation_meta=self.meta,
                conversation_common=self.common,
            )
        chat_id = str(self.meta.get("chat_id") or "").strip()
        if chat_id:
            response = self.messenger.send_text(chat_id, text)
            # Direct chat sends do not go through FeishuMessenger's
            # reply_agent_text observer.  Record and relay them here so a
            # native Agent message remains part of the shared Thread and can
            # wake an exact @Agent mention even when there is no reply anchor.
            outbound_id = extract_message_id(response)
            if outbound_id:
                try:
                    from agents.conversation.relay import ConversationRelay

                    relay = ConversationRelay()
                    try:
                        relay.publish(
                            source_agent_id=self.agent_id,
                            source_message_id=outbound_id,
                            text=text,
                            meta=dict(self.meta, message_id=outbound_id),
                            common=self.common,
                            dispatch_async=False,
                        )
                    finally:
                        relay.close()
                except Exception:
                    # Delivery already succeeded; transcript/relay
                    # persistence must not turn it into a failed message.
                    pass
            return response
        return None

    def _workspace_roots(self) -> list[Path]:
        roots: list[Path] = []
        for key in ("_workspace_path", "workspace_path"):
            value = str(self.meta.get(key) or "").strip()
            if not value:
                continue
            try:
                root = Path(value).expanduser().resolve()
            except OSError:
                continue
            if root not in roots:
                roots.append(root)
        extra = self.meta.get("_artifact_roots")
        if isinstance(extra, (list, tuple, set)):
            for value in extra:
                try:
                    root = Path(str(value)).expanduser().resolve()
                except OSError:
                    continue
                if root not in roots:
                    roots.append(root)
        return roots

    def _safe_artifact_path(self, path: Path) -> Path | None:
        """Keep native file output inside the current workspace boundary."""

        roots = self._workspace_roots()
        raw = path.expanduser()
        candidates: list[Path] = []
        if not raw.is_absolute():
            candidates.extend(root / raw for root in roots)
        candidates.append(raw)
        for candidate_path in candidates:
            try:
                candidate = candidate_path.resolve()
            except OSError:
                continue
            for root in roots:
                try:
                    candidate.relative_to(root)
                    return candidate
                except ValueError:
                    continue
        return None

    def _artifact_label(self, path: Path) -> str:
        safe = self._safe_artifact_path(path)
        if safe is None:
            return path.name or "artifact"
        for root in self._workspace_roots():
            try:
                return str(safe.relative_to(root))
            except (OSError, ValueError):
                continue
        return safe.name or "artifact"

    @staticmethod
    def _with_transport_id(event: ConversationEvent, response: Mapping[str, Any] | None) -> ConversationEvent:
        transport_id = extract_message_id(response)
        if not transport_id:
            return event
        payload = dict(event.payload)
        payload.setdefault("transport_message_id", transport_id)
        return ConversationEvent(
            event_id=event.event_id,
            thread_id=event.thread_id,
            agent_id=event.agent_id,
            type=event.type,
            text=event.text,
            payload=payload,
            visibility=event.visibility,
            created_at=event.created_at,
            chat_id=event.chat_id,
            source_message_id=event.source_message_id,
            session_id=event.session_id,
            dedupe_key=event.dedupe_key,
        )

    def emit(
        self,
        event_type: str,
        text: str = "",
        *,
        payload: Mapping[str, Any] | None = None,
        attachment_path: str | Path = "",
        terminal: bool = False,
        visibility: str = "public",
    ) -> OutputReceipt:
        clean_text = str(text or "").strip()
        protocol_leak_prevented = False
        if visibility == "public":
            clean_text, protocol_leak_prevented = sanitize_public_text(clean_text)
        values = dict(payload or {})
        path = Path(str(attachment_path or "")).expanduser() if attachment_path else None
        if path is not None:
            values.setdefault("path", self._artifact_label(path))
        event = self._event(event_type, clean_text, values, visibility=visibility)
        if protocol_leak_prevented:
            telemetry = self._event(
                "conversation.protocol_leak.prevented",
                "",
                {
                    "source_event_type": event_type,
                    "removed_protocol_content": True,
                },
                visibility="internal",
            )
            try:
                self.event_bus.publish(telemetry)
            except Exception:
                # Public delivery remains independent from telemetry storage.
                pass
            if not clean_text and path is None:
                return OutputReceipt(status="filtered", event=telemetry)
        now = time.monotonic()
        if (
            not terminal
            and event.type == "agent.progress"
            and self.config.minimum_event_interval_seconds > 0
        ):
            previous = self._last_public_event.get(event.type, 0.0)
            if previous and now - previous < self.config.minimum_event_interval_seconds:
                return OutputReceipt(status="throttled", event=event)
        # Check before touching Feishu.  Persisting the event after delivery is
        # still required for atomicity with the transcript, but this early
        # check prevents retries from uploading/sending the same artifact
        # twice when the previous attempt already committed its receipt.
        if event.dedupe_key and self.event_bus.has_dedupe(event.dedupe_key):
            return OutputReceipt(status="duplicate", event=event)
        response: dict[str, Any] | None = None
        try:
            if clean_text:
                response = self._send_text(clean_text, allow_pdf=False)
                if response is None:
                    return OutputReceipt(status="failed", event=event, error="conversation output was not delivered")
            if path is not None:
                safe_path = self._safe_artifact_path(path)
                if safe_path is None:
                    return OutputReceipt(status="failed", event=event, response=response, error="artifact is outside the workspace boundary")
                if not safe_path.is_file():
                    return OutputReceipt(status="failed", event=event, response=response, error=f"artifact not found: {safe_path}")
                file_key = self.messenger.upload_file(safe_path)
                source_message_id = str(self.meta.get("message_id") or "").strip()
                if source_message_id:
                    response = self.messenger.reply_file(
                        source_message_id,
                        file_key,
                        reply_in_thread=should_reply_in_thread(self.meta),
                    )
                else:
                    send_file = getattr(self.messenger, "send_file", None)
                    response = send_file(str(self.meta.get("chat_id") or ""), file_key) if callable(send_file) else None
                if response is None:
                    return OutputReceipt(status="failed", event=event, error="artifact output was not delivered")
            event = self._with_transport_id(event, response)
            stored = self.event_bus.publish(event)
            if stored is None:
                return OutputReceipt(status="duplicate", event=event, response=response)
            self._last_public_event[event.type] = now
            self.quality.record_public(event.type, clean_text, event.payload, now=now)
            return OutputReceipt(
                status="succeeded",
                event=stored,
                response=response,
                message_id=extract_message_id(response),
            )
        except Exception as exc:
            return OutputReceipt(status="failed", event=event, response=response, error=str(exc)[:500])

    def observe(self, event_type: str, text: str = "", **payload: Any) -> OutputReceipt:
        """Persist non-user-visible Harness telemetry without sending it.

        Provider tool calls and completion markers belong in the durable
        activity stream for the Dashboard, but must never become Feishu
        messages or leak raw provider arguments.
        """

        event = self._event(event_type, str(text or "").strip(), payload, visibility="internal")
        if event.dedupe_key and self.event_bus.has_dedupe(event.dedupe_key):
            return OutputReceipt(status="duplicate", event=event)
        try:
            stored = self.event_bus.publish(event)
            if stored is None:
                return OutputReceipt(status="duplicate", event=event)
            if event.type in {"agent.completed", "session.completed"}:
                self.quality.mark_conclusion()
            return OutputReceipt(status="succeeded", event=stored)
        except Exception as exc:
            return OutputReceipt(status="failed", event=event, error=str(exc)[:500])

    def message(self, text: str, **payload: Any) -> OutputReceipt:
        return self.emit("agent.message", text, payload=payload)

    def progress(self, text: str, **payload: Any) -> OutputReceipt:
        return self.emit("agent.progress", text, payload=payload)

    def finding(self, text: str, **payload: Any) -> OutputReceipt:
        return self.emit("agent.finding", text, payload=payload)

    def decision(self, text: str, **payload: Any) -> OutputReceipt:
        return self.emit("agent.decision", text, payload=payload)

    def question(self, text: str, **payload: Any) -> OutputReceipt:
        return self.emit("agent.question", text, payload=payload)

    def handoff(self, text: str, **payload: Any) -> OutputReceipt:
        return self.emit("agent.handoff", text, payload=payload)

    def blocked(self, text: str, **payload: Any) -> OutputReceipt:
        return self.emit("agent.blocked", text, payload=payload)

    def artifact(self, path: str | Path, *, text: str = "", **payload: Any) -> OutputReceipt:
        return self.emit("agent.artifact", text, payload=payload, attachment_path=path)

    def mark_conclusion(self) -> None:
        """Record that the current turn reached a stable conclusion."""

        self.quality.mark_conclusion()

    def quality_summary(self) -> dict[str, Any]:
        """Return observational conversation-quality metrics for telemetry."""

        return self.quality.summary()
