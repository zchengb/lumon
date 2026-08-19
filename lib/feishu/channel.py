from __future__ import annotations

import json
import logging
import multiprocessing
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Optional

from feishu.catchup import StartupCatchup, message_create_time
from feishu.client_registry import FeishuClientConfig, GATEWAY_AGENTS, configured_agents, load_client_config
from feishu.config import agents_home
from feishu.dedup import MessageDeduper
from feishu.handlers import handle_message_event

_LOG = logging.getLogger("lumen.feishu.channel")
_LIB_DIR = str(Path(__file__).resolve().parent.parent)


def _setup_logging() -> None:
    log_path = agents_home() / "gateway.log"
    if _LOG.handlers:
        return
    _LOG.setLevel(logging.INFO)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    _LOG.addHandler(handler)
    stream = logging.StreamHandler()
    stream.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    _LOG.addHandler(stream)


def event_to_dict(data: Any) -> dict[str, Any]:
    if isinstance(data, dict):
        return data
    try:
        import lark_oapi as lark

        raw = lark.JSON.marshal(data)
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        _LOG.exception("failed to marshal feishu event")
    event_obj = getattr(data, "event", None)
    header_obj = getattr(data, "header", None)
    payload: dict[str, Any] = {}
    if header_obj is not None:
        payload["header"] = header_obj if isinstance(header_obj, dict) else getattr(header_obj, "__dict__", {})
    if event_obj is not None:
        if isinstance(event_obj, dict):
            payload["event"] = event_obj
        else:
            message = getattr(event_obj, "message", None)
            sender = getattr(event_obj, "sender", None)
            payload["event"] = {
                "message": message if isinstance(message, dict) else getattr(message, "__dict__", {}),
                "sender": sender if isinstance(sender, dict) else getattr(sender, "__dict__", {}),
            }
    return payload


def _run_single_client_process(agent_id: str, lib_dir: str) -> None:
    # ponytail: lark_oapi.ws shares one module-level asyncio loop; one process per app
    if lib_dir and lib_dir not in sys.path:
        sys.path.insert(0, lib_dir)
    channel = FeishuChannel(clients=[])
    client = load_client_config(agent_id)
    if client is None:
        raise RuntimeError(f"No Feishu credentials for agent {agent_id}")
    channel.clients = [client]
    import lark_oapi as lark
    from lark_oapi.event.dispatcher_handler import EventDispatcherHandler
    from lark_oapi.ws import Client as WsClient

    channel._start_client(client, lark, EventDispatcherHandler, WsClient)


