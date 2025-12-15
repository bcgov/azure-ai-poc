from __future__ import annotations

from threading import Lock

from app.config import settings

from .cache import Cache
from .memory_backend import MemoryCacheBackend
from .noop_backend import NoOpCacheBackend
from .singleflight import SingleFlight
from .types import CachePolicy

_singleflight = SingleFlight()
_provider_lock = Lock()
_caches: dict[str, Cache] = {}


def get_cache(namespace: str) -> Cache:
    with _provider_lock:
        existing = _caches.get(namespace)
        if existing is not None:
            return existing

        policy = _policy_for_namespace(namespace)
        backend = (
            MemoryCacheBackend(max_entries=policy.max_entries)
            if settings.cache_enabled
            else NoOpCacheBackend()
        )
        cache = Cache(backend=backend, policy=policy, _singleflight=_singleflight)
        _caches[namespace] = cache
        return cache


def _policy_for_namespace(namespace: str) -> CachePolicy:
    max_entries = settings.cache_max_entries

    if namespace == "db":
        ttl = settings.cache_db_ttl_seconds
    elif namespace == "http":
        ttl = settings.cache_http_ttl_seconds
    elif namespace == "embed":
        ttl = settings.cache_embed_ttl_seconds
    elif namespace == "prompt":
        ttl = settings.cache_prompt_ttl_seconds
    elif namespace == "llm":
        ttl = settings.cache_llm_ttl_seconds
    else:
        ttl = settings.cache_default_ttl_seconds

    return CachePolicy(namespace=namespace, default_ttl_seconds=ttl, max_entries=max_entries)
