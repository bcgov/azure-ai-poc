"""Optimized embedding service with batching and caching."""

import asyncio
from typing import Any

from langchain_openai import AzureOpenAIEmbeddings

from app.core.cache import get_embedding_cache
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class OptimizedEmbeddingService:
    """Optimized embedding service with automatic batching and caching."""

    def __init__(self, batch_size: int = 16, max_concurrency: int = 3):
        """
        Initialize optimized embedding service.

        Args:
            batch_size: Number of texts to process in each batch (Azure OpenAI recommends 16)
            max_concurrency: Maximum concurrent batch requests
        """
        self.batch_size = batch_size
        self.max_concurrency = max_concurrency
        self.cache = get_embedding_cache()
        self.embeddings_model: AzureOpenAIEmbeddings | None = None
        self._initialized = False
        self._init_lock = asyncio.Lock()
        self.logger = logger

    async def initialize(self) -> None:
        """Initialize the embeddings model (lazy initialization)."""
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return

            try:
                self.embeddings_model = AzureOpenAIEmbeddings(
                    azure_endpoint=settings.AZURE_OPENAI_EMBEDDING_ENDPOINT,
                    azure_deployment=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME,
                    api_version="2024-12-01-preview",
                    api_key=settings.AZURE_OPENAI_API_KEY,
                    # Optimize for batch processing
                    chunk_size=self.batch_size,
                    max_retries=3,
                    timeout=30.0,
                )
                self._initialized = True
                self.logger.info("Optimized embedding service initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize embeddings model: {e}")
                raise

    async def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text with caching.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        # Check cache first
        cached = await self.cache.get_embedding(text)
        if cached is not None:
            return cached

        # Generate new embedding
        await self.initialize()
        if self.embeddings_model is None:
            raise RuntimeError("Embeddings model not initialized")

        embedding = await self.embeddings_model.aembed_query(text)

        # Cache the result
        await self.cache.set_embedding(text, embedding)

        return embedding

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts with batching and caching.

        This method:
        1. Checks cache for existing embeddings
        2. Batches uncached texts for efficient processing
        3. Processes batches with concurrency control
        4. Caches new embeddings
        5. Returns all embeddings in original order

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors in same order as input texts
        """
        if not texts:
            return []

        # Check cache for all texts
        cached_embeddings, uncached_texts = await self.cache.get_batch_embeddings(texts)

        # If everything was cached, return immediately
        if not uncached_texts:
            return [e for e in cached_embeddings if e is not None]

        # Initialize model if needed
        await self.initialize()
        if self.embeddings_model is None:
            raise RuntimeError("Embeddings model not initialized")

        self.logger.info(
            f"Generating embeddings for {len(uncached_texts)} texts "
            f"({len(texts) - len(uncached_texts)} cached)"
        )

        # Process uncached texts in batches
        async def process_batch(batch: list[str]) -> list[list[float]]:
            """Process a batch of texts and return embeddings."""
            try:
                # Use LangChain's embed_documents which handles batching internally
                batch_embeddings = await self.embeddings_model.aembed_documents(batch)
                return batch_embeddings
            except Exception as e:
                self.logger.error(f"Error generating batch embeddings: {e}")
                raise

        # Generate embeddings for uncached texts using simple batching
        # Split into batches
        batches = [
            uncached_texts[i : i + self.batch_size]
            for i in range(0, len(uncached_texts), self.batch_size)
        ]

        # Process batches with concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def process_batch_with_semaphore(batch: list[str]) -> list[list[float]]:
            async with semaphore:
                return await process_batch(batch)

        # Process all batches concurrently
        batch_results = await asyncio.gather(
            *[process_batch_with_semaphore(batch) for batch in batches]
        )

        # Flatten results
        new_embeddings: list[list[float]] = []
        for batch_result in batch_results:
            new_embeddings.extend(batch_result)

        # Cache new embeddings
        await self.cache.set_batch_embeddings(uncached_texts, new_embeddings)

        # Reconstruct full results list in original order
        uncached_iter = iter(new_embeddings)
        results = []
        for cached_emb in cached_embeddings:
            if cached_emb is not None:
                results.append(cached_emb)
            else:
                results.append(next(uncached_iter))

        return results

    def get_cache_stats(self) -> dict[str, Any]:
        """Get embedding cache statistics."""
        return self.cache.get_stats()

    async def clear_cache(self) -> None:
        """Clear the embedding cache."""
        await self.cache._cache.clear()
        self.logger.info("Embedding cache cleared")


# Singleton instance
_embedding_service: OptimizedEmbeddingService | None = None


def get_optimized_embedding_service() -> OptimizedEmbeddingService:
    """Get the singleton optimized embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = OptimizedEmbeddingService(
            batch_size=16,  # Azure OpenAI recommendation
            max_concurrency=3,  # Conservative concurrency
        )
    return _embedding_service
