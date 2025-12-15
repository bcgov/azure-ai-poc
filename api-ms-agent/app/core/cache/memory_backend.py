from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock

from .types import CacheBackend


@dataclass(frozen=True, slots=True)
class _Entry:
    value: bytes
    expires_at_monotonic: float | None


class MemoryCacheBackend(CacheBackend):
    def __init__(self, *, max_entries: int, namespace: str | None = None) -> None:
        if max_entries <= 0:
            raise ValueError("max_entries must be > 0")
        self._max_entries = max_entries
        self._namespace = namespace
        self._lock = Lock()
        self._entries: OrderedDict[str, _Entry] = OrderedDict()

    def get(self, key: str) -> bytes | None:
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at_monotonic is not None and entry.expires_at_monotonic <= now:
                self._entries.pop(key, None)
                return None
            self._entries.move_to_end(key, last=True)
            return entry.value

    def set(self, key: str, value: bytes, *, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            # Treat non-positive TTL as immediate expiry / no-op
            self.delete(key)
            return

        expires_at = time.monotonic() + float(ttl_seconds)
        with self._lock:
            self._entries[key] = _Entry(value=value, expires_at_monotonic=expires_at)
            self._entries.move_to_end(key, last=True)
            self._evict_expired_locked(now=time.monotonic())
            self._evict_lru_locked()

    def delete(self, key: str) -> None:
        with self._lock:
            self._entries.pop(key, None)

    def _evict_expired_locked(self, *, now: float) -> None:
        # OrderedDict is LRU ordered; expired entries can be anywhere, but we keep this O(n)
        # and rely on max_entries to be bounded.
        expired_keys: list[str] = []
        for k, entry in self._entries.items():
            if entry.expires_at_monotonic is not None and entry.expires_at_monotonic <= now:
                expired_keys.append(k)
        for k in expired_keys:
            self._entries.pop(k, None)

        if expired_keys and self._namespace:
            from app.core.cache.logging import log_cache_event

            log_cache_event(
                namespace=self._namespace,
                cache_event="evict",
                detail=f"reason=expired count={len(expired_keys)}",
            )

    def _evict_lru_locked(self) -> None:
        evicted = 0
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)
            evicted += 1

        if evicted and self._namespace:
            from app.core.cache.logging import log_cache_event

            log_cache_event(
                namespace=self._namespace,
                cache_event="evict",
                detail=f"reason=lru count={evicted}",
            )
