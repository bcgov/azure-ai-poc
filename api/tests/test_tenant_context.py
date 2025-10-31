"""Tests for tenant context service."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.auth.models import KeycloakUser
from app.models.tenant_models import TenantUser, TenantUserRole
from app.services.tenant_context import TenantContext, TenantContextService


class TestTenantContext:
    """Test cases for tenant context."""

    def test_tenant_context_creation(self):
        """Test tenant context creation."""
        context = TenantContext(
            user_id="user-123",
            tenant_id="test-tenant",
            tenant_role=TenantUserRole.TENANT_USER_WRITE,
        )

        assert context.tenant_id == "test-tenant"
        assert context.tenant_role == TenantUserRole.TENANT_USER_WRITE
        assert context.is_super_admin_user is False

    def test_has_role_hierarchy(self):
        """Test role hierarchy checking."""
        context = TenantContext(
            user_id="user-123",
            tenant_id="test-tenant",
            tenant_role=TenantUserRole.TENANT_ADMIN,
        )

        # Tenant admin should have specific role check
        assert context.has_role(TenantUserRole.TENANT_ADMIN) is True
        assert context.has_role(TenantUserRole.SUPER_ADMIN) is False

    def test_super_admin_permissions(self):
        """Test super admin permissions."""
        context = TenantContext(
            user_id="admin-123",
            tenant_id="test-tenant",
            tenant_role=TenantUserRole.SUPER_ADMIN,
            is_super_admin_user=True,
        )

        # Super admin should have specific role and super admin status
        assert context.has_role(TenantUserRole.SUPER_ADMIN) is True
        assert context.is_super_admin() is True

    def test_permission_methods(self):
        """Test convenience permission methods."""
        context = TenantContext(
            user_id="user-123",
            tenant_id="test-tenant",
            tenant_role=TenantUserRole.TENANT_USER_WRITE,
        )

        assert context.can_read() is True
        assert context.can_write() is True
        assert context.can_manage_tenant() is False


class TestTenantContextService:
    """Test cases for tenant context service."""

    @pytest.fixture
    def service(self):
        """Create a tenant context service for testing."""
        with patch("app.services.tenant_context.get_multi_tenant_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_get_service.return_value = mock_service
            service = TenantContextService()
            service.tenant_service = mock_service
            return service

    @pytest.fixture
    def keycloak_user(self):
        """Create a test Keycloak user."""
        return KeycloakUser(
            sub="user-123",
            email="user@example.com",
            preferred_username="testuser",
            client_roles=["ai-poc-participant"],
        )

    @pytest.fixture
    def super_admin_user(self):
        """Create a test super admin user."""
        return KeycloakUser(
            sub="admin-123",
            email="admin@example.com",
            preferred_username="admin",
            client_roles=["azure-ai-poc-super-admin"],
        )

    @pytest.mark.asyncio
    async def test_get_tenant_context_success(self, service, keycloak_user):
        """Test successful tenant context retrieval."""
        tenant_user = TenantUser(
            id="tu-123",
            tenant_id="test-tenant",
            user_id="user-123",
            user_email="user@example.com",
            role=TenantUserRole.TENANT_USER_WRITE,
            assigned_by="admin@example.com",
            is_active=True,
        )

        service.tenant_service.get_tenant_user.return_value = tenant_user

        context = await service.get_tenant_context("user-123", "test-tenant")

        assert context.tenant_id == "test-tenant"
        assert context.tenant_role == TenantUserRole.TENANT_USER_WRITE
        assert context.is_super_admin_user is False

    @pytest.mark.asyncio
    async def test_get_tenant_context_unauthorized(self, service, keycloak_user):
        """Test unauthorized tenant access."""
        service.tenant_service.get_tenant_user.return_value = None

        with pytest.raises(ValueError) as exc_info:
            await service.get_tenant_context("user-123", "test-tenant")

        assert "Failed to get tenant context" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_tenant_context_super_admin(self, service, super_admin_user):
        """Test super admin tenant access."""
        # Mock the super admin check to return True for admin-123
        with patch.object(service, "_is_super_admin_by_id", return_value=True):
            context = await service.get_tenant_context("admin-123", "test-tenant")

        assert context.tenant_id == "test-tenant"
        # Super admin gets TENANT_ADMIN role in the service implementation
        assert context.tenant_role == TenantUserRole.TENANT_ADMIN
        assert context.is_super_admin_user is True

    @pytest.mark.asyncio
    async def test_get_user_tenants_regular_user(self, service, keycloak_user):
        """Test getting tenants for regular user."""
        tenant_users = [
            TenantUser(
                id="tu-123",
                tenant_id="tenant-1",
                user_id="user-123",
                user_email="user@example.com",
                role=TenantUserRole.TENANT_USER_READ,
                assigned_by="admin@example.com",
            ),
            TenantUser(
                id="tu-124",
                tenant_id="tenant-2",
                user_id="user-123",
                user_email="user@example.com",
                role=TenantUserRole.TENANT_ADMIN,
                assigned_by="admin@example.com",
            ),
        ]

        service.tenant_service.get_user_tenants.return_value = tenant_users

        result = await service.get_user_tenants_by_id("user-123")

        assert len(result) == 2
        assert result[0].tenant_id == "tenant-1"
        assert result[1].tenant_id == "tenant-2"

    @pytest.mark.asyncio
    async def test_get_default_tenant(self, service, keycloak_user):
        """Test getting default tenant for user."""
        tenant_users = [
            TenantUser(
                id="tu-123",
                tenant_id="tenant-1",
                user_id="user-123",
                user_email="user@example.com",
                role=TenantUserRole.TENANT_USER_READ,
                assigned_by="admin@example.com",
            )
        ]

        service.tenant_service.get_user_tenants.return_value = tenant_users

        default_tenant = await service.get_default_tenant_by_id("user-123")

        assert default_tenant == "tenant-1"

    @pytest.mark.asyncio
    async def test_get_default_tenant_no_tenants(self, service, keycloak_user):
        """Test getting default tenant when user has no tenants."""
        service.tenant_service.get_user_tenants.return_value = []

        default_tenant = await service.get_default_tenant_by_id("user-123")

        assert default_tenant is None

    def test_is_super_admin(self, service):
        """Test super admin detection."""
        # Test with actual super admin user IDs from the service logic
        assert service._is_super_admin_by_id("admin") is True
        assert service._is_super_admin_by_id("super-admin") is True
        assert service._is_super_admin_by_id("system-admin") is True
        assert service._is_super_admin_by_id("user-123") is False
        assert service._is_super_admin_by_id("random-user") is False

    @pytest.mark.asyncio
    async def test_extract_tenant_from_request_path_params(self, service):
        """Test tenant ID extraction from request path params."""
        request = Mock()
        request.headers.get.return_value = None  # No header
        request.query_params.get.return_value = None  # No query param
        request.path_params = {"tenant_id": "test-tenant"}

        tenant_id = await service.extract_tenant_from_request(request)
        assert tenant_id == "test-tenant"

    @pytest.mark.asyncio
    async def test_extract_tenant_from_request_headers(self, service):
        """Test tenant ID extraction from headers."""
        request = Mock()
        request.headers.get.return_value = "test-tenant"  # Header found first

        tenant_id = await service.extract_tenant_from_request(request)
        assert tenant_id == "test-tenant"

    @pytest.mark.asyncio
    async def test_extract_tenant_from_request_query_params(self, service):
        """Test tenant ID extraction from query params."""
        request = Mock()
        request.headers.get.return_value = None
        request.query_params.get.return_value = "query-tenant"
        request.path_params = {}

        tenant_id = await service.extract_tenant_from_request(request)
        assert tenant_id == "query-tenant"

    @pytest.mark.asyncio
    async def test_extract_tenant_from_request_no_tenant(self, service):
        """Test tenant ID extraction when no tenant is found."""
        request = Mock()
        request.headers.get.return_value = None
        request.query_params.get.return_value = None
        request.path_params = {}

        tenant_id = await service.extract_tenant_from_request(request)
        assert tenant_id is None

    def test_tenant_context_read_only_user(self):
        """Test tenant context for read-only user."""
        context = TenantContext(
            user_id="user-123",
            tenant_id="test-tenant",
            tenant_role=TenantUserRole.TENANT_USER_READ,
        )

        assert context.can_read() is True
        assert context.can_write() is False
        assert context.can_manage_tenant() is False

    def test_tenant_context_write_user(self):
        """Test tenant context for write user."""
        context = TenantContext(
            user_id="user-123",
            tenant_id="test-tenant",
            tenant_role=TenantUserRole.TENANT_USER_WRITE,
        )

        assert context.can_read() is True
        assert context.can_write() is True
        assert context.can_manage_tenant() is False

    def test_tenant_context_admin_user(self):
        """Test tenant context for admin user."""
        context = TenantContext(
            user_id="user-123",
            tenant_id="test-tenant",
            tenant_role=TenantUserRole.TENANT_ADMIN,
        )

        assert context.can_read() is True
        assert context.can_write() is True
        assert context.can_manage_tenant() is True
