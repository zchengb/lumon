"""Bounded JSON-RPC transport to a private local Codex app-server process."""

from __future__ import annotations

import asyncio
import json
import os
import signal
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast


class CodexRpcError(Exception):
    """Provider error; deliberately excludes arbitrary server text and credentials."""

    def __init__(self, code: int | None = None) -> None:
        super().__init__("Codex app-server request failed.")
        self.code = code


class CodexRpc:
    def __init__(self) -> None:
        self.notifications: asyncio.Queue[dict[str, object]] = asyncio.Queue(maxsize=512)
        self.process: asyncio.subprocess.Process | None = None
        self._reader: asyncio.Task[None] | None = None
        self._stderr: asyncio.Task[None] | None = None
        self._pending: dict[int, asyncio.Future[dict[str, object]]] = {}
        self._sequence = 0

    async def start(
        self,
        binary: str,
        workspace: Path,
        environment: Mapping[str, str] | None,
        *,
        config: Sequence[str] = (),
    ) -> None:
        self.process = await asyncio.create_subprocess_exec(
            binary,
            "app-server",
            *(part for item in config for part in ("--config", item)),
            "--listen",
            "stdio://",
            cwd=workspace,
            env=environment,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=16 * 1024 * 1024,
            start_new_session=os.name == "posix",
        )
        self._reader = asyncio.create_task(self._read())
        self._stderr = asyncio.create_task(self._drain_stderr())

    async def send(self, payload: dict[str, object]) -> None:
        process = self.process
        if process is None or process.stdin is None or process.returncode is not None:
            raise CodexRpcError()
        process.stdin.write((json.dumps(payload) + "\n").encode())
        await process.stdin.drain()

    async def request(
        self, method: str, params: dict[str, object], *, timeout: float = 30
    ) -> dict[str, object]:
        self._sequence += 1
        request_id = self._sequence
        future: asyncio.Future[dict[str, object]] = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        try:
            await self.send({"id": request_id, "method": method, "params": params})
            return await asyncio.wait_for(future, timeout)
        finally:
            self._pending.pop(request_id, None)

    async def _read(self) -> None:
        assert self.process is not None and self.process.stdout is not None
        try:
            while line := await self.process.stdout.readline():
                payload: object = json.loads(line)
                if not isinstance(payload, dict):
                    raise CodexRpcError()
                message = cast(dict[str, object], payload)
                if "method" in message:
                    await self._receive_method(message)
                else:
                    self._receive_reply(message)
        except (ValueError, OSError, CodexRpcError):
            pass  # The process boundary reports a safe failure, never raw protocol text.
        finally:
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(CodexRpcError())
            # Wake the event consumer even when the provider closes unexpectedly.
            if self.notifications.full():
                self.notifications.get_nowait()
            self.notifications.put_nowait({"method": "lumon/closed"})

    async def _receive_method(self, message: dict[str, object]) -> None:
        if "id" in message:
            # Full-access operation needs no approvals. Never auto-approve new RPC types.
            await self.send(
                {
                    "id": message["id"],
                    "error": {
                        "code": -32601,
                        "message": "Unsupported client request; not approved.",
                    },
                }
            )
            return
        try:
            self.notifications.put_nowait(message)
        except asyncio.QueueFull as exc:
            raise CodexRpcError() from exc

    def _receive_reply(self, message: dict[str, object]) -> None:
        request_id = message.get("id")
        future = self._pending.get(request_id) if isinstance(request_id, int) else None
        if future is None or future.done():
            return
        result = message.get("result")
        if "error" in message or not isinstance(result, dict):
            error = message.get("error")
            code = cast(dict[str, object], error).get("code") if isinstance(error, dict) else None
            future.set_exception(CodexRpcError(code if isinstance(code, int) else None))
        else:
            future.set_result(cast(dict[str, object], result))

    async def _drain_stderr(self) -> None:
        assert self.process is not None and self.process.stderr is not None
        while await self.process.stderr.read(65536):
            pass

    async def close(self, *, kill_tools: bool = True) -> None:
        process = self.process
        if process is not None:
            # A fresh process group belongs exclusively to this execution, including tools.
            try:
                if kill_tools and os.name == "posix":
                    os.killpg(process.pid, signal.SIGKILL)
                elif process.returncode is None:
                    process.kill()
            except ProcessLookupError:
                pass
            await process.wait()
        tasks = [task for task in (self._reader, self._stderr) if task is not None]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
