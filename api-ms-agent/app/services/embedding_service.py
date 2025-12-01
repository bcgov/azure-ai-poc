"""
Embedding service for generating and storing document embeddings.

This service uses Azure OpenAI to generate embeddings and stores them
in Cosmos DB for vector similarity search.
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI

from app.config import settings
from app.logger import get_logger
from app.services.cosmos_db_service import (
    CosmosDbService,
    VectorSearchOptions,
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
        cosmos_service: CosmosDbService | None = None,
    ) -> None:
        """
        Initialize the embedding service.

        Args:
            cosmos_service: Optional Cosmos DB service instance
        """
        self._client: AsyncAzureOpenAI | None = None
        self._credential: DefaultAzureCredential | None = None
        self.cosmos = cosmos_service or get_cosmos_db_service()
        logger.info("EmbeddingService initialized")

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
        Index a document by chunking it and storing embeddings in Cosmos DB.

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
        doc_id = document_id or str(uuid.uuid4())
        chunks = self._chunk_text(content, chunk_size, chunk_overlap)

        logger.info(
            "indexing_document",
            document_id=doc_id,
            content_length=len(content),
            num_chunks=len(chunks),
        )

        # Generate embeddings and store chunks
        for i, chunk in enumerate(chunks):
            embedding = await self.generate_embedding(chunk)
            await self.cosmos.store_document_chunk(
                document_id=doc_id,
                user_id=user_id,
                content=chunk,
                embedding=embedding,
                chunk_index=i,
                metadata={
                    **(metadata or {}),
                    "total_chunks": len(chunks),
                },
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
        Perform vector similarity search.

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

        # Perform vector search
        options = VectorSearchOptions(
            user_id=user_id,
            document_id=document_id,
            top_k=top_k,
            min_similarity=min_similarity,
        )

        results = await self.cosmos.vector_search(query_embedding, options)

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
        count = await self.cosmos.delete_document_chunks(document_id, user_id)
        logger.info(
            "document_deleted",
            document_id=document_id,
            chunks_deleted=count,
        )
        return count

    async def list_documents(self, user_id: str, limit: int = 50) -> list[dict]:
        """
        List documents for a user.

        Args:
            user_id: The user identifier
            limit: Maximum number of documents to return

        Returns:
            List of document metadata
        """
        documents = await self.cosmos.list_user_documents(user_id, limit)
        logger.info("documents_listed", user_id=user_id, count=len(documents))
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
