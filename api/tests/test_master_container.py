"""Tests for multi-tenant service master container setup and initialization."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from app.services.multi_tenant_service import MultiTenantService


class TestMasterContainerSetup:
    """Test master container setup and initialization."""

    @pytest.fixture
    def mock_cosmos_service(self):
        """Create a mock Cosmos DB service."""
        mock_service = MagicMock()
        mock_service.create_container = AsyncMock()
        mock_service.database = MagicMock()
        mock_service.database.create_container = MagicMock()
        return mock_service

    @pytest.fixture
    def mock_search_service(self):
        """Create a mock Azure Search service."""
        mock_service = AsyncMock()
        return mock_service

    @pytest.fixture
    def service(self, mock_cosmos_service, mock_search_service):
        """Create a MultiTenantService instance with mocked dependencies."""
        with (
            patch("app.services.multi_tenant_service.get_cosmos_db_service") as mock_get_cosmos,
            patch("app.services.multi_tenant_service.get_azure_search_service") as mock_get_search,
        ):
            mock_get_cosmos.return_value = mock_cosmos_service
            mock_get_search.return_value = mock_search_service

            service = MultiTenantService()
            return service

    @pytest.mark.asyncio
    async def test_initialize_with_existing_container(self, service, mock_cosmos_service):
        """Test initialization when master container already exists."""
        # Setup
        mock_container = MagicMock()
        mock_cosmos_service.get_container.return_value = mock_container

        # Mock the query for validation
        mock_container.query_items.return_value = [5]  # 5 tenants

        # Execute
        await service.initialize()

        # Verify
        mock_cosmos_service.get_container.assert_called_once_with("tenants")
        mock_cosmos_service.create_container.assert_not_called()
        assert service._master_container == mock_container

    @pytest.mark.asyncio
    async def test_initialize_creates_new_container(self, service, mock_cosmos_service):
        """Test initialization when master container doesn't exist."""
        # Setup
        mock_container = MagicMock()
        mock_cosmos_service.get_container.side_effect = CosmosResourceNotFoundError(
            message="Container not found"
        )
        mock_cosmos_service.database.create_container.return_value = mock_container

        # Mock the query for validation
        mock_container.query_items.return_value = [0]  # 0 tenants

        # Execute
        await service.initialize()

        # Verify
        mock_cosmos_service.get_container.assert_called_once_with("tenants")
        mock_cosmos_service.database.create_container.assert_called_once()

        # Check container creation parameters
        call_args = mock_cosmos_service.database.create_container.call_args
        assert call_args.kwargs["id"] == "tenants"
        assert call_args.kwargs["partition_key"]["paths"] == ["/partitionKey"]
        assert "indexing_policy" in call_args.kwargs

        # Verify container properties
        container_props = call_args.kwargs["indexing_policy"]
        assert container_props["compositeIndexes"]

        assert service._master_container == mock_container

    @pytest.mark.asyncio
    async def test_validate_master_container_success(self, service, mock_cosmos_service):
        """Test successful master container validation."""
        # Setup
        mock_container = MagicMock()
        mock_container.query_items.return_value = [3]  # 3 tenants
        service._master_container = mock_container

        # Execute - this is called as part of initialize()
        await service._validate_master_container()

        # Verify
        mock_container.query_items.assert_called_once()
        query_args = mock_container.query_items.call_args
        assert "SELECT VALUE COUNT(1) FROM c WHERE c.type = 'tenant'" in query_args[1]["query"]

    @pytest.mark.asyncio
    async def test_validate_master_container_not_initialized(self, service):
        """Test validation fails when container not initialized."""
        # Setup - no container set
        service._master_container = None

        # Execute & Verify
        with pytest.raises(RuntimeError, match="Master container not initialized"):
            await service._validate_master_container()

    @pytest.mark.asyncio
    async def test_validate_master_container_query_fails(self, service):
        """Test validation fails when query fails."""
        # Setup
        mock_container = MagicMock()
        mock_container.query_items.side_effect = Exception("Query failed")
        service._master_container = mock_container

        # Execute & Verify
        with pytest.raises(RuntimeError, match="Master container validation failed"):
            await service._validate_master_container()

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, service):
        """Test health check when service is healthy."""
        # Setup
        mock_container = MagicMock()
        # Mock two queries: tenant count and user count
        mock_container.query_items.side_effect = [[5], [12]]  # 5 tenants, 12 users
        service._master_container = mock_container

        # Execute
        result = await service.health_check()

        # Verify
        assert result["status"] == "healthy"
        assert result["master_container"] == "tenants"
        assert result["statistics"]["total_tenants"] == 5
        assert result["statistics"]["active_users"] == 12

    @pytest.mark.asyncio
    async def test_health_check_no_container(self, service):
        """Test health check when container not initialized."""
        # Setup
        service._master_container = None

        # Execute
        result = await service.health_check()

        # Verify
        assert result["status"] == "unhealthy"
        assert "Master container not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_health_check_query_fails(self, service):
        """Test health check when queries fail."""
        # Setup
        mock_container = MagicMock()
        mock_container.query_items.side_effect = Exception("Database error")
        service._master_container = mock_container

        # Execute
        result = await service.health_check()

        # Verify
        assert result["status"] == "unhealthy"
        assert "Database error" in result["error"]

    @pytest.mark.asyncio
    async def test_container_properties_include_all_indexes(self, service, mock_cosmos_service):
        """Test that created container includes all necessary composite indexes."""
        # Setup
        mock_container = MagicMock()
        mock_cosmos_service.get_container.side_effect = CosmosResourceNotFoundError(
            message="Container not found"
        )
        mock_cosmos_service.database.create_container.return_value = mock_container
        mock_container.query_items.return_value = [0]

        # Execute
        await service.initialize()

        # Verify
        call_args = mock_cosmos_service.database.create_container.call_args
        container_props = call_args.kwargs["indexing_policy"]
        composite_indexes = container_props["compositeIndexes"]

        # Check for expected composite indexes
        expected_indexes = [
            ["/partitionKey", "/type"],
            ["/tenant_id", "/type"],
            ["/user_id", "/type"],
            ["/performed_by", "/timestamp"],
        ]

        assert len(composite_indexes) == len(expected_indexes)

        for expected_paths in expected_indexes:
            # Find matching composite index
            found = False
            for composite_index in composite_indexes:
                index_paths = [idx["path"] for idx in composite_index]
                if all(path in index_paths for path in expected_paths):
                    found = True
                    break
            assert found, f"Expected composite index with paths {expected_paths} not found"
