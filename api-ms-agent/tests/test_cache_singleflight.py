import asyncio

import pytest

from app.core.cache.cache import Cache
from app.core.cache.memory_backend import MemoryCacheBackend
from app.core.cache.singleflight import SingleFlight
from app.core.cache.types import CachePolicy


@pytest.mark.asyncio
async def test_singleflight_factory_runs_once() -> None:
    backend = MemoryCacheBackend(max_entries=10)
    policy = CachePolicy(namespace="test", default_ttl_seconds=60, max_entries=10)
    cache = Cache(backend=backend, policy=policy, _singleflight=SingleFlight())

    calls = 0

    async def factory() -> bytes:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return b"value"

    results = await asyncio.gather(
        cache.get_or_set("k", factory),
        cache.get_or_set("k", factory),
        cache.get_or_set("k", factory),
    )

    assert results == [b"value", b"value", b"value"]
    assert calls == 1
