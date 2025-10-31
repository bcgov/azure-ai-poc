"""Search index management service for multi-tenant Azure AI Search."""

import asyncio
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    ComplexField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
)

from app.core.config import settings
from app.core.logger import get_logger
from app.models.tenant_models import Tenant

logger = get_logger(__name__)


class SearchIndexService:
    """Service for managing per-tenant Azure AI Search indexes."""

    def __init__(self):
        """Initialize the search index service."""
        self.endpoint = settings.AZURE_SEARCH_ENDPOINT
        self.api_key = settings.AZURE_SEARCH_API_KEY
        self.index_client = SearchIndexClient(
            endpoint=self.endpoint, credential=AzureKeyCredential(self.api_key)
        )

    def _get_tenant_index_name(self, tenant_id: str) -> str:
        """Generate index name for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Formatted index name for the tenant
        """
        # Index names must be lowercase and contain only letters, numbers, and hyphens
        safe_tenant_id = tenant_id.lower().replace("_", "-").replace(" ", "-")
        return f"tenant-{safe_tenant_id}-documents"

    def _create_document_index_schema(self) -> list[SearchField]:
        """Create the document index schema.

        Returns:
            List of search fields for the document index
        """
        return [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SimpleField(name="tenant_id", type=SearchFieldDataType.String, filterable=True),
            SearchableField(
                name="title", type=SearchFieldDataType.String, analyzer_name="standard.lucene"
            ),
            SearchableField(
                name="content", type=SearchFieldDataType.String, analyzer_name="standard.lucene"
            ),
            SearchableField(
                name="summary", type=SearchFieldDataType.String, analyzer_name="standard.lucene"
            ),
            SimpleField(
                name="file_name", type=SearchFieldDataType.String, filterable=True, facetable=True
            ),
            SimpleField(
                name="file_type", type=SearchFieldDataType.String, filterable=True, facetable=True
            ),
            SimpleField(name="file_size", type=SearchFieldDataType.Int64, filterable=True),
            SimpleField(
                name="upload_date",
                type=SearchFieldDataType.DateTimeOffset,
                filterable=True,
                sortable=True,
            ),
            SimpleField(
                name="last_modified",
                type=SearchFieldDataType.DateTimeOffset,
                filterable=True,
                sortable=True,
            ),
            SimpleField(
                name="uploaded_by", type=SearchFieldDataType.String, filterable=True, facetable=True
            ),
            SimpleField(name="document_url", type=SearchFieldDataType.String),
            SimpleField(name="cosmos_id", type=SearchFieldDataType.String, filterable=True),
            # Vector field for semantic search (if enabled)
            ComplexField(
                name="content_vector",
                fields=[
                    SimpleField(
                        name="vector",
                        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    ),
                ],
            ),
            # Metadata fields
            ComplexField(
                name="metadata",
                fields=[
                    SimpleField(
                        name="category",
                        type=SearchFieldDataType.String,
                        filterable=True,
                        facetable=True,
                    ),
                    SimpleField(
                        name="tags",
                        type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                        filterable=True,
                        facetable=True,
                    ),
                    SimpleField(
                        name="classification",
                        type=SearchFieldDataType.String,
                        filterable=True,
                        facetable=True,
                    ),
                    SimpleField(
                        name="author",
                        type=SearchFieldDataType.String,
                        filterable=True,
                        facetable=True,
                    ),
                    SimpleField(
                        name="department",
                        type=SearchFieldDataType.String,
                        filterable=True,
                        facetable=True,
                    ),
                ],
            ),
        ]

    async def create_tenant_index(self, tenant: Tenant) -> bool:
        """Create a search index for a tenant.

        Args:
            tenant: Tenant object

        Returns:
            True if index was created successfully, False otherwise
        """
        try:
            index_name = self._get_tenant_index_name(tenant.id)
            logger.info(
                "Creating search index for tenant", tenant_id=tenant.id, index_name=index_name
            )

            # Check if index already exists
            try:
                existing_index = await asyncio.get_event_loop().run_in_executor(
                    None, self.index_client.get_index, index_name
                )
                if existing_index:
                    logger.info(
                        "Search index already exists", tenant_id=tenant.id, index_name=index_name
                    )
                    return True
            except Exception:
                # Index doesn't exist, which is expected
                pass

            # Create the index
            fields = self._create_document_index_schema()
            index = SearchIndex(name=index_name, fields=fields)

            await asyncio.get_event_loop().run_in_executor(
                None, self.index_client.create_index, index
            )

            logger.info(
                "Successfully created search index", tenant_id=tenant.id, index_name=index_name
            )
            return True

        except Exception as e:
            logger.error("Failed to create search index", tenant_id=tenant.id, error=str(e))
            return False

    async def delete_tenant_index(self, tenant_id: str) -> bool:
        """Delete a search index for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            True if index was deleted successfully, False otherwise
        """
        try:
            index_name = self._get_tenant_index_name(tenant_id)
            logger.info(
                "Deleting search index for tenant", tenant_id=tenant_id, index_name=index_name
            )

            await asyncio.get_event_loop().run_in_executor(
                None, self.index_client.delete_index, index_name
            )

            logger.info(
                "Successfully deleted search index", tenant_id=tenant_id, index_name=index_name
            )
            return True

        except Exception as e:
            logger.error("Failed to delete search index", tenant_id=tenant_id, error=str(e))
            return False

    async def list_tenant_indexes(self) -> list[dict[str, Any]]:
        """List all tenant indexes.

        Returns:
            List of index information dictionaries
        """
        try:
            indexes = await asyncio.get_event_loop().run_in_executor(
                None, self.index_client.list_indexes
            )

            tenant_indexes = []
            for index in indexes:
                if index.name.startswith("tenant-") and index.name.endswith("-documents"):
                    # Extract tenant ID from index name
                    tenant_id = index.name[7:-10]  # Remove "tenant-" prefix and "-documents" suffix
                    tenant_indexes.append(
                        {
                            "tenant_id": tenant_id.replace(
                                "-", "_"
                            ),  # Convert back to original format
                            "index_name": index.name,
                            "document_count": getattr(index, "document_count", None),
                            "storage_size": getattr(index, "storage_size", None),
                        }
                    )

            return tenant_indexes

        except Exception as e:
            logger.error("Failed to list tenant indexes", error=str(e))
            return []

    async def get_tenant_index_stats(self, tenant_id: str) -> dict[str, Any] | None:
        """Get statistics for a tenant's search index.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Dictionary with index statistics or None if not found
        """
        try:
            index_name = self._get_tenant_index_name(tenant_id)

            # Get index statistics
            index_stats = await asyncio.get_event_loop().run_in_executor(
                None, self.index_client.get_index_statistics, index_name
            )

            return {
                "tenant_id": tenant_id,
                "index_name": index_name,
                "document_count": index_stats.document_count,
                "storage_size": index_stats.storage_size,
            }

        except Exception as e:
            logger.error("Failed to get index statistics", tenant_id=tenant_id, error=str(e))
            return None

    async def index_exists(self, tenant_id: str) -> bool:
        """Check if a search index exists for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            True if index exists, False otherwise
        """
        try:
            index_name = self._get_tenant_index_name(tenant_id)
            await asyncio.get_event_loop().run_in_executor(
                None, self.index_client.get_index, index_name
            )
            return True
        except Exception:
            return False

    async def recreate_tenant_index(self, tenant: Tenant) -> bool:
        """Recreate a search index for a tenant (delete and create).

        Args:
            tenant: Tenant object

        Returns:
            True if index was recreated successfully, False otherwise
        """
        try:
            # Delete existing index if it exists
            if await self.index_exists(tenant.id):
                await self.delete_tenant_index(tenant.id)

            # Create new index
            return await self.create_tenant_index(tenant)

        except Exception as e:
            logger.error("Failed to recreate search index", tenant_id=tenant.id, error=str(e))
            return False


# Dependency injection
_search_index_service: SearchIndexService | None = None


def get_search_index_service() -> SearchIndexService:
    """Get or create the search index service instance.

    Returns:
        SearchIndexService instance
    """
    global _search_index_service
    if _search_index_service is None:
        _search_index_service = SearchIndexService()
    return _search_index_service
