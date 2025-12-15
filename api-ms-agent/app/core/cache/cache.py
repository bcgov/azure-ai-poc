from __future__ import annotations

from dataclasses import dataclass

from .logging import CacheTimer, log_cache_event
from .singleflight import SingleFlight
from .types import CacheBackend, CacheGetOrSet, CachePolicy


@dataclass(frozen=True, slots=True)
class Cache:
    backend: CacheBackend
    policy: CachePolicy
    _singleflight: SingleFlight

    def get(self, key: str) -> bytes | None:
        timer = CacheTimer()
        value = self.backend.get(key)
        log_cache_event(
            namespace=self.policy.namespace,
            cache_event="hit" if value is not None else "miss",
            duration_ms=timer.elapsed_ms(),
        )
        return value

    def set(self, key: str, value: bytes, *, ttl_seconds: int | None = None) -> None:
        ttl = self.policy.default_ttl_seconds if ttl_seconds is None else ttl_seconds
        timer = CacheTimer()
        self.backend.set(key, value, ttl_seconds=ttl)
        log_cache_event(
            namespace=self.policy.namespace,
            cache_event="set",
            duration_ms=timer.elapsed_ms(),
        )

    def delete(self, key: str) -> None:
        timer = CacheTimer()
        self.backend.delete(key)
        log_cache_event(
            namespace=self.policy.namespace,
            cache_event="delete",
            duration_ms=timer.elapsed_ms(),
        )

    async def get_or_set(
        self,
        key: str,
        factory: CacheGetOrSet,
        *,
        ttl_seconds: int | None = None,
    ) -> bytes:
        existing = self.backend.get(key)
        if existing is not None:
            log_cache_event(namespace=self.policy.namespace, cache_event="hit")
            return existing

        lock = await self._singleflight.acquire(key)
        async with lock:
            try:
                # Double-check after waiting.
                existing2 = self.backend.get(key)
                if existing2 is not None:
                    log_cache_event(namespace=self.policy.namespace, cache_event="hit")
                    return existing2

                timer = CacheTimer()
                value = await factory()
                ttl = self.policy.default_ttl_seconds if ttl_seconds is None else ttl_seconds
                self.backend.set(key, value, ttl_seconds=ttl)
                log_cache_event(
                    namespace=self.policy.namespace,
                    cache_event="set",
                    duration_ms=timer.elapsed_ms(),
                )
                return value
            finally:
                await self._singleflight.release(key)
