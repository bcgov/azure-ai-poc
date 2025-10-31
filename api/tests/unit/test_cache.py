"""Unit tests for caching utilities."""

import asyncio

import pytest

from app.core.cache import (
    EmbeddingCache,
    LRUCache,
    async_lru_cache,
    get_embedding_cache,
)


class TestLRUCache:
    """Tests for LRUCache."""

    @pytest.mark.asyncio
    async def test_basic_set_get(self):
        """Test basic cache set and get operations."""
        cache = LRUCache(max_size=3)

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") == "value2"
        assert await cache.get("nonexistent") is None

    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test that least recently used items are evicted."""
        cache = LRUCache(max_size=3)

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        # Access key1 to make it recently used
        await cache.get("key1")

        # Add key4, should evict key2 (least recently used)
        await cache.set("key4", "value4")

        assert await cache.get("key1") == "value1"  # Still present
        assert await cache.get("key2") is None  # Evicted
        assert await cache.get("key3") == "value3"  # Still present
        assert await cache.get("key4") == "value4"  # Newly added

    @pytest.mark.asyncio
    async def test_update_existing_key(self):
        """Test updating an existing key."""
        cache = LRUCache(max_size=3)

        await cache.set("key1", "value1")
        await cache.set("key1", "updated_value")

        assert await cache.get("key1") == "updated_value"

    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clearing the cache."""
        cache = LRUCache(max_size=3)

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        await cache.clear()

        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert cache.get_stats()["size"] == 0

    @pytest.mark.asyncio
    async def test_stats_tracking(self):
        """Test that cache statistics are tracked correctly."""
        cache = LRUCache(max_size=3)

        await cache.set("key1", "value1")

        # Hit
        await cache.get("key1")

        # Miss
        await cache.get("nonexistent")

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert stats["hit_rate"] == "50.00%"  # 1 hit out of 2 total requests

    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Test thread-safe concurrent access."""
        cache = LRUCache(max_size=100)

        async def set_value(key: str, value: str):
            await cache.set(key, value)

        async def get_value(key: str):
            return await cache.get(key)

        # Concurrent sets
        await asyncio.gather(*[set_value(f"key{i}", f"value{i}") for i in range(10)])

        # Concurrent gets
        results = await asyncio.gather(*[get_value(f"key{i}") for i in range(10)])

        assert all(results[i] == f"value{i}" for i in range(10))


class TestEmbeddingCache:
    """Tests for EmbeddingCache."""

    @pytest.mark.asyncio
    async def test_set_and_get_embedding(self):
        """Test setting and getting embeddings."""
        cache = EmbeddingCache(max_size=10)

        text = "Hello, world!"
        embedding = [0.1, 0.2, 0.3]

        await cache.set_embedding(text, embedding)
        result = await cache.get_embedding(text)

        assert result == embedding

    @pytest.mark.asyncio
    async def test_get_nonexistent_embedding(self):
        """Test getting a nonexistent embedding returns None."""
        cache = EmbeddingCache(max_size=10)

        result = await cache.get_embedding("nonexistent text")
        assert result is None

    @pytest.mark.asyncio
    async def test_content_based_hashing(self):
        """Test that embeddings are cached by content, not object identity."""
        cache = EmbeddingCache(max_size=10)

        text1 = "Hello, world!"
        text2 = "Hello, world!"  # Same content, different string object
        embedding = [0.1, 0.2, 0.3]

        await cache.set_embedding(text1, embedding)
        result = await cache.get_embedding(text2)

        assert result == embedding

    @pytest.mark.asyncio
    async def test_batch_operations(self):
        """Test batch embedding operations."""
        cache = EmbeddingCache(max_size=10)

        # Set some embeddings
        await cache.set_embedding("text1", [0.1, 0.2])
        await cache.set_embedding("text2", [0.3, 0.4])

        # Get batch with mix of cached and uncached
        texts = ["text1", "text2", "text3"]
        embeddings, uncached = await cache.get_batch_embeddings(texts)

        assert embeddings == [[0.1, 0.2], [0.3, 0.4], None]
        assert uncached == ["text3"]

    @pytest.mark.asyncio
    async def test_batch_set_embeddings(self):
        """Test batch setting of embeddings."""
        cache = EmbeddingCache(max_size=10)

        texts = ["text1", "text2", "text3"]
        embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]

        await cache.set_batch_embeddings(texts, embeddings)

        # Verify all were set
        result1 = await cache.get_embedding("text1")
        result2 = await cache.get_embedding("text2")
        result3 = await cache.get_embedding("text3")

        assert result1 == [0.1, 0.2]
        assert result2 == [0.3, 0.4]
        assert result3 == [0.5, 0.6]

    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """Test clearing the embedding cache."""
        cache = EmbeddingCache(max_size=10)

        await cache.set_embedding("text1", [0.1, 0.2])
        await cache.set_embedding("text2", [0.3, 0.4])

        await cache.clear()

        assert await cache.get_embedding("text1") is None
        assert await cache.get_embedding("text2") is None


class TestAsyncLRUCacheDecorator:
    """Tests for async_lru_cache decorator."""

    @pytest.mark.asyncio
    async def test_caching_function_results(self):
        """Test that function results are cached."""
        call_count = 0

        @async_lru_cache(max_size=10)
        async def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = await expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        result2 = await expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Should be cached

        result3 = await expensive_function(10)
        assert result3 == 20
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_cache_with_multiple_args(self):
        """Test caching with multiple arguments."""
        call_count = 0

        @async_lru_cache(max_size=10)
        async def add(x: int, y: int) -> int:
            nonlocal call_count
            call_count += 1
            return x + y

        result1 = await add(1, 2)
        assert result1 == 3
        assert call_count == 1

        result2 = await add(1, 2)
        assert result2 == 3
        assert call_count == 1  # Cached

        result3 = await add(2, 3)
        assert result3 == 5
        assert call_count == 2  # New arguments


class TestGetEmbeddingCache:
    """Tests for get_embedding_cache singleton."""

    @pytest.mark.asyncio
    async def test_singleton_behavior(self):
        """Test that get_embedding_cache returns the same instance."""
        cache1 = get_embedding_cache()
        cache2 = get_embedding_cache()

        assert cache1 is cache2

    @pytest.mark.asyncio
    async def test_shared_state(self):
        """Test that the singleton maintains state across calls."""
        cache1 = get_embedding_cache()
        cache2 = get_embedding_cache()

        await cache1.set_embedding("test", [1.0, 2.0])

        result = await cache2.get_embedding("test")
        assert result == [1.0, 2.0]
