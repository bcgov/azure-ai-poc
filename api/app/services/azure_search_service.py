"""Azure AI Search service abstraction.

Provides:
- Index creation (idempotent)
- Document (chunk + metadata) upload
- Vector similarity search
- CRUD helpers for document metadata and chunks

We consolidate document metadata and chunks into a single index using a hierarchical modeling approach.
Each stored record has a 'recordType' field: either 'document' or 'chunk'.
Chunk vectors are stored in 'embedding' field (Azure Search vector field).

Partition (multi-tenant) segregation achieved via 'partitionKey' field which is filterable.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class VectorSearchRequest:
    embedding: list[float]
    top_k: int = 3
    partition_key: str | None = None
    document_id: str | None = None


class AzureSearchService:
    def __init__(self) -> None:
        self.settings = settings
        self.index_name = self.settings.AZURE_SEARCH_INDEX_NAME
        self.endpoint = self.settings.AZURE_SEARCH_ENDPOINT
        self.api_key = self.settings.AZURE_SEARCH_API_KEY
        self._search_client: SearchClient | None = None
        self._index_client: SearchIndexClient | None = None
        self._ensure_initialized()

    def _credential(self):  # type: ignore[override]
        if self.api_key:
            return AzureKeyCredential(self.api_key)
        return DefaultAzureCredential()

    def _ensure_initialized(self) -> None:
        if not self.endpoint:
            raise ValueError("AZURE_SEARCH_ENDPOINT not configured")
        cred = self._credential()
        self._index_client = SearchIndexClient(self.endpoint, cred)  # type: ignore[arg-type]
        # Ensure index exists
        self._create_index_if_not_exists()
        self._search_client = SearchClient(self.endpoint, self.index_name, cred)  # type: ignore[arg-type]
        logger.info("AzureSearchService initialized: index=%s", self.index_name)

    def _create_index_if_not_exists(self) -> None:
        assert self._index_client is not None
        existing = [i.name for i in self._index_client.list_indexes()]
        if self.index_name in existing:
            return

        # Create vector search configuration with algorithm and profile
        # Required for vector fields in Azure Search 11.5+
        algo_name = "hnsw-algo"
        profile_name = "default-profile"

        try:
            algorithm = HnswAlgorithmConfiguration(name=algo_name)
            profile = VectorSearchProfile(name=profile_name, algorithm_configuration_name=algo_name)
            vector_search = VectorSearch(algorithms=[algorithm], profiles=[profile])
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to create vector search config: %s", e)
            # Fallback to basic VectorSearch if configuration fails
            try:
                vector_search = VectorSearch()
                profile_name = None  # No profile available
            except Exception:  # noqa: BLE001
                vector_search = None  # type: ignore
                profile_name = None

        fields: list[SearchField] = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SimpleField(
                name="recordType",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
            ),
            SimpleField(name="documentId", type=SearchFieldDataType.String, filterable=True),
            SimpleField(
                name="filename",
                type=SearchFieldDataType.String,
                filterable=True,
                searchable=True,
            ),
            SimpleField(name="partitionKey", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="userId", type=SearchFieldDataType.String, filterable=True),
            SimpleField(
                name="uploadedAt",
                type=SearchFieldDataType.String,
                filterable=True,
                sortable=True,
            ),
            SimpleField(
                name="chunkIndex",
                type=SearchFieldDataType.Int32,
                filterable=True,
                sortable=True,
            ),
            SearchField(name="content", type=SearchFieldDataType.String, searchable=True),
            SearchField(
                name="embedding",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=3072,
                vector_search_profile_name=profile_name,
            ),
            SearchField(
                name="metadataJson",
                type=SearchFieldDataType.String,
                searchable=False,
                filterable=False,
                facetable=False,
                sortable=False,
            ),
        ]

        if vector_search:
            index = SearchIndex(name=self.index_name, fields=fields, vector_search=vector_search)
        else:  # pragma: no cover - fallback path
            index = SearchIndex(name=self.index_name, fields=fields)
        self._index_client.create_index(index)
        logger.info("Created Azure AI Search index '%s'", self.index_name)

    @property
    def search_client(self) -> SearchClient:
        assert self._search_client is not None
        return self._search_client

    # ----------------- Document & Chunk Operations -----------------
    def upload_chunks(self, chunks: list[dict[str, Any]]) -> None:
        # Azure Search upsert documents.
        if not chunks:
            return
        batch = []
        for c in chunks:
            batch.append(
                {
                    "id": c["id"],
                    "recordType": "chunk",
                    "documentId": c["document_id"],
                    "filename": c["metadata"].get("filename"),
                    "partitionKey": c["partition_key"],
                    "userId": c.get("user_id"),
                    "uploadedAt": c["metadata"].get("uploadedAt"),
                    "chunkIndex": c["metadata"].get("chunkIndex"),
                    "content": c["content"],
                    "embedding": c.get("embedding"),
                    "metadataJson": json.dumps(c.get("metadata", {})),
                }
            )
        self.search_client.upload_documents(documents=batch)
        logger.info("Uploaded %d chunks to Azure Search", len(batch))

    def upload_document_metadata(self, doc: dict[str, Any]) -> None:
        self.search_client.upload_documents(
            documents=[
                {
                    "id": doc["id"],
                    "recordType": "document",
                    "documentId": doc["id"],
                    "filename": doc["filename"],
                    "partitionKey": doc["partition_key"],
                    "userId": doc.get("user_id"),
                    "uploadedAt": doc["uploaded_at"],
                    "content": "",  # metadata only
                    "chunkIndex": -1,
                    "metadataJson": json.dumps({"chunkIds": doc.get("chunk_ids", [])}),
                }
            ]
        )
        logger.info("Uploaded document metadata %s", doc["id"])

    def get_document(self, document_id: str, partition_key: str) -> dict[str, Any] | None:
        filter_expr = (
            f"partitionKey eq '{partition_key}' and id eq '{document_id}' "
            "and recordType eq 'document'"
        )
        results = self.search_client.search(search_text="*", filter=filter_expr, top=1)
        for r in results:
            return r
        return None

    def list_documents(self, partition_key: str) -> list[dict[str, Any]]:
        filter_expr = f"partitionKey eq '{partition_key}' and recordType eq 'document'"
        results = self.search_client.search(
            search_text="*",
            filter=filter_expr,
            top=1000,
            order_by=["uploadedAt desc"],
        )
        return list(results)

    def list_chunks(self, document_id: str, partition_key: str) -> list[dict[str, Any]]:
        filter_expr = (
            f"partitionKey eq '{partition_key}' and recordType eq 'chunk' "
            f"and documentId eq '{document_id}'"
        )
        results = self.search_client.search(
            search_text="*", filter=filter_expr, top=1000, order_by=["chunkIndex asc"]
        )
        return list(results)

    def delete_document_and_chunks(self, document_id: str, partition_key: str) -> None:
        # Delete document metadata and all chunks by issuing delete with ids.
        # Need to query first to collect ids.
        filter_expr = f"partitionKey eq '{partition_key}' and documentId eq '{document_id}'"
        results = self.search_client.search(search_text="*", filter=filter_expr, top=2000)
        ids = [r["id"] for r in results]
        if not ids:
            return
        self.search_client.delete_documents(documents=[{"id": i} for i in ids])
        logger.info("Deleted document %s and %d related records", document_id, len(ids))

    # ----------------- Vector Search -----------------
    def vector_search(self, request: VectorSearchRequest) -> list[dict[str, Any]]:
        # Build filter
        filters = ["recordType eq 'chunk'"]
        if request.partition_key:
            filters.append(f"partitionKey eq '{request.partition_key}'")
        if request.document_id:
            filters.append(f"documentId eq '{request.document_id}'")
        filter_expr = " and ".join(filters)

        vector_query = {
            "value": request.embedding,
            "k": request.top_k,
            "fields": "embedding",
        }
        results = self.search_client.search(
            search_text="*",
            vector_queries=[vector_query],
            filter=filter_expr,
            top=request.top_k,
            select=["id", "documentId", "content", "filename", "chunkIndex", "partitionKey"],
        )
        # Azure Search returns no explicit score for pure vector query yet; we keep order.
        return list(results)


# Global singleton
_azure_search_service: AzureSearchService | None = None


def get_azure_search_service() -> AzureSearchService:
    global _azure_search_service
    if _azure_search_service is None:
        _azure_search_service = AzureSearchService()
    return _azure_search_service
