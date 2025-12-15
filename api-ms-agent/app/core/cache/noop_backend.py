from __future__ import annotations

from .types import CacheBackend


class NoOpCacheBackend(CacheBackend):
    def get(self, key: str) -> bytes | None:
        return None

    def set(self, key: str, value: bytes, *, ttl_seconds: int) -> None:
        pass

    def delete(self, key: str) -> None:
        pass