class FeishuChannel:
    def __init__(
        self,
        clients: Optional[list[FeishuClientConfig]] = None,
        on_event: Optional[Callable[[dict[str, Any], FeishuClientConfig], None]] = None,
    ) -> None:
        _setup_logging()
        self.clients = clients if clients is not None else configured_agents(list(GATEWAY_AGENTS))
        self.on_event = on_event or handle_message_event
        self.deduper = MessageDeduper(agents_home() / "dedup.sqlite3")
        self.started_at = time.time()
        self.catchup = StartupCatchup(
            started_at=self.started_at,
            on_flush=self._dispatch_event,
            mark_seen=lambda agent_id, message_id: self.deduper.claim(f"{agent_id}:{message_id}"),
        )

    def process_event(self, event: dict[str, Any], client: FeishuClientConfig) -> None:
        event_body = event.get("event") if isinstance(event.get("event"), dict) else event
        message = event_body.get("message") if isinstance(event_body, dict) else {}
        message_id = ""
        chat_id = ""
        create_time = 0.0
        if isinstance(message, dict):
            message_id = str(message.get("message_id") or "").strip()
            chat_id = str(message.get("chat_id") or "").strip()
            create_time = message_create_time(message)
        decision = self.catchup.offer(
            agent_id=client.agent_id,
            chat_id=chat_id,
            message_id=message_id,
            create_time=create_time,
            event=event,
            client=client,
        )
        if decision == "catchup_buffer":
            _LOG.info(
                "catchup buffer agent=%s chat_id=%s message_id=%s",
                client.agent_id,
                chat_id or "-",
                message_id or "-",
            )
            return
        if decision in {"catchup_drop", "outdated"}:
            _LOG.info(
                "skip %s agent=%s message_id=%s create_time=%s",
                decision,
                client.agent_id,
                message_id or "-",
                int(create_time) if create_time else "-",
            )
            return
        self._dispatch_event(event, client)

    def _dedupe_key(self, client: FeishuClientConfig, message_id: str) -> str:
        mid = str(message_id or "").strip()
        if not mid:
            return ""
        return f"{str(client.agent_id or '').strip().lower()}:{mid}"

    def _dispatch_event(self, event: dict[str, Any], client: FeishuClientConfig) -> None:
        from feishu.handlers import extract_message_meta, remember_message_identities, should_handle

        if not should_handle(event, client):
            # Identity discovery must not depend on routing.  A group message
            # addressed to a human (or to another Agent) still proves that
            # this app is present in the group and that the sender may later
            # appear in the Dashboard's private-contact list if they DM.
            try:
                meta = extract_message_meta(event)
                if str(meta.get("sender_type") or "").strip().lower() not in {"bot", "app"}:
                    remember_message_identities(event, meta, agent_id=client.agent_id)
            except Exception:
                _LOG.debug("unable to record ignored Feishu identity", exc_info=True)
            event_body = event.get("event") if isinstance(event.get("event"), dict) else event
            message = event_body.get("message") if isinstance(event_body, dict) else {}
            _LOG.info(
                "ignore message agent=%s chat_type=%s mentions=%s parent_id=%s thread_id=%s",
                client.agent_id,
                (message.get("chat_type") if isinstance(message, dict) else None),
                (message.get("mentions") if isinstance(message, dict) else None),
                (message.get("parent_id") if isinstance(message, dict) else None),
                (message.get("thread_id") if isinstance(message, dict) else None),
            )
            return
        message_id = ""
        event_body = event.get("event") if isinstance(event.get("event"), dict) else event
        message = event_body.get("message") if isinstance(event_body, dict) else {}
        if isinstance(message, dict):
            message_id = str(message.get("message_id") or "").strip()
        dedupe_key = self._dedupe_key(client, message_id)
        if dedupe_key and not self.deduper.claim(dedupe_key):
            _LOG.info("skip duplicate agent=%s message_id=%s", client.agent_id, message_id or "-")
            return
        _LOG.info(
            "dispatch agent=%s message_id=%s chat_type=%s",
            client.agent_id,
            message_id or "-",
            (message.get("chat_type") if isinstance(message, dict) else "") or "-",
        )
        self.on_event(event, client)

    def start(self) -> None:
        if not self.clients:
            raise RuntimeError(
                "No Feishu agent credentials configured. Set FEISHU_*_APP_ID/SECRET "
                "for dylan, mark, irving, and/or milchick."
            )
        try:
            import lark_oapi as lark
            from lark_oapi.event.dispatcher_handler import EventDispatcherHandler
            from lark_oapi.ws import Client as WsClient
        except ImportError as exc:
            raise RuntimeError(
                "lark-oapi is required for Agent Gateway. Install with: pip install lark-oapi"
            ) from exc

        if len(self.clients) == 1:
            while True:
                try:
                    self._start_client(self.clients[0], lark, EventDispatcherHandler, WsClient)
                except Exception:
                    _LOG.error("ws client failed agent=%s\n%s", self.clients[0].agent_id, traceback.format_exc())
                _LOG.warning("ws client exited; reconnecting agent=%s", self.clients[0].agent_id)
                time.sleep(2)
            return

        ctx = multiprocessing.get_context("spawn")
        clients = {client.agent_id: client for client in self.clients}

        def spawn(client: FeishuClientConfig) -> multiprocessing.Process:
            proc = ctx.Process(
                target=_run_single_client_process,
                args=(client.agent_id, _LIB_DIR),
                name=f"feishu-ws-{client.agent_id}",
                daemon=True,
            )
            proc.start()
            _LOG.info("spawned ws process pid=%s agent=%s", proc.pid, proc.name)
            return proc

        procs = {agent_id: spawn(client) for agent_id, client in clients.items()}
        try:
            while procs:
                for agent_id, proc in list(procs.items()):
                    proc.join(timeout=1)
                    if proc.is_alive():
                        continue
                    _LOG.error(
                        "ws process exited agent=%s exitcode=%s; reconnecting",
                        agent_id,
                        proc.exitcode,
                    )
                    procs[agent_id] = spawn(clients[agent_id])
        finally:
            for proc in procs.values():
                if proc.is_alive():
                    proc.terminate()

    def _start_client(self, client: FeishuClientConfig, lark, EventDispatcherHandler, WsClient) -> None:
        channel = self

        def on_message(data: Any) -> None:
            try:
                raw = event_to_dict(data)
                _LOG.info("received im.message.receive_v1 keys=%s", list(raw.keys()))
                from agents.runtime.jobs_pool import get_executor

                get_executor().submit(channel._safe_process, raw, client)
            except Exception:
                _LOG.error("on_message failed\n%s", traceback.format_exc())

        handler = (
            EventDispatcherHandler.builder("", "")
            .register_p2_im_message_receive_v1(on_message)
            .register_p2_im_message_message_read_v1(lambda *_a, **_k: None)
            .register_p2_im_message_reaction_created_v1(lambda *_a, **_k: None)
            .register_p2_im_message_reaction_deleted_v1(lambda *_a, **_k: None)
            .build()
        )
        ws = WsClient(
            client.app_id,
            client.app_secret,
            event_handler=handler,
            log_level=lark.LogLevel.INFO,
        )
        print(f"Lumen agent gateway listening as {client.agent_id} ({client.app_id[:6]}…)")
        _LOG.info("starting ws client for %s app_id=%s…", client.agent_id, client.app_id[:8])
        try:
            ws.start()
        finally:
            _LOG.warning("ws client returned agent=%s", client.agent_id)

    def _safe_process(self, event: dict[str, Any], client: FeishuClientConfig) -> None:
        try:
            self.process_event(event, client)
        except Exception:
            _LOG.error("process_event failed\n%s", traceback.format_exc())
