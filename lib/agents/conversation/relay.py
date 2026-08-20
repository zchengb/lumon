from __future__ import annotations

import hashlib
import logging
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from agents.conversation.config import ThreadNativeConfig
from agents.conversation.thread_store import ThreadMessage, ThreadTranscriptStore
from feishu.agent_mentions import parse_agent_mentions


_LOG = logging.getLogger("lumen.agent.conversation")


@dataclass(frozen=True)
class TrustedConversationContext:
    origin_user_id: str
    source_agent_id: str
    target_agent_id: str
    chat_id: str
    chat_type: str = ""
    thread_id: str = ""
    root_id: str = ""
    project_slug: str = ""
    source_message_id: str = ""
    relay_id: str = ""
    hop_count: int = 0
    visited_agents: tuple[str, ...] = ()


@dataclass(frozen=True)
class AgentConversationEvent:
    context: TrustedConversationContext
    text: str
    attachment_refs: tuple[str, ...] = ()


def relay_id_for(*, source_message_id: str, source_agent_id: str, text: str) -> str:
    digest = hashlib.sha256(
        f"{source_message_id}\0{source_agent_id}\0{text}".encode("utf-8")
    ).hexdigest()[:24]
    return f"relay_{digest}"


class ConversationRelay:
    """Wake a mentioned Agent through the normal bridge path."""

    def __init__(
        self,
        *,
        store: ThreadTranscriptStore | None = None,
        config: ThreadNativeConfig | None = None,
        dispatch: Callable[[str, str, dict[str, str]], Any] | None = None,
    ) -> None:
        self.store = store or ThreadTranscriptStore()
        self._owned = store is None
        self.config = config or ThreadNativeConfig()
        self.dispatch = dispatch

    def close(self) -> None:
        if self._owned:
            self.store.close()

    def publish(
        self,
        *,
        source_agent_id: str,
        source_message_id: str,
        text: str,
        meta: dict[str, Any],
        common: dict[str, Any] | None = None,
        attachment_refs: Iterable[str] = (),
        dispatch_async: bool = True,
    ) -> ThreadMessage | None:
        """Record a successful visible Agent message and relay exact mentions."""

        from agents.conversation.config import thread_native_config

        config = thread_native_config(common, meta)
        target_ids = [item.agent_id for item in parse_agent_mentions(text)]
        data = meta if isinstance(meta, dict) else {}
        outbound = ThreadMessage(
            message_id=str(source_message_id or "").strip(),
            chat_id=str(data.get("chat_id") or "").strip(),
            thread_id=str(data.get("thread_id") or "").strip(),
            # Feishu may omit root_id for a normal group message.  The
            # original inbound message is then the stable fallback anchor;
            # using the newly-created outbound id would split one thread into
            # unrelated transcripts.
            root_id=str(
                data.get("root_id")
                or data.get("parent_id")
                or data.get("message_id")
                or source_message_id
                or ""
            ).strip(),
            parent_id=str(data.get("message_id") or "").strip(),
            sender_kind="agent",
            sender_user_id=str(data.get("_origin_user_id") or data.get("user_id") or "").strip(),
            sender_agent_id=str(source_agent_id or "").strip().lower(),
            text=str(text or "").strip(),
            mentions=target_ids,
            attachment_refs=list(attachment_refs),
            project_slug=str(data.get("_project_slug") or data.get("project_slug") or "").strip(),
        )
        if not outbound.message_id or not outbound.chat_id:
            return None
        self.store.record(outbound)
        _LOG.info(
            "thread.message.outbound source_agent=%s target_mentions=%s chat_id=%s thread_id=%s message_id=%s",
            outbound.sender_agent_id,
            ",".join(target_ids),
            outbound.chat_id,
            outbound.thread_id or outbound.root_id,
            outbound.message_id,
        )
        for target_id in target_ids:
            _LOG.info(
                "agent.mention.detected source_agent=%s target_agent=%s chat_id=%s thread_id=%s source_message_id=%s",
                outbound.sender_agent_id,
                target_id,
                outbound.chat_id,
                outbound.thread_id or outbound.root_id,
                outbound.message_id,
            )
        if not config.enabled or not target_ids:
            if target_ids:
                _LOG.info(
                    "agent.conversation.relay.skipped reason=feature_disabled source_agent=%s chat_id=%s thread_id=%s",
                    outbound.sender_agent_id,
                    outbound.chat_id,
                    outbound.thread_id or outbound.root_id,
                )
            return outbound

        origin = str(data.get("_origin_user_id") or data.get("user_id") or "").strip()
        try:
            current_hop = max(0, int(str(data.get("_relay_hop") or "0") or 0))
        except (TypeError, ValueError):
            current_hop = 0
        visited = tuple(
            item.strip().lower()
            for item in str(data.get("_relay_visited") or "").split(",")
            if item.strip()
        )
        for target_id in target_ids:
            if target_id == str(source_agent_id or "").strip().lower() or target_id in visited:
                _LOG.info(
                    "agent.conversation.loop_blocked source_agent=%s target_agent=%s source_message_id=%s",
                    source_agent_id,
                    target_id,
                    outbound.message_id,
                )
                continue
            if current_hop >= config.max_relay_hops:
                _LOG.info(
                    "agent.conversation.relay.skipped reason=max_hops source_agent=%s target_agent=%s hop=%s source_message_id=%s",
                    source_agent_id,
                    target_id,
                    current_hop,
                    outbound.message_id,
                )
                continue
            context = TrustedConversationContext(
                origin_user_id=origin,
                source_agent_id=str(source_agent_id or "").strip().lower(),
                target_agent_id=target_id,
                chat_id=outbound.chat_id,
                chat_type=str(data.get("chat_type") or "").strip().lower(),
                thread_id=outbound.thread_id,
                root_id=outbound.root_id,
                project_slug=outbound.project_slug,
                source_message_id=outbound.message_id,
                relay_id=relay_id_for(
                    source_message_id=outbound.message_id,
                    source_agent_id=outbound.sender_agent_id,
                    text=outbound.text,
                ),
                hop_count=current_hop + 1,
                visited_agents=tuple(dict.fromkeys((*visited, outbound.sender_agent_id))),
            )
            if not self.store.mark_relay(
                relay_id=context.relay_id,
                source_message_id=context.source_message_id,
                source_agent_id=context.source_agent_id,
                target_agent_id=context.target_agent_id,
                hop=context.hop_count,
            ):
                _LOG.info(
                    "agent.conversation.relay.skipped reason=duplicate relay_id=%s target_agent=%s source_message_id=%s",
                    context.relay_id,
                    target_id,
                    outbound.message_id,
                )
                continue
            _LOG.info(
                "agent.conversation.relayed source_agent=%s target_agent=%s origin_user_id=%s chat_id=%s thread_id=%s source_message_id=%s relay_id=%s hop=%s",
                context.source_agent_id,
                context.target_agent_id,
                context.origin_user_id,
                context.chat_id,
                context.thread_id or context.root_id,
                context.source_message_id,
                context.relay_id,
                context.hop_count,
            )
            event = AgentConversationEvent(context=context, text=outbound.text, attachment_refs=tuple(outbound.attachment_refs))
            if dispatch_async:
                threading.Thread(target=self._dispatch, args=(event,), daemon=True).start()
            else:
                self._dispatch(event)
        return outbound

    def _dispatch(self, event: AgentConversationEvent) -> Any:
        context = event.context
        meta = {
            "message_id": context.source_message_id,
            "chat_id": context.chat_id,
            "thread_id": context.thread_id,
            "parent_id": context.source_message_id,
            "root_id": context.root_id or context.source_message_id,
            "chat_type": context.chat_type or ("group" if context.chat_id.startswith("oc_") else "p2p"),
            # Preserve the original human authority.  The target Agent is not
            # granted authority by the source Agent.
            "user_id": context.origin_user_id,
            "_origin_user_id": context.origin_user_id,
            "_project_slug": context.project_slug,
            "_conversation_relay": "1",
            "_relay_id": context.relay_id,
            "_relay_hop": str(context.hop_count),
            "_relay_visited": ",".join(context.visited_agents),
            "_source_agent": context.source_agent_id,
            "_target_agent": context.target_agent_id,
            "_thread_native_handoff": "1",
        }
        if event.attachment_refs:
            meta["attachment_refs"] = "\n".join(event.attachment_refs)
        callback = self.dispatch
        if callback is None:
            from agents.bridge import handle_agent_message

            callback = lambda agent_id, text, payload: handle_agent_message(
                agent_id=agent_id,
                text=text,
                meta=payload,
            )
        return callback(context.target_agent_id, event.text, meta)


