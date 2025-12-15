"""Embedding service for generating and storing document embeddings.

This service uses Azure OpenAI to generate embeddings and stores them
in Azure AI Search for vector similarity search.

Storage Architecture:
- Vector embeddings: Azure AI Search (for similarity search)
- Document metadata: Cosmos DB (for user document listing)
"""

from __future__ import annotations

import asyncio
import json
import random
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.config import settings
from app.core.cache.keys import canonical_json, hash_text
from app.core.cache.provider import get_cache
from app.logger import get_logger
from app.services.azure_search_service import (
    AzureSearchService,
    DocumentChunk,
    VectorSearchOptions,
    get_azure_search_service,
)
from app.services.cosmos_db_service import (
    CosmosDbService,
    get_cosmos_db_service,
)
from app.services.document_intelligence_service import ParagraphWithPage
from app.services.openai_clients import get_embedding_client

logger = get_logger(__name__)


def _embedding_cache_key(*, deployment: str, user_id: str | None, text: str) -> str:
    payload = {
        "deployment": deployment,
        "user_id": user_id or "",
        "text_hash": hash_text(text),
    }
    return f"embed:{hash_text(canonical_json(payload))}"


@dataclass
class ChunkWithPage:
    """A text chunk with its associated page number."""

    content: str
    page_number: int


@dataclass
class Document:
    """A document with optional embeddings."""

    id: str
    content: str
    user_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    chunks: list[str] = field(default_factory=list)


@dataclass
class SearchResult:
    """Result from vector similarity search."""

    chunk_id: str
    document_id: str
    content: str
    similarity: float
    metadata: dict[str, Any] = field(default_factory=dict)


