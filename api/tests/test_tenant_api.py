"""
Tests for tenant management API endpoints.

This module tests all CRUD operations for tenants and tenant users,
including permission checking, error handling, and response validation.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from app.models.tenant_models import (
    CreateTenantRequest,
    CreateTenantUserRequest,
    Tenant,
    TenantStatus,
    TenantUser,
    TenantUserRole,
    UpdateTenantRequest,
    UpdateTenantUserRequest,
)


class TestTenantEndpoints:
    """Test tenant CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_tenant_success(
        self, async_client: AsyncClient, mock_super_admin_user, mock_multi_tenant_service
    ):
        """Test successful tenant creation."""
        # Mock the multi-tenant service
        mock_tenant = Tenant(
            id="tenant-123",
            name="test-tenant",
            display_name="Test Tenant",
            description="A test tenant",
            status=TenantStatus.ACTIVE,
            created_by="admin@example.com",
        )

        tenant_request = CreateTenantRequest(
            name="test-tenant",
            display_name="Test Tenant",
            description="A test tenant",
        )

        # Configure the mock service that's injected via dependency override
        mock_multi_tenant_service.create_tenant.return_value = mock_tenant

        response = await async_client.post(
            "/api/v1/tenants/",
            json=tenant_request.model_dump(),
        )

        # Debug output
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text}")

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "test-tenant"
        assert data["display_name"] == "Test Tenant"
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_tenant_unauthorized(self, async_client_regular_user: AsyncClient):
        """Test tenant creation without super admin role."""
        tenant_request = CreateTenantRequest(
            name="test-tenant",
            display_name="Test Tenant",
        )

        # Regular user should get 403 forbidden
        response = await async_client_regular_user.post(
            "/api/v1/tenants/",
            json=tenant_request.model_dump(),
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_list_tenants_success(self, async_client: AsyncClient, mock_multi_tenant_service):
        """Test successful tenant listing."""
        mock_tenants = [
            Tenant(
                id="tenant-1",
                name="tenant-one",
                display_name="Tenant One",
                status=TenantStatus.ACTIVE,
                created_by="admin@example.com",
            ),
            Tenant(
                id="tenant-2",
                name="tenant-two",
                display_name="Tenant Two",
                status=TenantStatus.ACTIVE,
                created_by="admin@example.com",
            ),
        ]

        # Configure the mock service via dependency override (no patches needed)
        mock_multi_tenant_service.list_tenants.return_value = mock_tenants

        response = await async_client.get("/api/v1/tenants/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "tenant-one"
        assert data[1]["name"] == "tenant-two"

    @pytest.mark.asyncio
    async def test_get_tenant_by_id_success(
        self, async_client: AsyncClient, mock_multi_tenant_service
    ):
        """Test successful tenant retrieval."""
        tenant_id = "tenant-123"
        mock_tenant = Tenant(
            id=tenant_id,
            name="test-tenant",
            display_name="Test Tenant",
            status=TenantStatus.ACTIVE,
            created_by="admin@example.com",
        )

        # Configure the mock service via dependency override
        mock_multi_tenant_service.get_tenant.return_value = mock_tenant

        response = await async_client.get(f"/api/v1/tenants/{tenant_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == tenant_id
        assert data["name"] == "test-tenant"

    @pytest.mark.asyncio
    async def test_get_tenant_not_found(self, async_client: AsyncClient, mock_super_admin_user):
        """Test tenant not found."""
        tenant_id = "nonexistent-tenant"

        with patch("app.auth.dependencies.get_tenant_context") as mock_auth:
            mock_auth.return_value = mock_super_admin_user

            with patch(
                "app.services.multi_tenant_service.get_multi_tenant_service"
            ) as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.get_tenant.return_value = None
                mock_service.return_value = mock_service_instance

                response = await async_client.get(f"/api/v1/tenants/{tenant_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Tenant not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_tenant_success(
        self, async_client: AsyncClient, mock_multi_tenant_service
    ):
        """Test successful tenant update."""
        tenant_id = "tenant-123"
        update_request = UpdateTenantRequest(
            display_name="Updated Tenant Name",
            description="Updated description",
        )

        mock_updated_tenant = Tenant(
            id=tenant_id,
            name="test-tenant",
            display_name="Updated Tenant Name",
            description="Updated description",
            status=TenantStatus.ACTIVE,
            created_by="admin@example.com",
        )

        # Configure the mock service via dependency override
        mock_multi_tenant_service.update_tenant.return_value = mock_updated_tenant

        response = await async_client.put(
            f"/api/v1/tenants/{tenant_id}",
            json=update_request.model_dump(),
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["display_name"] == "Updated Tenant Name"
        assert data["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_delete_tenant_success(self, async_client: AsyncClient, mock_super_admin_user):
        """Test successful tenant deletion."""
        tenant_id = "tenant-123"

        with patch("app.auth.dependencies.require_super_admin") as mock_auth:
            mock_auth.return_value = mock_super_admin_user

            with patch(
                "app.services.multi_tenant_service.get_multi_tenant_service"
            ) as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.delete_tenant.return_value = True
                mock_service.return_value = mock_service_instance

                response = await async_client.delete(f"/api/v1/tenants/{tenant_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestTenantUserEndpoints:
    """Test tenant user management operations."""

    @pytest.mark.asyncio
    async def test_add_tenant_user_success(
        self, async_client_tenant_admin: AsyncClient, mock_multi_tenant_service
    ):
        """Test successful tenant user addition."""
        tenant_id = "tenant-123"
        user_request = CreateTenantUserRequest(
            user_id="user-456",
            user_email="user@example.com",
            role=TenantUserRole.TENANT_USER_READ,
        )

        mock_tenant_user = TenantUser(
            id="tu-123",
            tenant_id=tenant_id,
            user_id="user-456",
            user_email="user@example.com",
            role=TenantUserRole.TENANT_USER_READ,
            assigned_by="admin@example.com",
        )

        # Configure the mock service via dependency override
        mock_multi_tenant_service.add_tenant_user.return_value = mock_tenant_user

        response = await async_client_tenant_admin.post(
            f"/api/v1/tenants/{tenant_id}/users",
            json=user_request.model_dump(),
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["user_id"] == "user-456"
        assert data["role"] == "tenant_user_read"

    @pytest.mark.asyncio
    async def test_list_tenant_users_success(
        self, async_client_tenant_admin: AsyncClient, mock_multi_tenant_service
    ):
        """Test successful tenant user listing."""
        tenant_id = "tenant-123"
        mock_users = [
            TenantUser(
                id="tu-1",
                tenant_id=tenant_id,
                user_id="user-1",
                user_email="user1@example.com",
                role=TenantUserRole.TENANT_USER_READ,
                assigned_by="admin@example.com",
            ),
            TenantUser(
                id="tu-2",
                tenant_id=tenant_id,
                user_id="user-2",
                user_email="user2@example.com",
                role=TenantUserRole.TENANT_USER_WRITE,
                assigned_by="admin@example.com",
            ),
        ]

        # Configure the mock service via dependency override
        mock_multi_tenant_service.list_tenant_users.return_value = mock_users

        response = await async_client_tenant_admin.get(f"/api/v1/tenants/{tenant_id}/users")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["role"] == "tenant_user_read"
        assert data[1]["role"] == "tenant_user_write"

    @pytest.mark.asyncio
    async def test_update_tenant_user_success(
        self, async_client_tenant_admin: AsyncClient, mock_multi_tenant_service
    ):
        """Test successful tenant user update."""
        tenant_id = "tenant-123"
        user_id = "user-456"
        update_request = UpdateTenantUserRequest(
            role=TenantUserRole.TENANT_USER_WRITE,
        )

        mock_updated_user = TenantUser(
            id="tu-123",
            tenant_id=tenant_id,
            user_id=user_id,
            user_email="user@example.com",
            role=TenantUserRole.TENANT_USER_WRITE,
            assigned_by="admin@example.com",
        )

        # Configure the mock service via dependency override
        mock_multi_tenant_service.update_tenant_user.return_value = mock_updated_user

        response = await async_client_tenant_admin.put(
            f"/api/v1/tenants/{tenant_id}/users/{user_id}",
            json=update_request.model_dump(),
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["role"] == "tenant_user_write"

    @pytest.mark.asyncio
    async def test_remove_tenant_user_success(
        self, async_client: AsyncClient, mock_tenant_admin_user
    ):
        """Test successful tenant user removal."""
        tenant_id = "tenant-123"
        user_id = "user-456"

        with patch("app.auth.dependencies.require_tenant_admin") as mock_auth:
            mock_auth.return_value = mock_tenant_admin_user

            with patch(
                "app.services.multi_tenant_service.get_multi_tenant_service"
            ) as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.remove_tenant_user.return_value = True
                mock_service.return_value = mock_service_instance

                response = await async_client.delete(f"/api/v1/tenants/{tenant_id}/users/{user_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestTenantStatsAndHealth:
    """Test tenant statistics and health endpoints."""

    @pytest.mark.asyncio
    async def test_get_tenant_stats_success(
        self, async_client: AsyncClient, mock_multi_tenant_service
    ):
        """Test successful tenant statistics retrieval."""
        mock_stats = {
            "tenant_count": 5,
            "active_tenants": 4,
            "total_users": 25,
            "total_documents": 150,
        }

        # Configure the mock service via dependency override
        mock_multi_tenant_service.get_tenant_stats.return_value = mock_stats

        response = await async_client.get("/api/v1/tenants/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["tenant_count"] == 5
        assert data["active_tenants"] == 4
        assert data["total_users"] == 25

    @pytest.mark.asyncio
    async def test_get_tenant_health_success(
        self, async_client_tenant_admin: AsyncClient, mock_multi_tenant_service
    ):
        """Test successful tenant health check."""
        tenant_id = "tenant-123"
        mock_health = {
            "tenant_id": tenant_id,
            "status": "healthy",
            "container_status": "healthy",
            "search_index_status": "healthy",
            "user_count": 10,
            "document_count": 50,
            "quota_usage": {"storage": 0.6, "users": 0.4},
        }

        # Configure the mock service via dependency override
        mock_multi_tenant_service.get_tenant_health.return_value = mock_health

        response = await async_client_tenant_admin.get(f"/api/v1/tenants/{tenant_id}/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["tenant_id"] == tenant_id
        assert data["status"] == "healthy"
        assert data["user_count"] == 10


# Fixtures
@pytest.fixture
def mock_super_admin_user():
    """Mock super admin user context."""
    from app.models.tenant_models import TenantUserRole
    from app.services.tenant_context import TenantContext

    return TenantContext(
        user_id="admin-123",
        tenant_id=None,
        tenant_role=TenantUserRole.SUPER_ADMIN,
        is_super_admin_user=True,
    )


@pytest.fixture
def mock_tenant_admin_user():
    """Mock tenant admin user context."""
    from app.models.tenant_models import TenantUserRole
    from app.services.tenant_context import TenantContext

    return TenantContext(
        user_id="tenant-admin-123",
        tenant_id="tenant-123",
        tenant_role=TenantUserRole.TENANT_ADMIN,
        is_super_admin_user=False,
    )


@pytest.fixture
def mock_regular_user():
    """Mock regular user context."""
    from app.models.tenant_models import TenantUserRole
    from app.services.tenant_context import TenantContext

    return TenantContext(
        user_id="user-123",
        tenant_id="tenant-123",
        tenant_role=TenantUserRole.TENANT_USER_READ,
        is_super_admin_user=False,
    )