def record_inbound_message(
    *,
    message_id: str,
    meta: dict[str, Any],
    text: str,
    mentions: Iterable[str] = (),
    attachment_refs: Iterable[str] = (),
    project_slug: str = "",
    store: ThreadTranscriptStore | None = None,
) -> ThreadMessage | None:
    owned = store is None
    transcript = store or ThreadTranscriptStore()
    try:
        if not str(message_id or "").strip() or not str(meta.get("chat_id") or "").strip():
            return None
        parent_id = str(meta.get("parent_id") or "").strip()
        parent = transcript.get(parent_id) if parent_id else None
        root_id = str(meta.get("root_id") or "").strip()
        if not root_id and parent is not None:
            root_id = parent.root_id or parent.message_id
        thread_id = str(meta.get("thread_id") or "").strip()
        if not thread_id and parent is not None:
            thread_id = parent.thread_id
        return transcript.record(
            ThreadMessage(
                message_id=str(message_id).strip(),
                chat_id=str(meta.get("chat_id") or "").strip(),
                thread_id=thread_id,
                root_id=root_id,
                parent_id=parent_id,
                sender_kind="user",
                sender_user_id=str(meta.get("user_id") or "").strip(),
                text=str(text or "").strip(),
                mentions=list(dict.fromkeys(str(item or "").strip().lower() for item in mentions if str(item or "").strip())),
                attachment_refs=list(attachment_refs),
                project_slug=str(project_slug or meta.get("_project_slug") or "").strip(),
            )
        )
    finally:
        if owned:
            transcript.close()
