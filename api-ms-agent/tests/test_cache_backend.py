import time

from app.core.cache.memory_backend import MemoryCacheBackend


def test_memory_cache_ttl_expiry() -> None:
    cache = MemoryCacheBackend(max_entries=10)
    cache.set("k", b"v", ttl_seconds=1)
    assert cache.get("k") == b"v"

    time.sleep(1.05)
    assert cache.get("k") is None


def test_memory_cache_lru_eviction() -> None:
    cache = MemoryCacheBackend(max_entries=2)

    cache.set("a", b"1", ttl_seconds=60)
    cache.set("b", b"2", ttl_seconds=60)

    # Touch 'a' so it becomes most-recently-used.
    assert cache.get("a") == b"1"

    # Adding 'c' should evict LRU ('b').
    cache.set("c", b"3", ttl_seconds=60)

    assert cache.get("b") is None
    assert cache.get("a") == b"1"
    assert cache.get("c") == b"3"
