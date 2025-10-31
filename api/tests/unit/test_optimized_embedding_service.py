"""Unit tests for optimized embedding service."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.optimized_embedding_service import (
    OptimizedEmbeddingService,
    get_optimized_embedding_service,
)


class TestOptimizedEmbeddingService:
    """Tests for OptimizedEmbeddingService class."""

    @pytest.fixture
    def service(self):
        """Create a service instance for testing."""
        return OptimizedEmbeddingService(batch_size=2, max_concurrency=2)

    @pytest.fixture
    def mock_cache(self):
        """Create a mock embedding cache."""
        cache = AsyncMock()
        cache.get_embedding = AsyncMock(return_value=None)
        cache.set_embedding = AsyncMock()
        cache.get_batch_embeddings = AsyncMock(
            return_value=(
                [None, None, None],  # All embeddings are None (not cached)
                ["text1", "text2", "text3"],  # All texts are uncached
            )
        )
        cache.set_batch_embeddings = AsyncMock()
        cache.get_stats = MagicMock(
            return_value={"size": 0, "hits": 0, "misses": 0, "hit_rate": 0.0}
        )
        return cache

    @pytest.fixture
    def mock_embeddings_model(self):
        """Create a mock embeddings model."""
        model = AsyncMock()
        model.aembed_query = AsyncMock(return_value=[0.1, 0.2, 0.3])
        model.aembed_documents = AsyncMock(return_value=[[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]])
        return model

    @pytest.mark.asyncio
    async def test_initialization(self, service, mock_embeddings_model):
        """Test service initialization."""
        assert not service._initialized

        with patch(
            "app.services.optimized_embedding_service.AzureOpenAIEmbeddings",
            return_value=mock_embeddings_model,
        ):
            await service.initialize()

        assert service._initialized
        assert service.embeddings_model is not None

    @pytest.mark.asyncio
    async def test_initialization_idempotent(self, service, mock_embeddings_model):
        """Test that multiple initialization calls don't cause issues."""
        with patch(
            "app.services.optimized_embedding_service.AzureOpenAIEmbeddings",
            return_value=mock_embeddings_model,
        ):
            await service.initialize()
            await service.initialize()  # Second call

        # Should only initialize once
        assert service._initialized

    @pytest.mark.asyncio
    async def test_embed_text_with_cache_miss(self, service, mock_cache, mock_embeddings_model):
        """Test embedding a single text with cache miss."""
        service.cache = mock_cache
        service.embeddings_model = mock_embeddings_model
        service._initialized = True

        result = await service.embed_text("test text")

        assert result == [0.1, 0.2, 0.3]
        mock_cache.get_embedding.assert_called_once_with("test text")
        mock_embeddings_model.aembed_query.assert_called_once_with("test text")
        mock_cache.set_embedding.assert_called_once_with("test text", [0.1, 0.2, 0.3])

    @pytest.mark.asyncio
    async def test_embed_text_with_cache_hit(self, service, mock_cache):
        """Test embedding a single text with cache hit."""
        service.cache = mock_cache
        service._initialized = True

        # Set cache to return a cached embedding
        mock_cache.get_embedding = AsyncMock(return_value=[0.5, 0.6, 0.7])

        result = await service.embed_text("test text")

        assert result == [0.5, 0.6, 0.7]
        mock_cache.get_embedding.assert_called_once_with("test text")
        # Should not call set_embedding since it was cached
        mock_cache.set_embedding.assert_not_called()

    @pytest.mark.asyncio
    async def test_embed_texts_empty(self, service):
        """Test embedding empty list."""
        result = await service.embed_texts([])
        assert result == []

    @pytest.mark.asyncio
    async def test_embed_texts_all_cached(self, service, mock_cache):
        """Test embedding texts when all are cached."""
        service.cache = mock_cache
        service._initialized = True

        # Mock all texts as cached
        mock_cache.get_batch_embeddings = AsyncMock(
            return_value=(
                [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]],  # All cached
                [],  # No uncached texts
            )
        )

        result = await service.embed_texts(["text1", "text2", "text3"])

        assert result == [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        mock_cache.get_batch_embeddings.assert_called_once_with(["text1", "text2", "text3"])

    @pytest.mark.asyncio
    async def test_embed_texts_with_batching(self, service, mock_cache, mock_embeddings_model):
        """Test embedding texts with batching."""
        service.cache = mock_cache
        service.embeddings_model = mock_embeddings_model
        service._initialized = True

        # Mock some cached, some uncached
        mock_cache.get_batch_embeddings = AsyncMock(
            return_value=(
                [[0.1, 0.2], None, [0.5, 0.6]],  # text1 and text3 cached
                ["text2"],  # text2 not cached
            )
        )

        mock_embeddings_model.aembed_documents = AsyncMock(
            return_value=[[0.3, 0.4]]  # Embedding for text2
        )

        result = await service.embed_texts(["text1", "text2", "text3"])

        assert result == [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        mock_cache.get_batch_embeddings.assert_called_once()
        mock_cache.set_batch_embeddings.assert_called_once_with(["text2"], [[0.3, 0.4]])

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, service, mock_cache):
        """Test getting cache statistics."""
        service.cache = mock_cache

        stats = service.get_cache_stats()

        assert stats == {"size": 0, "hits": 0, "misses": 0, "hit_rate": 0.0}
        mock_cache.get_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_cache(self, service, mock_cache):
        """Test clearing the cache."""
        service.cache = mock_cache
        service.cache._cache = AsyncMock()
        service.cache._cache.clear = AsyncMock()

        await service.clear_cache()

        service.cache._cache.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_embed_texts(self, service, mock_cache, mock_embeddings_model):
        """Test concurrent embedding requests."""
        service.cache = mock_cache
        service.embeddings_model = mock_embeddings_model
        service._initialized = True

        # Mock cache to return no cached embeddings
        async def mock_get_batch(texts):
            return ([None] * len(texts), texts)

        mock_cache.get_batch_embeddings = AsyncMock(side_effect=mock_get_batch)

        # Mock embeddings - return appropriate embeddings based on input
        async def mock_embed(texts):
            return [[0.1, 0.2] for _ in texts]

        mock_embeddings_model.aembed_documents = AsyncMock(side_effect=mock_embed)

        # Run multiple embedding requests concurrently
        results = await asyncio.gather(
            service.embed_texts(["text1", "text2"]),
            service.embed_texts(["text3", "text4"]),
        )

        assert len(results) == 2
        assert len(results[0]) == 2
        assert len(results[1]) == 2


class TestGetOptimizedEmbeddingService:
    """Tests for get_optimized_embedding_service singleton."""

    def test_singleton_pattern(self):
        """Test that get_optimized_embedding_service returns the same instance."""
        service1 = get_optimized_embedding_service()
        service2 = get_optimized_embedding_service()

        assert service1 is service2

    def test_default_configuration(self):
        """Test that singleton has correct default configuration."""
        service = get_optimized_embedding_service()

        assert service.batch_size == 16
        assert service.max_concurrency == 3
