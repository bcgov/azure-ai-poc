import asyncio

import pytest

from app.core.cache.cache import Cache
from app.core.cache.memory_backend import MemoryCacheBackend
from app.core.cache.singleflight import SingleFlight
from app.core.cache.types import CachePolicy


@pytest.mark.asyncio
async def test_cache_get_or_set_singleflight_under_load() -> None:
    backend = MemoryCacheBackend(max_entries=1000)
    policy = CachePolicy(namespace="load", default_ttl_seconds=60, max_entries=1000)
    cache = Cache(backend=backend, policy=policy, _singleflight=SingleFlight())

    calls = 0

    async def factory() -> bytes:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return b"value"

    results = await asyncio.gather(*[cache.get_or_set("k", factory) for _ in range(50)])

    assert results == [b"value"] * 50
    assert calls == 1