class EmbeddingService:
    """Service for generating embeddings and performing vector search."""

    # Default chunk settings
    DEFAULT_CHUNK_SIZE = 1000
    DEFAULT_CHUNK_OVERLAP = 200

    def __init__(
        self,
        search_service: AzureSearchService | None = None,
        cosmos_service: CosmosDbService | None = None,
    ) -> None:
        """
        Initialize the embedding service.

        Args:
            search_service: Optional Azure Search service instance for vector operations
            cosmos_service: Optional Cosmos DB service instance for metadata
        """
        # NOTE: Do not name this attribute `search` since this class also exposes a `search()`
        # method for consumers (documents router). Keeping these distinct avoids attribute/method
        # name collisions.
        self.search_service = search_service or get_azure_search_service()
        self.cosmos = cosmos_service or get_cosmos_db_service()
        logger.info("EmbeddingService initialized with Azure AI Search backend")

    @staticmethod
    def _is_retryable_embedding_error(exc: Exception) -> bool:
        """Return True if the embedding call error is likely transient."""
        try:
            from openai import (
                APIConnectionError,
                APIStatusError,
                APITimeoutError,
                InternalServerError,
                RateLimitError,
            )

            if isinstance(
                exc,
                (
                    RateLimitError,
                    APIConnectionError,
                    APITimeoutError,
                    InternalServerError,
                ),
            ):
                return True

            if isinstance(exc, APIStatusError):
                return getattr(exc, "status_code", None) in {429, 500, 502, 503, 504}
        except Exception:
            # Fallback for environments where OpenAI exception classes differ.
            pass

        msg = str(exc).lower()
        return any(
            token in msg
            for token in [
                "rate limit",
                "timeout",
                "timed out",
                "temporarily unavailable",
                "connection reset",
                "service unavailable",
                "502",
                "503",
                "504",
                "429",
            ]
        )

    async def _embeddings_create_with_retry(self, client, *, input_text) -> Any:
        """Call Azure OpenAI embeddings with bounded retries + timeout."""
        max_retries = max(0, int(getattr(settings, "embedding_max_retries", 3)))
        timeout_s = float(
            getattr(
                settings,
                "embedding_request_timeout_seconds",
                settings.llm_request_timeout_seconds,
            )
        )
        base_delay = float(getattr(settings, "embedding_retry_base_seconds", 0.5))

        for attempt in range(max_retries + 1):
            try:
                return await asyncio.wait_for(
                    client.embeddings.create(
                        model=settings.azure_openai_embedding_deployment,
                        input=input_text,
                    ),
                    timeout=timeout_s,
                )
            except Exception as exc:
                if attempt >= max_retries or not self._is_retryable_embedding_error(exc):
                    logger.error(
                        "embedding_request_failed",
                        attempt=attempt,
                        max_retries=max_retries,
                        error=str(exc),
                    )
                    raise

                # Exponential backoff with jitter
                delay = base_delay * (2**attempt)
                delay = delay * (0.5 + random.random())
                delay = min(delay, 10.0)

                logger.warning(
                    "embedding_request_retry",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    delay_seconds=f"{delay:.2f}",
                    error=str(exc),
                )
                await asyncio.sleep(delay)

    async def generate_embedding(self, text: str, *, user_id: str | None = None) -> list[float]:
        """
        Generate an embedding vector for the given text.

        Args:
            text: The text to embed

        Returns:
            The embedding vector
        """
        cache = get_cache("embed")
        cache_key = _embedding_cache_key(
            deployment=settings.azure_openai_embedding_deployment,
            user_id=user_id,
            text=text,
        )

        cached = cache.get(cache_key)
        if cached is not None:
            try:
                embedding = json.loads(cached.decode("utf-8"))
                if isinstance(embedding, list):
                    return embedding
            except Exception:
                pass

        client = await get_embedding_client()

        try:
            response = await self._embeddings_create_with_retry(client, input_text=text)
            embedding = response.data[0].embedding
            logger.debug(
                "embedding_generated",
                text_length=len(text),
                embedding_dims=len(embedding),
            )

            try:
                cache.set(cache_key, canonical_json(embedding).encode("utf-8"))
            except Exception:
                pass

            return embedding
        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            raise

    async def generate_embeddings_batch(
        self,
        texts: list[str],
        batch_size: int = 2048,
        max_concurrent: int = 4,
        *,
        user_id: str | None = None,
    ) -> list[list[float]]:
        """
        Generate embedding vectors for multiple texts in parallel batches.

        This is more efficient than calling generate_embedding repeatedly
        as it reduces API round-trips and processes batches concurrently.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call
                (Azure OpenAI supports up to 2048 for text-embedding-3-large)
            max_concurrent: Maximum number of concurrent API calls

        Returns:
            List of embedding vectors in the same order as input texts
        """
        if not texts:
            return []

        cache = get_cache("embed")
        deployment = settings.azure_openai_embedding_deployment

        results: list[list[float] | None] = [None] * len(texts)
        missing: list[tuple[int, str]] = []
        for i, text in enumerate(texts):
            cache_key = _embedding_cache_key(deployment=deployment, user_id=user_id, text=text)
            cached = cache.get(cache_key)
            if cached is not None:
                try:
                    embedding = json.loads(cached.decode("utf-8"))
                    if isinstance(embedding, list):
                        results[i] = embedding
                        continue
                except Exception:
                    pass
            missing.append((i, text))

        if not missing:
            # All hits.
            return [r for r in results if r is not None]

        client = await get_embedding_client()

        async def process_batch(batch: list[str]) -> list[list[float]]:
            """Process a single batch of texts."""
            response = await self._embeddings_create_with_retry(client, input_text=batch)
            # Sort by index to maintain order
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [item.embedding for item in sorted_data]

        try:
            missing_texts = [t for _, t in missing]
            batches = [
                missing_texts[i : i + batch_size] for i in range(0, len(missing_texts), batch_size)
            ]

            # Process batches concurrently with semaphore to limit parallel requests
            semaphore = asyncio.Semaphore(max_concurrent)

            async def limited_process(batch: list[str]) -> list[list[float]]:
                async with semaphore:
                    return await process_batch(batch)

            # Run all batches concurrently
            batch_results = await asyncio.gather(*[limited_process(b) for b in batches])

            # Flatten results maintaining order
            all_embeddings = [emb for batch_embs in batch_results for emb in batch_embs]

            # Write back into original order + populate cache.
            for (index, text), embedding in zip(missing, all_embeddings, strict=True):
                results[index] = embedding
                try:
                    cache_key = _embedding_cache_key(
                        deployment=deployment,
                        user_id=user_id,
                        text=text,
                    )
                    cache.set(cache_key, canonical_json(embedding).encode("utf-8"))
                except Exception:
                    pass

            logger.debug(
                "batch_embeddings_generated",
                total_texts=len(texts),
                batches=len(batches),
                concurrent=min(max_concurrent, len(batches)),
            )
            final: list[list[float]] = []
            for r in results:
                if r is None:
                    raise RuntimeError("Embedding batch result missing entry")
                final.append(r)
            return final

        except Exception as e:
            logger.error("batch_embedding_generation_failed", error=str(e))
            raise

    def _chunk_text(
        self,
        text: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> list[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: The text to chunk
            chunk_size: Maximum size of each chunk
            overlap: Number of characters to overlap between chunks

        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at a sentence boundary
            if end < len(text):
                # Look for sentence endings
                for sep in [". ", ".\n", "! ", "? ", "\n\n"]:
                    last_sep = text[start:end].rfind(sep)
                    if last_sep > chunk_size // 2:
                        end = start + last_sep + len(sep)
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap

        logger.debug("text_chunked", original_length=len(text), num_chunks=len(chunks))
        return chunks

    def _chunk_paragraphs_with_pages(
        self,
        paragraphs: list[ParagraphWithPage],
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> list[ChunkWithPage]:
        """
        Chunk paragraphs while preserving page numbers.

        Combines paragraphs into chunks up to chunk_size, tracking the page number
        of the first paragraph in each chunk for citation purposes.

        Args:
            paragraphs: List of paragraphs with page numbers
            chunk_size: Maximum size of each chunk
            overlap: Number of characters to overlap between chunks

        Returns:
            List of chunks with page numbers
        """
        if not paragraphs:
            return []

        chunks_with_pages: list[ChunkWithPage] = []
        current_chunk = ""
        current_page = paragraphs[0].page_number if paragraphs else 1

        for para in paragraphs:
            # If adding this paragraph exceeds chunk_size, finalize current chunk
            if current_chunk and len(current_chunk) + len(para.content) + 2 > chunk_size:
                if current_chunk.strip():
                    chunks_with_pages.append(
                        ChunkWithPage(content=current_chunk.strip(), page_number=current_page)
                    )
                # Start new chunk with overlap from the end of the current chunk
                if overlap > 0 and len(current_chunk) > overlap:
                    current_chunk = current_chunk[-overlap:] + "\n\n" + para.content
                else:
                    current_chunk = para.content
                current_page = para.page_number
            else:
                # Append paragraph to current chunk
                if not current_chunk:
                    current_page = para.page_number
                current_chunk = (current_chunk + "\n\n" + para.content).strip()

        # Don't forget the last chunk
        if current_chunk.strip():
            chunks_with_pages.append(
                ChunkWithPage(content=current_chunk.strip(), page_number=current_page)
            )

        logger.debug(
            "paragraphs_chunked_with_pages",
            num_paragraphs=len(paragraphs),
            num_chunks=len(chunks_with_pages),
        )
        return chunks_with_pages

    async def index_document(
        self,
        content: str,
        user_id: str,
        document_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        paragraphs_with_pages: list[ParagraphWithPage] | None = None,
    ) -> Document:
        """
        Index a document by chunking it and storing embeddings in Azure AI Search.

        Uses batch embedding generation and bulk chunk storage for performance.
        Also stores document metadata in Cosmos DB for listing.

        Args:
            content: The document content
            user_id: The user identifier
            document_id: Optional document ID (generated if not provided)
            metadata: Optional document metadata
            chunk_size: Size of each chunk
            chunk_overlap: Overlap between chunks
            paragraphs_with_pages: Optional paragraphs with page numbers for page-aware chunking

        Returns:
            The indexed document
        """
        doc_id = document_id or str(uuid.uuid4())

        # Use page-aware chunking if paragraphs with pages are provided
        chunks_with_pages: list[ChunkWithPage] | None = None
        if paragraphs_with_pages:
            chunks_with_pages = self._chunk_paragraphs_with_pages(
                paragraphs_with_pages, chunk_size, chunk_overlap
            )
            chunks = [c.content for c in chunks_with_pages]
        else:
            chunks = self._chunk_text(content, chunk_size, chunk_overlap)

        logger.info(
            "indexing_document",
            document_id=doc_id,
            content_length=len(content),
            num_chunks=len(chunks),
            has_page_info=chunks_with_pages is not None,
        )

        # Generate all embeddings in batches (batch_size=2048 for Azure OpenAI)
        embeddings = await self.generate_embeddings_batch(chunks, user_id=user_id)

        # Build DocumentChunk objects for bulk upload
        now = datetime.now(UTC)
        chunk_metadata = {**(metadata or {}), "total_chunks": len(chunks)}

        if chunks_with_pages:
            # Use page numbers from chunking
            document_chunks = [
                DocumentChunk(
                    id=f"{doc_id}_chunk_{i}",
                    document_id=doc_id,
                    user_id=user_id,
                    content=chunk_with_page.content,
                    embedding=embedding,
                    chunk_index=i,
                    page_number=chunk_with_page.page_number,
                    metadata=chunk_metadata,
                    created_at=now,
                )
                for i, (chunk_with_page, embedding) in enumerate(
                    zip(chunks_with_pages, embeddings, strict=True)
                )
            ]
        else:
            # No page info available
            document_chunks = [
                DocumentChunk(
                    id=f"{doc_id}_chunk_{i}",
                    document_id=doc_id,
                    user_id=user_id,
                    content=chunk,
                    embedding=embedding,
                    chunk_index=i,
                    page_number=None,
                    metadata=chunk_metadata,
                    created_at=now,
                )
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True))
            ]

        # Bulk upload chunks to Azure Search (batched at 1000 per request)
        await self.search_service.bulk_store_chunks(document_chunks)

        # Store document metadata in Cosmos DB
        await self.cosmos.save_document_metadata(
            document_id=doc_id,
            user_id=user_id,
            title=(metadata or {}).get("title") or f"Document {doc_id[:8]}...",
            filename=(metadata or {}).get("filename"),
            content_type=(metadata or {}).get("content_type"),
            chunk_count=len(chunks),
            pages=(metadata or {}).get("pages"),
            metadata=metadata,
        )

        document = Document(
            id=doc_id,
            content=content,
            user_id=user_id,
            metadata=metadata or {},
            chunks=chunks,
        )

        logger.info(
            "document_indexed",
            document_id=doc_id,
            chunks_stored=len(chunks),
        )

        return document

    async def search(
        self,
        query: str,
        user_id: str | None = None,
        document_id: str | None = None,
        top_k: int = 5,
        min_similarity: float = 0.0,
    ) -> list[SearchResult]:
        """
        Perform vector similarity search using Azure AI Search.

        Args:
            query: The search query
            user_id: Optional user filter
            document_id: Optional document filter
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of search results ordered by similarity
        """
        # Generate embedding for the query
        query_embedding = await self.generate_embedding(query, user_id=user_id)

        # Perform vector search in Azure AI Search
        options = VectorSearchOptions(
            user_id=user_id,
            document_id=document_id,
            top_k=top_k,
            min_similarity=min_similarity,
        )

        results = await self.search_service.vector_search(query_embedding, options)

        search_results = [
            SearchResult(
                chunk_id=r["id"],
                document_id=r["document_id"],
                content=r["content"],
                similarity=r.get("similarity", 0.0),
                metadata=r.get("metadata", {}),
            )
            for r in results
        ]

        logger.info(
            "search_completed",
            query_length=len(query),
            results=len(search_results),
            top_k=top_k,
        )

        return search_results

    async def delete_document(self, document_id: str, user_id: str) -> int:
        """
        Delete a document and all its chunks.

        Args:
            document_id: The document identifier
            user_id: The user identifier

        Returns:
            Number of chunks deleted
        """
        # Delete chunks from Azure AI Search
        count = await self.search_service.delete_document_chunks(document_id, user_id)

        # Delete metadata from Cosmos DB
        await self.cosmos.delete_document_metadata(document_id, user_id)

        logger.info(
            "document_deleted",
            document_id=document_id,
            chunks_deleted=count,
        )
        return count

    async def list_documents(self, user_id: str, limit: int = 50) -> list[dict]:
        """
        List documents for a user.

        Uses Cosmos DB for fast metadata retrieval.

        Args:
            user_id: The user identifier
            limit: Maximum number of documents to return

        Returns:
            List of document metadata
        """
        documents = await self.cosmos.list_user_documents(user_id, limit)
        return documents

    async def close(self) -> None:
        """Clean up resources. Clients are managed by openai_clients module."""
        logger.info("EmbeddingService closed")


# Global service instance
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the global embedding service."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
