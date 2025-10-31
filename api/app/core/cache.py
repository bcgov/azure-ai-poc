"""Caching utilities for performance optimization."""

import asyncio
import hashlib
from collections import OrderedDict
from collections.abc import Callable
from functools import wraps
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class LRUCache:
    """Thread-safe LRU (Least Recently Used) cache implementation."""

    def __init__(self, max_size: int = 1000):
        """Initialize LRU cache with maximum size."""
        self.max_size = max_size
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> Any | None:
        """Get value from cache, return None if not found."""
        async with self._lock:
            if key in self.cache:
                self._hits += 1
                # Move to end to mark as recently used
                self.cache.move_to_end(key)
                return self.cache[key]
            self._misses += 1
            return None

    async def set(self, key: str, value: Any) -> None:
        """Set value in cache, evict oldest if at capacity."""
        async with self._lock:
            if key in self.cache:
                # Update existing value
                self.cache.move_to_end(key)
            else:
                # Add new value
                if len(self.cache) >= self.max_size:
                    # Remove oldest item (first item)
                    self.cache.popitem(last=False)
            self.cache[key] = value

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self.cache.clear()
            self._hits = 0
            self._misses = 0

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.2f}%",
        }


class EmbeddingCache:
    """Specialized cache for embeddings with content-based hashing."""

    def __init__(self, max_size: int = 5000):
        """Initialize embedding cache."""
        self._cache = LRUCache(max_size=max_size)
        self.logger = logger

    def _generate_key(self, text: str) -> str:
        """Generate cache key from text content using SHA-256."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def get_embedding(self, text: str) -> list[float] | None:
        """Get cached embedding for text."""
        key = self._generate_key(text)
        return await self._cache.get(key)

    async def set_embedding(self, text: str, embedding: list[float]) -> None:
        """Cache embedding for text."""
        key = self._generate_key(text)
        await self._cache.set(key, embedding)

    async def get_batch_embeddings(
        self, texts: list[str]
    ) -> tuple[list[list[float] | None], list[str]]:
        """
        Get embeddings for multiple texts.

        Returns:
            Tuple of (embeddings_or_none, uncached_texts)
            - embeddings_or_none: List with cached embeddings or None for cache misses
            - uncached_texts: List of texts that need embedding generation
        """
        results: list[list[float] | None] = []
        uncached: list[str] = []

        for text in texts:
            embedding = await self.get_embedding(text)
            results.append(embedding)
            if embedding is None:
                uncached.append(text)

        cache_hit_rate = (len(texts) - len(uncached)) / len(texts) * 100 if texts else 0
        self.logger.debug(
            f"Batch embedding cache lookup: {cache_hit_rate:.1f}% hit rate "
            f"({len(texts) - len(uncached)}/{len(texts)})"
        )

        return results, uncached

    async def set_batch_embeddings(self, texts: list[str], embeddings: list[list[float]]) -> None:
        """Cache embeddings for multiple texts."""
        if len(texts) != len(embeddings):
            raise ValueError("texts and embeddings must have same length")

        for text, embedding in zip(texts, embeddings, strict=True):
            await self.set_embedding(text, embedding)

    async def clear(self) -> None:
        """Clear all cached embeddings."""
        await self._cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return self._cache.get_stats()


def cache_key_from_args(*args: Any, **kwargs: Any) -> str:
    """Generate cache key from function arguments."""
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_str = "|".join(key_parts)
    return hashlib.sha256(key_str.encode("utf-8")).hexdigest()


def async_lru_cache(max_size: int = 128, ttl_seconds: int | None = None):
    """
    Decorator for async function caching with LRU eviction.

    Args:
        max_size: Maximum number of cached results
        ttl_seconds: Optional time-to-live in seconds (not implemented yet)
    """

    def decorator(func: Callable):
        cache = LRUCache(max_size=max_size)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from arguments
            cache_key = cache_key_from_args(*args, **kwargs)

            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Call function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result)
            return result

        # Add cache management methods
        wrapper.cache = cache  # type: ignore[attr-defined]
        wrapper.cache_clear = cache.clear  # type: ignore[attr-defined]
        wrapper.cache_stats = cache.get_stats  # type: ignore[attr-defined]

        return wrapper

    return decorator


# Global embedding cache instance
_embedding_cache: EmbeddingCache | None = None


def get_embedding_cache() -> EmbeddingCache:
    """Get the global embedding cache instance."""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache(max_size=5000)
    return _embedding_cache
