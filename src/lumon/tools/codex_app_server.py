"""One steerable Codex execution using the CLI's native app-server protocol."""

from __future__ import annotations

import asyncio
import json
from collections import deque
from typing import cast

from lumon.tools.codex import (
    CodexErrorCode,
    CodexEvent,
    CodexEventCallback,
    CodexExecutionResult,
    CodexRequest,
    CodexTool,
    parse_codex_line,
)
from lumon.tools.codex_rpc import CodexRpc, CodexRpcError
from lumon.tools.steering import SteeringControl, SteeringInput, SteeringRequest
from lumon.version import __version__


async def execute_steerable(
    tool: CodexTool,
    request: CodexRequest,
    control: SteeringControl,
    on_event: CodexEventCallback | None = None,
) -> CodexExecutionResult:
    session = _Execution(tool, request, control, on_event)
    try:
        return await asyncio.wait_for(session.run(), tool.timeout_seconds)
    except TimeoutError:
        return session.failure(CodexErrorCode.TIMEOUT, timed_out=True)
    except FileNotFoundError:
        return session.failure(CodexErrorCode.CLI_NOT_FOUND)
    except (OSError, ValueError, CodexRpcError):
        return session.failure(CodexErrorCode.EXECUTION_FAILED)
    finally:
        control.close()
        await session.close()


