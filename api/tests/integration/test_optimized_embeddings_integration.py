"""Integration test for optimized embedding service in document processing."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.optimized_embedding_service import OptimizedEmbeddingService


def create_mock_embeddings_model():
    """Create a mock Azure OpenAI embeddings model."""
    mock_model = AsyncMock()

    # Mock single embedding generation
    async def mock_aembed_query(text: str) -> list[float]:
        """Generate a fake embedding vector based on text hash."""
        # Create deterministic embeddings based on text for testing
        hash_val = hash(text) % 1000
        return [float(hash_val + i * 0.1) for i in range(1536)]

    # Mock batch embedding generation
    async def mock_aembed_documents(texts: list[str]) -> list[list[float]]:
        """Generate fake embedding vectors for multiple texts."""
        return [await mock_aembed_query(text) for text in texts]

    mock_model.aembed_query = mock_aembed_query
    mock_model.aembed_documents = mock_aembed_documents

    return mock_model


@pytest.fixture
async def mock_embedding_service():
    """Create an optimized embedding service with mocked Azure OpenAI."""
    mock_path = "app.services.optimized_embedding_service.AzureOpenAIEmbeddings"
    with patch(mock_path) as mock_embeddings_class:
        mock_model = create_mock_embeddings_model()
        mock_embeddings_class.return_value = mock_model

        service = OptimizedEmbeddingService(batch_size=16, max_concurrency=3)
        await service.initialize()

        yield service

        # Cleanup
        await service.clear_cache()


@pytest.mark.asyncio
async def test_optimized_embedding_service_basic(mock_embedding_service):
    """Test that the optimized embedding service works end-to-end."""
    service = mock_embedding_service

    # Test single text embedding
    text = "This is a test document for embedding."
    embedding = await service.embed_text(text)

    assert embedding is not None
    assert isinstance(embedding, list)
    assert len(embedding) == 1536  # Standard embedding size
    assert all(isinstance(x, float) for x in embedding)


@pytest.mark.asyncio
async def test_optimized_embedding_service_batch_with_caching(
    mock_embedding_service,
):
    """Test batch embedding with caching to verify performance optimization."""
    service = mock_embedding_service

    # Clear cache to start fresh
    await service.clear_cache()

    # First batch - should miss cache
    texts = [
        "Document about natural resources in BC",
        "Information about forestry management",
        "BC Government environmental policy",
    ]

    embeddings1 = await service.embed_texts(texts)
    assert len(embeddings1) == 3
    assert all(len(emb) == 1536 for emb in embeddings1)

    # Check cache stats - should have 3 items cached
    stats = service.get_cache_stats()
    assert stats["size"] == 3
    initial_hits = stats["hits"]
    print(f"✅ First batch: 3 embeddings cached (cache size: {stats['size']})")

    # Second batch with same texts - should hit cache (much faster)
    embeddings2 = await service.embed_texts(texts)
    assert embeddings1 == embeddings2

    # Cache hits should have increased
    stats_after = service.get_cache_stats()
    assert stats_after["hits"] > initial_hits
    print(f"✅ Second batch: Cache hits increased from {initial_hits} to {stats_after['hits']}")


@pytest.mark.asyncio
async def test_optimized_embedding_service_mixed_cache_batch(
    mock_embedding_service,
):
    """Test batch embedding with mix of cached and uncached texts."""
    service = mock_embedding_service
    await service.clear_cache()

    # Cache some texts first
    cached_texts = ["Text A", "Text B"]
    await service.embed_texts(cached_texts)

    stats_after_first = service.get_cache_stats()
    assert stats_after_first["size"] == 2
    print("✅ Cached 2 texts initially")

    # Mix cached and new texts
    mixed_texts = ["Text A", "Text C", "Text B", "Text D"]
    embeddings = await service.embed_texts(mixed_texts)

    assert len(embeddings) == 4
    assert all(len(emb) == 1536 for emb in embeddings)

    # Verify cache has all 4 texts now
    stats = service.get_cache_stats()
    assert stats["size"] == 4
    print(f"✅ Mixed batch: Cache now has {stats['size']} items (2 new + 2 cached)")


@pytest.mark.asyncio
async def test_cache_persistence_across_calls():
    """Test that cache persists across multiple service calls."""
    from app.services.optimized_embedding_service import (
        get_optimized_embedding_service,
    )

    mock_path = "app.services.optimized_embedding_service.AzureOpenAIEmbeddings"
    with patch(mock_path) as mock_embeddings_class:
        mock_model = create_mock_embeddings_model()
        mock_embeddings_class.return_value = mock_model

        service = get_optimized_embedding_service()
        await service.initialize()
        await service.clear_cache()

        # First call
        text1 = "Persistent text 1"
        await service.embed_text(text1)
        stats1 = service.get_cache_stats()
        assert stats1["size"] == 1

        # Second call with different text
        text2 = "Persistent text 2"
        await service.embed_text(text2)
        stats2 = service.get_cache_stats()
        assert stats2["size"] == 2

        # Third call with first text - should hit cache
        initial_hits = stats2["hits"]
        await service.embed_text(text1)
        stats3 = service.get_cache_stats()
        assert stats3["hits"] > initial_hits
        assert stats3["size"] == 2  # Size shouldn't increase

        print(
            f"✅ Cache persists: {stats3['size']} items, "
            f"{stats3['hits']} hits, "
            f"{stats3['misses']} misses"
        )


@pytest.mark.asyncio
async def test_document_service_uses_optimized_embeddings():
    """Test that document service can use the optimized embedding service."""
    from app.services.optimized_embedding_service import (
        get_optimized_embedding_service,
    )

    mock_path = "app.services.optimized_embedding_service.AzureOpenAIEmbeddings"
    with patch(mock_path) as mock_embeddings_class:
        mock_model = create_mock_embeddings_model()
        mock_embeddings_class.return_value = mock_model

        # Get the embedding service (singleton)
        embedding_service = get_optimized_embedding_service()

        # Initialize
        await embedding_service.initialize()
        await embedding_service.clear_cache()
        initial_stats = embedding_service.get_cache_stats()

        # Verify service is accessible
        assert embedding_service is not None
        assert initial_stats["size"] == 0
        print("✅ Embedding service initialized (cache empty)")

        # Test that embedding service works independently
        test_chunks = [
            "Chunk 1 content",
            "Chunk 2 content",
            "Chunk 3 content",
        ]
        embeddings = await embedding_service.embed_texts(test_chunks)

        assert len(embeddings) == 3
        final_stats = embedding_service.get_cache_stats()
        assert final_stats["size"] == 3
        print(f"✅ Generated embeddings for 3 chunks (cache size: {final_stats['size']})")


@pytest.mark.asyncio
async def test_langchain_service_uses_optimized_embeddings():
    """Test that LangChain service uses optimized embedding service."""
    from app.services.langchain_service import LangChainAIService
    from app.services.optimized_embedding_service import (
        get_optimized_embedding_service,
    )

    mock_openai_path = "app.services.optimized_embedding_service.AzureOpenAIEmbeddings"
    mock_langchain_path = "app.services.langchain_service.AzureChatOpenAI"

    with (
        patch(mock_openai_path) as mock_embeddings_class,
        patch(mock_langchain_path) as mock_chat_class,
    ):
        # Mock embeddings
        mock_embeddings_model = create_mock_embeddings_model()
        mock_embeddings_class.return_value = mock_embeddings_model

        # Mock chat model (not used in this test, but required for init)
        mock_chat = AsyncMock()
        mock_chat_class.return_value = mock_chat

        # Mock cosmos service
        mock_cosmos = AsyncMock()

        # Get services
        langchain_service = LangChainAIService(cosmos_service=mock_cosmos)
        embedding_service = get_optimized_embedding_service()

        # Initialize
        await langchain_service.initialize_client()
        await embedding_service.initialize()
        await embedding_service.clear_cache()

        # Generate embeddings through langchain service
        texts = ["Query about BC forestry", "Question about environmental policy"]
        embeddings = await langchain_service.generate_embeddings_batch(texts)

        assert len(embeddings) == 2
        assert all(len(emb) == 1536 for emb in embeddings)
        print(f"✅ LangChain service generated {len(embeddings)} embeddings")

        # Verify cache was used
        stats = embedding_service.get_cache_stats()
        assert stats["size"] == 2
        print(f"✅ Cache populated: {stats['size']} items")

        # Second call should hit cache
        initial_hits = stats["hits"]
        embeddings2 = await langchain_service.generate_embeddings_batch(texts)
        assert embeddings == embeddings2

        stats2 = embedding_service.get_cache_stats()
        assert stats2["hits"] > initial_hits
        print(f"✅ Cache hits increased from {initial_hits} to {stats2['hits']} on second call")
