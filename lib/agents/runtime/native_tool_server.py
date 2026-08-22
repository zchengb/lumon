"""Minimal stdio MCP-compatible dispatcher for the Lumon tool seam.

Provider-native clients can use ``tools/list`` without knowing Lumon's legacy
action envelope. Calls are still routed through ``ConnectedToolExecutor`` and
therefore retain Host identity/receipt handling. The default process is
intentionally conservative: without an inbound gate context it refuses a
call instead of guessing a human identity.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
from pathlib import Path
from typing import Any

from agents.runtime.connected_tools import ConnectedToolExecutor, ConnectedToolRegistry
from agents.security.access_policy import AccessDecision, InteractionContext, POLICY_VERSION
from agents.security.trusted import TrustedActionContext


def _env_list(name: str) -> tuple[str, ...]:
    raw = str(os.environ.get(name) or "").strip()
    if not raw:
        return ()
    try:
        value = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        value = raw.split(",")
    if not isinstance(value, (list, tuple, set)):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _response(request_id: Any, result: Any = None, error: Any = None) -> dict[str, Any]:
    value: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error is not None:
        value["error"] = error
    else:
        value["result"] = result
    return value


def _context() -> TrustedActionContext | None:
    token = str(os.environ.get("LUMON_ENTRY_GATE_TOKEN") or "").strip()
    if not token:
        return None
    user_id = str(os.environ.get("LUMON_GATE_USER_ID") or "")
    chat_id = str(os.environ.get("LUMON_GATE_CHAT_ID") or "")
    thread_id = str(os.environ.get("LUMON_GATE_THREAD_ID") or "")
    agent_id = str(os.environ.get("LUMEN_AGENT_ID") or "agent")
    access_context = InteractionContext(
        agent_id=agent_id,
        user_id=user_id,
        chat_id=chat_id,
        chat_type=str(os.environ.get("LUMON_GATE_CHAT_TYPE") or ""),
        thread_id=thread_id,
        message_id=str(os.environ.get("LUMON_GATE_MESSAGE_ID") or ""),
        is_dm=os.environ.get("LUMON_GATE_IS_DM") == "1",
        trust_zone=str(os.environ.get("LUMON_GATE_TRUST_ZONE") or ""),
        chat_name=str(os.environ.get("LUMON_GATE_CHAT_NAME") or ""),
        root_id=str(os.environ.get("LUMON_GATE_ROOT_ID") or ""),
        participants=_env_list("LUMON_GATE_PARTICIPANTS"),
        available_agents=_env_list("LUMON_GATE_AVAILABLE_AGENTS"),
        available_agents_verified=os.environ.get("LUMON_GATE_AVAILABLE_AGENTS_VERIFIED") == "1",
    )
    decision = AccessDecision(
        allowed=os.environ.get("LUMON_GATE_ALLOWED") == "1",
        reason_code="ENTRY_GATE",
        trust_zone=str(os.environ.get("LUMON_GATE_TRUST_ZONE") or "") or None,
        host_read_allowed=os.environ.get("LUMON_GATE_HOST_READ") == "1",
        mutation_allowed=os.environ.get("LUMON_GATE_MUTATION") == "1",
        effective_capabilities=frozenset(
            item.strip() for item in str(os.environ.get("LUMON_GATE_CAPABILITIES") or "").split(",") if item.strip()
        ),
        policy_version=POLICY_VERSION,
        context=access_context,
    )
    return TrustedActionContext(
        agent_id=agent_id,
        project_slug=str(os.environ.get("LUMEN_PROJECT") or ""),
        actor_user_id=str(os.environ.get("LUMON_GATE_USER_ID") or ""),
        chat_id=str(os.environ.get("LUMON_GATE_CHAT_ID") or ""),
        thread_id=str(os.environ.get("LUMON_GATE_THREAD_ID") or ""),
        source_message_id=str(os.environ.get("LUMON_GATE_MESSAGE_ID") or ""),
        trace_id=str(os.environ.get("LUMON_GATE_TRACE_ID") or ""),
        access_decision=decision,
        entry_gate_token=token,
    )


def handle(request: dict[str, Any], *, executor: ConnectedToolExecutor | None = None) -> dict[str, Any]:
    request_id = request.get("id")
    method = str(request.get("method") or "")
    params = request.get("params") if isinstance(request.get("params"), dict) else {}
    registry = executor.registry if executor is not None else ConnectedToolRegistry(include_legacy=False)
    if method in {"initialize", "notifications/initialized"}:
        return _response(request_id, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}})
    if method in {"tools/list", "list_tools"}:
        return _response(request_id, {"tools": registry.schemas()})
    if method in {"tools/call", "call_tool"}:
        context = _context()
        if context is None:
            return _response(request_id, error={"code": -32001, "message": "entry gate context is required"})
        name = str(params.get("name") or params.get("tool") or "")
        arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        try:
            if executor is None:
                socket_path = str(os.environ.get("LUMON_NATIVE_TOOL_SOCKET") or "").strip()
                if not socket_path:
                    return _response(
                        request_id,
                        error={"code": -32003, "message": "Host native-tool dispatcher is not connected"},
                    )
                result = _dispatch_to_host(socket_path, {"name": name, "arguments": arguments})
            else:
                result = executor.execute(name, arguments, context=context)
            if hasattr(result, "to_dict"):
                result = result.to_dict()
            return _response(request_id, {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, default=str)}], "structuredContent": result})
        except Exception as exc:
            return _response(request_id, error={"code": -32002, "message": str(exc)[:500]})
    return _response(request_id, error={"code": -32601, "message": f"method not found: {method}"})


def _dispatch_to_host(socket_path: str, request: dict[str, Any]) -> Any:
    """Send one native call to the Host-owned dispatcher."""

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(30)
        client.connect(socket_path)
        client.sendall((json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8"))
        data = client.makefile("rb").readline()
    if not data:
        raise RuntimeError("Host native-tool dispatcher closed without a response")
    response = json.loads(data.decode("utf-8"))
    if not isinstance(response, dict) or response.get("ok") is not True:
        raise RuntimeError(str((response or {}).get("error") or "native tool dispatch failed")[:500])
    return response.get("result")


class NativeToolDispatcher:
    """Host-side Unix socket bridge for provider-native tool calls."""

    def __init__(self, *, socket_path: Path, executor: ConnectedToolExecutor, context: TrustedActionContext) -> None:
        self.socket_path = Path(socket_path).expanduser().resolve()
        self.executor = executor
        self.context = context
        self._server: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> "NativeToolDispatcher":
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        self.socket_path.unlink(missing_ok=True)
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(self.socket_path))
        server.listen(8)
        server.settimeout(0.5)
        self._server = server
        self._thread = threading.Thread(target=self._serve, name="lumon-native-tool-host", daemon=True)
        self._thread.start()
        return self

    def _serve(self) -> None:
        server = self._server
        if server is None:
            return
        while not self._stop.is_set():
            try:
                client, _ = server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with client:
                try:
                    line = client.makefile("rb").readline()
                    request = json.loads(line.decode("utf-8")) if line else {}
                    name = str(request.get("name") or "")
                    arguments = request.get("arguments") if isinstance(request.get("arguments"), dict) else {}
                    result = self.executor.execute(name, arguments, context=self.context)
                    if hasattr(result, "to_dict"):
                        result = result.to_dict()
                    payload = {"ok": True, "result": result}
                except Exception as exc:
                    payload = {"ok": False, "error": str(exc)[:500]}
                client.sendall((json.dumps(payload, ensure_ascii=False, default=str) + "\n").encode("utf-8"))

    def close(self) -> None:
        self._stop.set()
        if self._server is not None:
            try:
                self._server.close()
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=1)
        try:
            self.socket_path.unlink(missing_ok=True)
        except OSError:
            pass


def main() -> int:
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if isinstance(request, dict):
                print(json.dumps(handle(request), ensure_ascii=False, default=str), flush=True)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            print(json.dumps(_response(None, error={"code": -32700, "message": str(exc)[:200]}), ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
