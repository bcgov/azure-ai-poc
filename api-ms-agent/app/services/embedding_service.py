"""
Embedding service for generating and storing document embeddings.

This service uses Azure OpenAI to generate embeddings and stores them
in Azure AI Search for vector similarity search.

Storage Architecture:
- Vector embeddings: Azure AI Search (for similarity search)
- Document metadata: Cosmos DB (for user document listing)
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI

from app.config import settings
from app.logger import get_logger
from app.services.azure_search_service import (
    AzureSearchService,
    VectorSearchOptions,
    get_azure_search_service,
)
from app.services.cosmos_db_service import (
    CosmosDbService,
    get_cosmos_db_service,
)

logger = get_logger(__name__)


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
        self._client: AsyncAzureOpenAI | None = None
        self._credential: DefaultAzureCredential | None = None
        self.search = search_service or get_azure_search_service()
        self.cosmos = cosmos_service or get_cosmos_db_service()
        logger.info("EmbeddingService initialized with Azure AI Search backend")

    async def _get_client(self) -> AsyncAzureOpenAI:
        """Get or create the Azure OpenAI client for embeddings."""
        if self._client is None:
            endpoint = settings.azure_openai_embedding_endpoint or settings.azure_openai_endpoint

            if settings.use_managed_identity:
                self._credential = DefaultAzureCredential()
                token_provider = get_bearer_token_provider(
                    self._credential, "https://cognitiveservices.azure.com/.default"
                )
                self._client = AsyncAzureOpenAI(
                    azure_endpoint=endpoint,
                    azure_ad_token_provider=token_provider,
                    api_version=settings.azure_openai_api_version,
                )
                logger.info("Using managed identity for embeddings")
            else:
                self._client = AsyncAzureOpenAI(
                    azure_endpoint=endpoint,
                    api_key=settings.azure_openai_api_key,
                    api_version=settings.azure_openai_api_version,
                )
                logger.info("Using API key for embeddings")
        return self._client

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate an embedding vector for the given text.

        Args:
            text: The text to embed

        Returns:
            The embedding vector
        """
        client = await self._get_client()

        try:
            response = await client.embeddings.create(
                model=settings.azure_openai_embedding_deployment,
                input=text,
            )
            embedding = response.data[0].embedding
            logger.debug(
                "embedding_generated",
                text_length=len(text),
                embedding_dims=len(embedding),
            )
            return embedding
        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            raise

    async def generate_embeddings_batch(
        self, texts: list[str], batch_size: int = 16
    ) -> list[list[float]]:
        """
        Generate embedding vectors for multiple texts in batches.

        This is more efficient than calling generate_embedding repeatedly
        as it reduces API round-trips.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call (Azure OpenAI limit is 16)

        Returns:
            List of embedding vectors in the same order as input texts
        """
        if not texts:
            return []

        client = await self._get_client()
        all_embeddings: list[list[float]] = []

        try:
            # Process in batches
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                response = await client.embeddings.create(
                    model=settings.azure_openai_embedding_deployment,
                    input=batch,
                )
                # Sort by index to maintain order
                sorted_data = sorted(response.data, key=lambda x: x.index)
                batch_embeddings = [item.embedding for item in sorted_data]
                all_embeddings.extend(batch_embeddings)

            logger.debug(
                "batch_embeddings_generated",
                total_texts=len(texts),
                batches=((len(texts) - 1) // batch_size) + 1,
            )
            return all_embeddings

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

    async def index_document(
        self,
        content: str,
        user_id: str,
        document_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> Document:
        """
        Index a document by chunking it and storing embeddings in Azure AI Search.

        Uses batch embedding generation and parallel chunk storage for performance.
        Also stores document metadata in Cosmos DB for listing.

        Args:
            content: The document content
            user_id: The user identifier
            document_id: Optional document ID (generated if not provided)
            metadata: Optional document metadata
            chunk_size: Size of each chunk
            chunk_overlap: Overlap between chunks

        Returns:
            The indexed document
        """
        import asyncio

        doc_id = document_id or str(uuid.uuid4())
        chunks = self._chunk_text(content, chunk_size, chunk_overlap)

        logger.info(
            "indexing_document",
            document_id=doc_id,
            content_length=len(content),
            num_chunks=len(chunks),
        )

        # Generate all embeddings in batches (much faster than sequential)
        embeddings = await self.generate_embeddings_batch(chunks)

        # Store chunks in parallel using asyncio.gather
        chunk_metadata = {**(metadata or {}), "total_chunks": len(chunks)}
        storage_tasks = [
            self.search.store_document_chunk(
                document_id=doc_id,
                user_id=user_id,
                content=chunk,
                embedding=embedding,
                chunk_index=i,
                metadata=chunk_metadata,
            )
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True))
        ]
        await asyncio.gather(*storage_tasks)

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
        query_embedding = await self.generate_embedding(query)

        # Perform vector search in Azure AI Search
        options = VectorSearchOptions(
            user_id=user_id,
            document_id=document_id,
            top_k=top_k,
            min_similarity=min_similarity,
        )

        results = await self.search.vector_search(query_embedding, options)

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
        count = await self.search.delete_document_chunks(document_id, user_id)

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
        """Clean up resources."""
        if self._credential:
            await self._credential.close()
        if self._client:
            await self._client.close()
        logger.info("EmbeddingService closed")


# Global service instance
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the global embedding service."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
