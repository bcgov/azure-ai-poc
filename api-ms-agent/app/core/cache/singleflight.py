from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass(slots=True)
class _Gate:
    lock: asyncio.Lock
    refcount: int


class SingleFlight:
    def __init__(self) -> None:
        self._gates: dict[str, _Gate] = {}
        self._map_lock = asyncio.Lock()

    async def acquire(self, key: str) -> asyncio.Lock:
        async with self._map_lock:
            gate = self._gates.get(key)
            if gate is None:
                gate = _Gate(lock=asyncio.Lock(), refcount=0)
                self._gates[key] = gate
            gate.refcount += 1
            return gate.lock

    async def release(self, key: str) -> None:
        async with self._map_lock:
            gate = self._gates.get(key)
            if gate is None:
                return
            gate.refcount -= 1
            if gate.refcount <= 0:
                self._gates.pop(key, None)
