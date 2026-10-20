"""Per-execution input mailbox, independent of the chat and provider adapters."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SteeringPolicy = Literal["pause", "resume"]


@dataclass(frozen=True, slots=True)
class SteeringInput:
    text: str
    images: tuple[Path, ...] = ()
    policy: SteeringPolicy | None = None


@dataclass(frozen=True, slots=True)
class SteeringRequest:
    input: SteeringInput
    accepted: asyncio.Future[bool]


class SteeringControl:
    """Acknowledge delivery only after the provider accepts the input."""

    def __init__(self, policy: SteeringPolicy | None = None) -> None:
        self.policy: SteeringPolicy | None = policy
        self.closed = False
        self._sequence = 0
        self._queue: asyncio.PriorityQueue[tuple[int, int, SteeringRequest]] = (
            asyncio.PriorityQueue(maxsize=32)
        )
        self._receipts: set[asyncio.Future[bool]] = set()

    def submit(self, message: SteeringInput) -> asyncio.Future[bool] | None:
        if self.closed or self._queue.full():
            return None
        if message.policy is not None:
            self.policy = message.policy
        receipt = asyncio.get_running_loop().create_future()
        request = SteeringRequest(message, receipt)
        self._sequence += 1
        self._queue.put_nowait((0 if message.policy else 1, self._sequence, request))
        self._receipts.add(receipt)
        receipt.add_done_callback(self._receipts.discard)
        return receipt

    async def receive(self) -> SteeringRequest:
        return (await self._queue.get())[2]

    def close(self) -> None:
        self.closed = True
        for receipt in tuple(self._receipts):
            if not receipt.done():
                receipt.set_result(False)
