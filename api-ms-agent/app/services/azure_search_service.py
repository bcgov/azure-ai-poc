"""
Azure AI Search service for vector embeddings storage and search.

This service provides:
- Vector similarity search using Azure AI Search
- Document embeddings storage with metadata
- Index management for document chunks
- Managed identity authentication with key fallback

Uses the async Azure Search SDK (azure.search.documents.aio) for non-blocking I/O.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.identity.aio import DefaultAzureCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DocumentChunk:
    """A document chunk with vector embedding stored in Azure AI Search."""

    id: str
    document_id: str
    user_id: str
    content: str
    embedding: list[float]
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class VectorSearchOptions:
    """Options for vector similarity search."""

    user_id: str | None = None
    document_id: str | None = None
    top_k: int = 5
    min_similarity: float = 0.0


class AzureSearchService:
    """Service for Azure AI Search vector operations.

    Uses the async Azure Search SDK for non-blocking I/O operations.
    """

    # Embedding dimensions for text-embedding-3-large
    EMBEDDING_DIMENSIONS = 3072

    def __init__(self) -> None:
        """Initialize the Azure Search service."""
        self._index_client: SearchIndexClient | None = None
        self._search_client: SearchClient | None = None
        self._credential: DefaultAzureCredential | None = None
        self._initialized = False
        self._index_name = settings.azure_search_index_name

    async def _initialize_client(self) -> None:
        """Initialize the Azure Search clients with managed identity or key authentication."""
        if self._initialized:
            return

        endpoint = settings.azure_search_endpoint

        if not endpoint:
            logger.warning(
                "azure_search_config_missing",
                message="Azure AI Search not configured - vector search will not be available",
            )
            return

        try:
            # Use key authentication for local, managed identity for cloud
            if settings.environment == "local" and settings.azure_search_key:
                credential: AzureKeyCredential | DefaultAzureCredential = AzureKeyCredential(
                    settings.azure_search_key
                )
                logger.info("azure_search_init", auth_method="key")
            else:
                self._credential = DefaultAzureCredential()
                credential = self._credential
                logger.info("azure_search_init", auth_method="managed_identity")

            # Create index client for index management
            self._index_client = SearchIndexClient(
                endpoint=endpoint,
                credential=credential,
            )

            # Ensure index exists
            await self._ensure_index_exists()

            # Create search client for document operations
            self._search_client = SearchClient(
                endpoint=endpoint,
                index_name=self._index_name,
                credential=credential,
            )

            self._initialized = True
            logger.info("azure_search_initialized", index=self._index_name)

        except Exception as error:
            logger.error("azure_search_init_failed", error=str(error))
            # Don't raise - allow service to work without search

    async def _ensure_index_exists(self) -> None:
        """Ensure the search index exists with proper vector configuration."""
        if not self._index_client:
            return

        try:
            # Check if index already exists
            try:
                await self._index_client.get_index(self._index_name)
                logger.info("azure_search_index_exists", index=self._index_name)
                return
            except Exception:
                pass  # Index doesn't exist, create it

            # Define the index schema with vector search
            fields = [
                SimpleField(
                    name="id",
                    type=SearchFieldDataType.String,
                    key=True,
                    filterable=True,
                ),
                SimpleField(
                    name="document_id",
                    type=SearchFieldDataType.String,
                    filterable=True,
                    sortable=True,
                ),
                SimpleField(
                    name="user_id",
                    type=SearchFieldDataType.String,
                    filterable=True,
                ),
                SearchableField(
                    name="content",
                    type=SearchFieldDataType.String,
                    searchable=True,
                ),
                SimpleField(
                    name="chunk_index",
                    type=SearchFieldDataType.Int32,
                    filterable=True,
                    sortable=True,
                ),
                SimpleField(
                    name="title",
                    type=SearchFieldDataType.String,
                    filterable=True,
                ),
                SimpleField(
                    name="filename",
                    type=SearchFieldDataType.String,
                    filterable=True,
                ),
                SimpleField(
                    name="content_type",
                    type=SearchFieldDataType.String,
                    filterable=True,
                ),
                SimpleField(
                    name="total_chunks",
                    type=SearchFieldDataType.Int32,
                    filterable=True,
                ),
                SimpleField(
                    name="created_at",
                    type=SearchFieldDataType.DateTimeOffset,
                    filterable=True,
                    sortable=True,
                ),
                # Vector field for embeddings
                SearchField(
                    name="embedding",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=self.EMBEDDING_DIMENSIONS,
                    vector_search_profile_name="vector-profile",
                ),
            ]

            # Configure vector search
            vector_search = VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="hnsw-config",
                    ),
                ],
                profiles=[
                    VectorSearchProfile(
                        name="vector-profile",
                        algorithm_configuration_name="hnsw-config",
                    ),
                ],
            )

            # Create the index
            index = SearchIndex(
                name=self._index_name,
                fields=fields,
                vector_search=vector_search,
            )

            await self._index_client.create_index(index)
            logger.info("azure_search_index_created", index=self._index_name)

        except Exception as error:
            logger.error("azure_search_index_create_failed", error=str(error))
            raise

    async def _ensure_initialized(self) -> bool:
        """Ensure the service is initialized. Returns True if ready."""
        if not self._initialized:
            await self._initialize_client()
        return self._initialized

    async def bulk_store_chunks(
        self,
        chunks: list[DocumentChunk],
        batch_size: int = 1000,
    ) -> int:
        """
        Bulk store document chunks in Azure Search with batching.

        Azure Search supports up to 1000 documents per upload batch.
        This is significantly faster than individual uploads.

        Args:
            chunks: List of DocumentChunk objects to store
            batch_size: Number of documents per upload batch (max 1000)

        Returns:
            Number of successfully stored chunks
        """
        if not chunks:
            return 0

        if not await self._ensure_initialized():
            return 0

        # Prepare all documents
        documents = []
        for chunk in chunks:
            documents.append(
                {
                    "id": chunk.id,
                    "document_id": chunk.document_id,
                    "user_id": chunk.user_id,
                    "content": chunk.content,
                    "embedding": chunk.embedding,
                    "chunk_index": chunk.chunk_index,
                    "title": (chunk.metadata or {}).get("title", ""),
                    "filename": (chunk.metadata or {}).get("filename", ""),
                    "content_type": (chunk.metadata or {}).get("content_type", ""),
                    "total_chunks": (chunk.metadata or {}).get("total_chunks", 0),
                    "created_at": chunk.created_at.isoformat(),
                }
            )

        success_count = 0
        total_batches = (len(documents) + batch_size - 1) // batch_size

        try:
            for i in range(0, len(documents), batch_size):
                batch = documents[i : i + batch_size]
                batch_num = (i // batch_size) + 1

                result = await self._search_client.upload_documents(documents=batch)
                batch_success = sum(1 for r in result if r.succeeded)
                success_count += batch_success

                logger.debug(
                    "bulk_upload_batch_complete",
                    batch=batch_num,
                    total_batches=total_batches,
                    succeeded=batch_success,
                    failed=len(batch) - batch_success,
                )

            logger.info(
                "bulk_chunks_stored",
                total_chunks=len(chunks),
                succeeded=success_count,
                batches=total_batches,
            )
            return success_count

        except Exception as error:
            logger.error("bulk_store_failed", error=str(error), stored=success_count)
            raise

    async def store_document_chunk(
        self,
        document_id: str,
        user_id: str,
        content: str,
        embedding: list[float],
        chunk_index: int,
        metadata: dict[str, Any] | None = None,
    ) -> DocumentChunk:
        """
        Store a document chunk with its vector embedding.

        Args:
            document_id: The parent document identifier
            user_id: The user identifier
            content: The text content of the chunk
            embedding: The vector embedding
            chunk_index: Index of this chunk in the document
            metadata: Optional additional metadata

        Returns:
            The stored document chunk
        """
        chunk_id = f"{document_id}_chunk_{chunk_index}"
        now = datetime.now(UTC)

        chunk = DocumentChunk(
            id=chunk_id,
            document_id=document_id,
            user_id=user_id,
            content=content,
            embedding=embedding,
            chunk_index=chunk_index,
            metadata=metadata or {},
            created_at=now,
        )

        if not await self._ensure_initialized():
            return chunk

        # Prepare document for Azure Search
        document = {
            "id": chunk_id,
            "document_id": document_id,
            "user_id": user_id,
            "content": content,
            "embedding": embedding,
            "chunk_index": chunk_index,
            "title": (metadata or {}).get("title", ""),
            "filename": (metadata or {}).get("filename", ""),
            "content_type": (metadata or {}).get("content_type", ""),
            "total_chunks": (metadata or {}).get("total_chunks", 0),
            "created_at": now.isoformat(),
        }

        try:
            result = await self._search_client.upload_documents(documents=[document])
            if result[0].succeeded:
                logger.debug(
                    "chunk_stored",
                    chunk_id=chunk_id,
                    document_id=document_id,
                    embedding_dims=len(embedding),
                )
            else:
                logger.error(
                    "chunk_store_failed",
                    chunk_id=chunk_id,
                    error=result[0].error_message,
                )
            return chunk
        except Exception as error:
            logger.error("chunk_store_failed", error=str(error), chunk_id=chunk_id)
            raise
            raise

    async def vector_search(
        self,
        embedding: list[float],
        options: VectorSearchOptions | None = None,
    ) -> list[dict[str, Any]]:
        """
        Perform vector similarity search using Azure AI Search.

        Args:
            embedding: The query embedding vector
            options: Vector search options

        Returns:
            List of similar document chunks with similarity scores
        """
        if not await self._ensure_initialized():
            logger.warning("azure_search_not_initialized")
            return []

        if options is None:
            options = VectorSearchOptions()

        try:
            # Build filter expression
            filters = []
            if options.user_id:
                filters.append(f"user_id eq '{options.user_id}'")
            if options.document_id:
                filters.append(f"document_id eq '{options.document_id}'")

            filter_expression = " and ".join(filters) if filters else None

            # Create vector query
            vector_query = VectorizedQuery(
                vector=embedding,
                k_nearest_neighbors=options.top_k,
                fields="embedding",
            )

            start_time = time.time()

            # Execute search (async iteration)
            results = await self._search_client.search(
                search_text=None,
                vector_queries=[vector_query],
                filter=filter_expression,
                top=options.top_k,
                select=[
                    "id",
                    "document_id",
                    "user_id",
                    "content",
                    "chunk_index",
                    "title",
                    "filename",
                ],
            )

            # Process results (async iteration)
            items = []
            async for result in results:
                # Azure Search returns @search.score for relevance
                similarity = result.get("@search.score", 0.0)

                # Skip results below minimum similarity threshold
                if options.min_similarity > 0 and similarity < options.min_similarity:
                    continue

                items.append(
                    {
                        "id": result["id"],
                        "document_id": result["document_id"],
                        "user_id": result.get("user_id", ""),
                        "content": result["content"],
                        "chunk_index": result.get("chunk_index", 0),
                        "similarity": similarity,
                        "metadata": {
                            "title": result.get("title", ""),
                            "filename": result.get("filename", ""),
                        },
                    }
                )

            query_time = (time.time() - start_time) * 1000
            logger.info(
                "vector_search_completed",
                results=len(items),
                query_time_ms=f"{query_time:.2f}",
                top_k=options.top_k,
                document_id=options.document_id,
            )

            return items

        except Exception as error:
            logger.error("vector_search_failed", error=str(error))
            raise

    async def list_user_documents(self, user_id: str, limit: int = 50) -> list[dict]:
        """
        List documents for a user by aggregating unique document IDs.

        Args:
            user_id: The user identifier
            limit: Maximum number of documents to return

        Returns:
            List of document metadata
        """
        if not await self._ensure_initialized():
            return []

        try:
            # Query to get documents for user, group by document_id
            results = await self._search_client.search(
                search_text="*",
                filter=f"user_id eq '{user_id}'",
                select=[
                    "document_id",
                    "title",
                    "filename",
                    "created_at",
                    "chunk_index",
                    "total_chunks",
                ],
                top=1000,  # Get more to aggregate
            )

            # Aggregate documents (async iteration)
            documents_map: dict[str, dict] = {}
            async for result in results:
                doc_id = result.get("document_id")
                if doc_id and doc_id not in documents_map:
                    documents_map[doc_id] = {
                        "id": doc_id,
                        "document_id": doc_id,
                        "title": result.get("title")
                        or result.get("filename")
                        or f"Document {doc_id[:8]}...",
                        "created_at": result.get("created_at"),
                        "chunk_count": result.get("total_chunks", 1),
                    }

            result_list = list(documents_map.values())[:limit]
            logger.info("documents_listed", user_id=user_id, count=len(result_list))
            return result_list

        except Exception as error:
            logger.error("documents_list_failed", error=str(error), user_id=user_id)
            return []

    async def delete_document_chunks(self, document_id: str, user_id: str) -> int:
        """
        Delete all chunks for a document.

        Args:
            document_id: The document identifier
            user_id: The user identifier

        Returns:
            Number of chunks deleted
        """
        if not await self._ensure_initialized():
            return 0

        try:
            # Find all chunks for the document
            results = await self._search_client.search(
                search_text="*",
                filter=f"document_id eq '{document_id}' and user_id eq '{user_id}'",
                select=["id"],
                top=1000,
            )

            # Collect chunk IDs to delete (async iteration)
            chunk_ids = [{"id": result["id"]} async for result in results]

            if not chunk_ids:
                return 0

            # Delete the chunks
            delete_result = await self._search_client.delete_documents(documents=chunk_ids)

            deleted_count = sum(1 for r in delete_result if r.succeeded)
            logger.info(
                "chunks_deleted",
                document_id=document_id,
                count=deleted_count,
            )
            return deleted_count

        except Exception as error:
            logger.error(
                "chunks_delete_failed",
                error=str(error),
                document_id=document_id,
            )
            return 0

    async def health_check(self) -> dict[str, Any]:
        """
        Perform a health check on the Azure AI Search connection.

        Returns:
            Health check result with status and details
        """
        if not await self._ensure_initialized():
            return {
                "status": "unconfigured",
                "details": {
                    "message": "Azure AI Search not configured",
                    "timestamp": time.time(),
                },
            }

        try:
            start_time = time.time()

            # Try to get index stats
            if self._index_client:
                await self._index_client.get_index(self._index_name)

            response_time = (time.time() - start_time) * 1000

            return {
                "status": "up",
                "details": {
                    "responseTime": f"{response_time:.2f}ms",
                    "status": "connected",
                    "index": self._index_name,
                    "timestamp": time.time(),
                },
            }

        except Exception as error:
            logger.error("azure_search_health_check_failed", error=str(error))
            return {
                "status": "down",
                "details": {
                    "error": str(error),
                    "status": "disconnected",
                    "timestamp": time.time(),
                },
            }

    async def dispose(self) -> None:
        """Dispose of the Azure Search clients."""
        if self._search_client:
            await self._search_client.close()
        if self._index_client:
            await self._index_client.close()
        if self._credential:
            await self._credential.close()
        self._index_client = None
        self._search_client = None
        self._credential = None
        self._initialized = False
        logger.info("azure_search_disposed")


# Global service instance
_azure_search_service: AzureSearchService | None = None


def get_azure_search_service() -> AzureSearchService:
    """Get the global Azure Search service instance."""
    global _azure_search_service
    if _azure_search_service is None:
        _azure_search_service = AzureSearchService()
    return _azure_search_service


@asynccontextmanager
async def azure_search_context():
    """Context manager for Azure Search service."""
    service = get_azure_search_service()
    try:
        yield service
    finally:
        pass  # Cleanup if needed