class _Execution:
    def __init__(
        self,
        tool: CodexTool,
        request: CodexRequest,
        control: SteeringControl,
        on_event: CodexEventCallback | None,
    ) -> None:
        self.tool, self.request, self.control = tool, request, control
        self.on_event = on_event
        self.rpc = CodexRpc()
        self.thread_id: str | None = None
        self.turn_id: str | None = None
        self.turn_done: asyncio.Future[dict[str, object]] | None = None
        self.ready = asyncio.Event()
        self.input_lock = asyncio.Lock()
        self.replacements: list[SteeringRequest] = []
        self.tasks: list[asyncio.Task[None]] = []
        self.events: deque[CodexEvent] = deque(maxlen=200)
        self.callbacks: asyncio.Queue[CodexEvent] = asyncio.Queue(maxsize=200)
        self.final_text: str | None = None
        self.succeeded = False
        self.early_notifications: list[dict[str, object]] = []
        self.callback_failed = False

    async def run(self) -> CodexExecutionResult:
        await self.rpc.start(self.tool.binary, self.request.workspace, self.tool.environment)
        await self.rpc.request(
            "initialize",
            {"clientInfo": {"name": "lumon", "title": "Lumon", "version": __version__}},
        )
        await self.rpc.send({"method": "initialized", "params": {}})
        params: dict[str, object] = {
            "cwd": str(self.request.workspace),
            "approvalPolicy": "never",
        }
        if self.tool.model:
            params["model"] = self.tool.model
        if self.request.resume_session_id:
            params["threadId"] = self.request.resume_session_id
            response = await self.rpc.request("thread/resume", params)
        else:
            params["sandbox"] = "danger-full-access"
            response = await self.rpc.request("thread/start", params)
        self.thread_id = _string(_object(response.get("thread")), "id")
        self.tasks = [
            asyncio.create_task(self._notifications()),
            asyncio.create_task(self._callbacks()),
            asyncio.create_task(self._inputs()),
        ]
        await self._start_turn(
            [SteeringInput(self.request.prompt, self.request.images, self.control.policy)]
        )
        while True:
            assert self.turn_done is not None
            outcome = await self.turn_done
            async with self.input_lock:
                if self.replacements:
                    requests, self.replacements = self.replacements, []
                    await self._start_turn([item.input for item in requests])
                    for item in requests:
                        if not item.accepted.done():
                            item.accepted.set_result(True)
                    continue
                self.control.close()
                if outcome.get("status") != "completed":
                    return self.failure(CodexErrorCode.EXECUTION_FAILED)
                break
        await asyncio.wait_for(self.callbacks.join(), timeout=10)
        if self.callback_failed:
            raise CodexRpcError()
        self.succeeded = True
        return CodexExecutionResult(
            status="succeeded",
            final_text=self.final_text,
            events=tuple(self.events),
            return_code=0,
            agent_session_id=self.thread_id,
        )

    async def _start_turn(self, inputs: list[SteeringInput]) -> None:
        self.ready.clear()
        self.turn_id = None
        self.early_notifications.clear()
        self.turn_done = asyncio.get_running_loop().create_future()
        self.final_text = None
        if not self.callbacks.full():
            self.callbacks.put_nowait(CodexEvent("turn_started"))
        params: dict[str, object] = {
            "threadId": self.thread_id,
            "input": [part for item in inputs for part in _user_input(item)],
        }
        policy = next((item.policy for item in reversed(inputs) if item.policy), None)
        if self.control.policy == "pause":
            policy = "pause"
        if policy:
            params["sandboxPolicy"] = (
                {"type": "readOnly", "networkAccess": False}
                if policy == "pause"
                else {"type": "dangerFullAccess"}
            )
        if self.tool.reasoning_effort:
            params["effort"] = self.tool.reasoning_effort
        result = await self.rpc.request("turn/start", params)
        self.turn_id = _string(_object(result.get("turn")), "id")
        for message in self.early_notifications:
            self._apply_notification(message)
        self.early_notifications.clear()
        self.ready.set()

    async def _inputs(self) -> None:
        try:
            while True:
                request = await self.control.receive()
                await self.ready.wait()
                async with self.input_lock:
                    await self._deliver_input(request)
        except (OSError, TimeoutError, CodexRpcError) as exc:
            if self.turn_done is not None and not self.turn_done.done():
                self.turn_done.set_exception(CodexRpcError())
            raise CodexRpcError() from exc

    async def _deliver_input(self, request: SteeringRequest) -> None:
        if request.accepted.done():
            return
        if self.turn_done is None or self.turn_done.done():
            request.accepted.set_result(False)
            return
        if request.input.policy:
            # Unlike steer, interrupt cancels currently executing tools. The replacement
            # turn enforces a read-only sandbox, not just a natural-language prohibition.
            self.replacements.append(request)
            await self.rpc.request(
                "turn/interrupt",
                {
                    "threadId": self.thread_id,
                    "turnId": self.turn_id,
                },
                timeout=3,
            )
            await asyncio.wait_for(asyncio.shield(self.turn_done), timeout=1)
            return
        try:
            result = await self.rpc.request(
                "turn/steer",
                {
                    "threadId": self.thread_id,
                    "expectedTurnId": self.turn_id,
                    "input": _user_input(request.input),
                },
                timeout=3,
            )
        except CodexRpcError as exc:
            if exc.code == -32600:  # The turn can finish between the local check and RPC.
                request.accepted.set_result(False)
                return
            raise
        if result.get("turnId") != self.turn_id:
            raise CodexRpcError()
        request.accepted.set_result(True)

    async def _notifications(self) -> None:
        try:
            while True:
                message = await self.rpc.notifications.get()
                if message.get("method") == "lumon/closed":
                    raise CodexRpcError()
                if message.get("method") not in {
                    "turn/completed",
                    "item/started",
                    "item/completed",
                }:
                    continue
                if self.turn_id is None:
                    if len(self.early_notifications) >= 200:
                        raise CodexRpcError()
                    self.early_notifications.append(message)
                    continue
                self._apply_notification(message)
        except (ValueError, CodexRpcError) as exc:
            if self.turn_done is not None and not self.turn_done.done():
                self.turn_done.set_exception(CodexRpcError())
            raise CodexRpcError() from exc

    def _apply_notification(self, message: dict[str, object]) -> None:
        params = _object(message.get("params"))
        if params.get("threadId") != self.thread_id:
            return
        method = message.get("method")
        if method == "turn/completed":
            turn = _object(params.get("turn"))
            if self.turn_done is not None and not self.turn_done.done():
                if turn.get("id") == self.turn_id:
                    self.turn_done.set_result(turn)
            return
        if params.get("turnId") != self.turn_id:
            return
        event = _event(method, params)
        if event is not None:
            self.events.append(event)
            if event.kind == "message":
                self.final_text = event.text
            if not self.callbacks.full():
                self.callbacks.put_nowait(event)

    async def _callbacks(self) -> None:
        while True:
            event = await self.callbacks.get()
            try:
                if self.on_event is not None:
                    await self.on_event(event)
            except Exception as exc:
                self.callback_failed = True
                if self.turn_done is not None and not self.turn_done.done():
                    self.turn_done.set_exception(CodexRpcError())
                raise CodexRpcError() from exc
            finally:
                self.callbacks.task_done()

    def failure(self, code: CodexErrorCode, *, timed_out: bool = False) -> CodexExecutionResult:
        return CodexExecutionResult(
            status="timed_out" if timed_out else "failed",
            error_code=code,
            agent_session_id=self.thread_id,
            events=tuple(self.events),
            failure_diagnostic="Codex app-server did not complete; active execution was stopped.",
        )

    async def close(self) -> None:
        if self.turn_id and self.turn_done is not None and not self.turn_done.done():
            try:
                await self.rpc.request(
                    "turn/interrupt",
                    {
                        "threadId": self.thread_id,
                        "turnId": self.turn_id,
                    },
                    timeout=1,
                )
            except (OSError, TimeoutError, CodexRpcError):
                pass  # Process-group cleanup below is the fail-closed fallback.
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        await self.rpc.close(kill_tools=not self.succeeded)


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise CodexRpcError()
    return cast(dict[str, object], value)


def _string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise CodexRpcError()
    return value


def _user_input(message: SteeringInput) -> list[dict[str, object]]:
    return [
        {"type": "text", "text": message.text},
        *({"type": "localImage", "path": str(path)} for path in message.images),
    ]


def _event(method: object, params: dict[str, object]) -> CodexEvent | None:
    if method not in {"item/started", "item/completed"}:
        return None
    item = _object(params.get("item"))
    kind = item.get("type")
    mapped = {
        "agentMessage": "agent_message",
        "commandExecution": "command_execution",
        "fileChange": "file_change",
    }.get(str(kind))
    if mapped is None or (mapped == "agent_message" and method != "item/completed"):
        return None
    translated = {
        **item,
        "type": mapped,
        "aggregated_output": item.get("aggregatedOutput"),
        "exit_code": item.get("exitCode"),
    }
    lifecycle = "started" if method == "item/started" else "completed"
    return parse_codex_line(json.dumps({"type": f"item.{lifecycle}", "item": translated}))
