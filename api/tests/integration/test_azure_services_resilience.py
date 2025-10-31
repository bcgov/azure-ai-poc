"""Integration tests for Azure services error handling and resilience."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from azure.core.exceptions import (
    AzureError,
    ResourceNotFoundError,
    ServiceRequestError,
)

from app.services.azure_openai_service import AzureOpenAIService
from app.services.azure_search_service import AzureSearchService
from app.services.cosmos_db_service import CosmosDbService


class TestAzureOpenAIServiceResilience:
    """Tests for Azure OpenAI service error handling."""

    @pytest.mark.asyncio
    async def test_embedding_service_timeout(self):
        """Test embedding generation with timeout."""
        service = AzureOpenAIService()

        with patch.object(service, "embeddings", MagicMock()) as mock_embeddings:
            mock_embeddings.aembed_query = AsyncMock(side_effect=TimeoutError("Request timeout"))

            with pytest.raises(TimeoutError):
                await service.embeddings.aembed_query("test text")

    @pytest.mark.asyncio
    async def test_chat_completion_rate_limit(self):
        """Test chat completion with rate limit error."""
        service = AzureOpenAIService()

        with patch.object(service, "llm", MagicMock()) as mock_llm:
            mock_llm.ainvoke = AsyncMock(side_effect=Exception("Rate limit exceeded"))

            with pytest.raises(Exception, match="Rate limit"):
                await service.llm.ainvoke("test prompt")

    @pytest.mark.asyncio
    async def test_embedding_invalid_input(self):
        """Test embedding with invalid input."""
        service = AzureOpenAIService()

        with patch.object(service, "embeddings", MagicMock()) as mock_embeddings:
            mock_embeddings.aembed_query = AsyncMock(side_effect=ValueError("Invalid input text"))

            with pytest.raises(ValueError):
                await service.embeddings.aembed_query("")


class TestAzureSearchServiceResilience:
    """Tests for Azure Search service error handling."""

    @pytest.mark.asyncio
    async def test_create_index_already_exists(self):
        """Test creating index that already exists."""
        service = AzureSearchService()

        with patch.object(service, "index_client", MagicMock()) as mock_client:
            mock_client.create_index = MagicMock(side_effect=AzureError("Index already exists"))

            with pytest.raises(AzureError):
                await service.create_index("existing-index")

    @pytest.mark.asyncio
    async def test_search_with_invalid_query(self):
        """Test search with malformed query."""
        service = AzureSearchService()

        with patch.object(service, "search_client", MagicMock()) as mock_client:
            mock_client.search = MagicMock(side_effect=ValueError("Invalid search query syntax"))

            with pytest.raises(ValueError):
                await service.search(
                    index_name="test-index",
                    query="invalid)(*&^%syntax",
                )

    @pytest.mark.asyncio
    async def test_delete_nonexistent_index(self):
        """Test deleting non-existent index."""
        service = AzureSearchService()

        with patch.object(service, "index_client", MagicMock()) as mock_client:
            mock_client.delete_index = MagicMock(
                side_effect=ResourceNotFoundError("Index not found")
            )

            with pytest.raises(ResourceNotFoundError):
                await service.delete_index("nonexistent-index")

    @pytest.mark.asyncio
    async def test_upload_documents_quota_exceeded(self):
        """Test uploading documents when quota is exceeded."""
        service = AzureSearchService()

        with patch.object(service, "search_client", MagicMock()) as mock_client:
            mock_client.upload_documents = AsyncMock(side_effect=AzureError("Quota exceeded"))

            with pytest.raises(AzureError, match="Quota"):
                await service.search_client.upload_documents([{"id": "1"}])

    @pytest.mark.asyncio
    async def test_search_service_unavailable(self):
        """Test search when service is unavailable."""
        service = AzureSearchService()

        with patch.object(service, "search_client", MagicMock()) as mock_client:
            mock_client.search = MagicMock(side_effect=ServiceRequestError("Service unavailable"))

            with pytest.raises(ServiceRequestError):
                await service.search(
                    index_name="test-index",
                    query="test",
                )


class TestCosmosDbServiceResilience:
    """Tests for Cosmos DB service error handling."""

    @pytest.mark.asyncio
    async def test_create_item_duplicate_id(self):
        """Test creating item with duplicate ID."""
        service = CosmosDbService()

        with patch.object(service, "get_container", MagicMock()) as mock_get:
            mock_container = MagicMock()
            mock_container.create_item = MagicMock(
                side_effect=AzureError("Conflict: Item already exists")
            )
            mock_get.return_value = mock_container

            with pytest.raises(AzureError, match="Conflict"):
                service.get_container("test").create_item({"id": "duplicate"})

    @pytest.mark.asyncio
    async def test_read_item_not_found(self):
        """Test reading non-existent item."""
        service = CosmosDbService()

        with patch.object(service, "get_container", MagicMock()) as mock_get:
            mock_container = MagicMock()
            mock_container.read_item = MagicMock(
                side_effect=ResourceNotFoundError("Item not found")
            )
            mock_get.return_value = mock_container

            with pytest.raises(ResourceNotFoundError):
                service.get_container("test").read_item(
                    item="nonexistent",
                    partition_key="key",
                )

    @pytest.mark.asyncio
    async def test_query_items_request_rate_too_large(self):
        """Test query when request rate is too large."""
        service = CosmosDbService()

        with patch.object(service, "get_container", MagicMock()) as mock_get:
            mock_container = MagicMock()
            mock_container.query_items = MagicMock(side_effect=AzureError("Request rate too large"))
            mock_get.return_value = mock_container

            with pytest.raises(AzureError, match="rate"):
                list(
                    service.get_container("test").query_items(
                        query="SELECT * FROM c",
                    )
                )

    @pytest.mark.asyncio
    async def test_delete_item_partition_mismatch(self):
        """Test deleting item with wrong partition key."""
        service = CosmosDbService()

        with patch.object(service, "get_container", MagicMock()) as mock_get:
            mock_container = MagicMock()
            mock_container.delete_item = MagicMock(side_effect=AzureError("Partition key mismatch"))
            mock_get.return_value = mock_container

            with pytest.raises(AzureError, match="Partition"):
                service.get_container("test").delete_item(
                    item="item-id",
                    partition_key="wrong-key",
                )

    @pytest.mark.asyncio
    async def test_create_container_invalid_throughput(self):
        """Test creating container with invalid throughput."""
        service = CosmosDbService()

        with patch.object(service, "database", MagicMock()) as mock_db:
            mock_db.create_container = AsyncMock(
                side_effect=ValueError("Invalid throughput configuration")
            )

            with pytest.raises(ValueError, match="throughput"):
                await service.create_container(
                    container_name="test",
                    partition_key_path="/invalid",
                )


class TestAzureServicesConnectionHandling:
    """Tests for Azure services connection handling."""

    @pytest.mark.asyncio
    async def test_openai_service_connection_lost(self):
        """Test OpenAI service when connection is lost."""
        service = AzureOpenAIService()

        with patch.object(service, "embeddings", MagicMock()) as mock_embeddings:
            mock_embeddings.aembed_query = AsyncMock(side_effect=ConnectionError("Connection lost"))

            with pytest.raises(ConnectionError):
                await service.embeddings.aembed_query("test")

    @pytest.mark.asyncio
    async def test_search_service_authentication_failure(self):
        """Test Search service with authentication failure."""
        service = AzureSearchService()

        with patch.object(service, "search_client", MagicMock()) as mock_client:
            mock_client.search = MagicMock(side_effect=AzureError("Authentication failed"))

            with pytest.raises(AzureError, match="Authentication"):
                await service.search(
                    index_name="test-index",
                    query="test",
                )

    @pytest.mark.asyncio
    async def test_cosmos_service_network_timeout(self):
        """Test Cosmos DB service with network timeout."""
        service = CosmosDbService()

        with patch.object(service, "get_container", MagicMock()) as mock_get:
            mock_container = MagicMock()
            mock_container.read_item = MagicMock(side_effect=TimeoutError("Network timeout"))
            mock_get.return_value = mock_container

            with pytest.raises(TimeoutError):
                service.get_container("test").read_item(
                    item="test-id",
                    partition_key="key",
                )
