from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

type CacheNamespace = str


class CacheBackend(Protocol):
    def get(self, key: str) -> bytes | None: ...

    def set(self, key: str, value: bytes, *, ttl_seconds: int) -> None: ...

    def delete(self, key: str) -> None: ...


type CacheGetOrSet = Callable[[], Awaitable[bytes]]


@dataclass(frozen=True, slots=True)
class CachePolicy:
    namespace: CacheNamespace
    default_ttl_seconds: int
    max_entries: int
