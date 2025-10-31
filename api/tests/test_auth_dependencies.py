"""Tests for enhanced authentication dependencies with multi-tenant support."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.auth.dependencies import (
    get_tenant_context,
    require_read_access,
    require_super_admin,
    require_tenant_admin,
    require_tenant_role,
    require_write_access,
)
from app.auth.models import KeycloakUser
from app.models.tenant_models import TenantUserRole
from app.services.tenant_context import TenantContext


class TestGetTenantContext:
    """Test get_tenant_context dependency."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock KeycloakUser."""
        return KeycloakUser(
            sub="user-123", preferred_username="testuser", client_roles=["ai-poc-participant"]
        )

    @pytest.fixture
    def mock_context_service(self, monkeypatch):
        """Mock the tenant context service."""
        mock_service = AsyncMock()

        def mock_get_service():
            return mock_service

        monkeypatch.setattr("app.auth.dependencies.get_tenant_context_service", mock_get_service)
        return mock_service

    @pytest.mark.asyncio
    async def test_get_tenant_context_success(self, mock_user, mock_context_service):
        """Test successful tenant context retrieval."""
        # Setup
        expected_context = TenantContext(
            user_id="user-123",
            tenant_id="tenant-1",
            tenant_role=TenantUserRole.TENANT_USER_READ,
            is_super_admin_user=False,
        )
        mock_context_service.get_tenant_context.return_value = expected_context

        # Execute
        result = await get_tenant_context(mock_user, "tenant-1")

        # Verify
        assert result == expected_context
        mock_context_service.get_tenant_context.assert_called_once_with("user-123", "tenant-1")

    @pytest.mark.asyncio
    async def test_get_tenant_context_no_tenant_id(self, mock_user, mock_context_service):
        """Test tenant context retrieval without tenant ID."""
        # Setup
        expected_context = TenantContext(
            user_id="user-123",
            tenant_id="default-tenant",
            tenant_role=TenantUserRole.TENANT_USER_READ,
            is_super_admin_user=False,
        )
        mock_context_service.get_tenant_context.return_value = expected_context

        # Execute
        result = await get_tenant_context(mock_user, None)

        # Verify
        assert result == expected_context
        mock_context_service.get_tenant_context.assert_called_once_with("user-123", None)

    @pytest.mark.asyncio
    async def test_get_tenant_context_access_denied(self, mock_user, mock_context_service):
        """Test tenant context retrieval with access denied."""
        # Setup
        mock_context_service.get_tenant_context.side_effect = ValueError("Access denied")

        # Execute & Verify
        with pytest.raises(HTTPException) as exc_info:
            await get_tenant_context(mock_user, "forbidden-tenant")

        assert exc_info.value.status_code == 403
        assert "Access denied" in str(exc_info.value.detail)


class TestRequireTenantRole:
    """Test require_tenant_role dependency factory."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock TenantContext."""
        context = MagicMock(spec=TenantContext)
        context.has_any_role.return_value = True
        return context

    @pytest.mark.asyncio
    async def test_require_tenant_role_success(self, mock_context):
        """Test successful role requirement check."""
        # Setup
        checker = require_tenant_role(TenantUserRole.TENANT_USER_READ, TenantUserRole.TENANT_ADMIN)

        # Execute
        result = await checker(mock_context)

        # Verify
        assert result == mock_context
        mock_context.has_any_role.assert_called_once_with(
            TenantUserRole.TENANT_USER_READ, TenantUserRole.TENANT_ADMIN
        )

    @pytest.mark.asyncio
    async def test_require_tenant_role_access_denied(self, mock_context):
        """Test role requirement check with access denied."""
        # Setup
        mock_context.has_any_role.return_value = False
        checker = require_tenant_role(TenantUserRole.TENANT_ADMIN)

        # Execute & Verify
        with pytest.raises(HTTPException) as exc_info:
            await checker(mock_context)

        assert exc_info.value.status_code == 403
        assert "tenant_admin" in str(exc_info.value.detail)

    def test_require_tenant_role_no_roles(self):
        """Test require_tenant_role with no roles provided."""
        with pytest.raises(ValueError):
            require_tenant_role()


class TestRequireSuperAdmin:
    """Test require_super_admin dependency."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock TenantContext."""
        context = MagicMock(spec=TenantContext)
        context.is_super_admin.return_value = True
        return context

    @pytest.mark.asyncio
    async def test_require_super_admin_success(self, mock_context):
        """Test successful super admin check."""
        # Setup
        checker = require_super_admin()

        # Execute
        result = await checker(mock_context)

        # Verify
        assert result == mock_context
        mock_context.is_super_admin.assert_called_once()

    @pytest.mark.asyncio
    async def test_require_super_admin_access_denied(self, mock_context):
        """Test super admin check with access denied."""
        # Setup
        mock_context.is_super_admin.return_value = False
        checker = require_super_admin()

        # Execute & Verify
        with pytest.raises(HTTPException) as exc_info:
            await checker(mock_context)

        assert exc_info.value.status_code == 403
        assert "Super admin required" in str(exc_info.value.detail)


class TestRequireTenantAdmin:
    """Test require_tenant_admin dependency."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock TenantContext."""
        context = MagicMock(spec=TenantContext)
        context.can_manage_tenant.return_value = True
        return context

    @pytest.mark.asyncio
    async def test_require_tenant_admin_success(self, mock_context):
        """Test successful tenant admin check."""
        # Setup
        checker = require_tenant_admin()

        # Execute
        result = await checker(mock_context)

        # Verify
        assert result == mock_context
        mock_context.can_manage_tenant.assert_called_once()

    @pytest.mark.asyncio
    async def test_require_tenant_admin_access_denied(self, mock_context):
        """Test tenant admin check with access denied."""
        # Setup
        mock_context.can_manage_tenant.return_value = False
        checker = require_tenant_admin()

        # Execute & Verify
        with pytest.raises(HTTPException) as exc_info:
            await checker(mock_context)

        assert exc_info.value.status_code == 403
        assert "Tenant admin or super admin required" in str(exc_info.value.detail)


class TestRequireReadAccess:
    """Test require_read_access dependency."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock TenantContext."""
        context = MagicMock(spec=TenantContext)
        context.can_read.return_value = True
        return context

    @pytest.mark.asyncio
    async def test_require_read_access_success(self, mock_context):
        """Test successful read access check."""
        # Setup
        checker = require_read_access()

        # Execute
        result = await checker(mock_context)

        # Verify
        assert result == mock_context
        mock_context.can_read.assert_called_once()

    @pytest.mark.asyncio
    async def test_require_read_access_denied(self, mock_context):
        """Test read access check with access denied."""
        # Setup
        mock_context.can_read.return_value = False
        checker = require_read_access()

        # Execute & Verify
        with pytest.raises(HTTPException) as exc_info:
            await checker(mock_context)

        assert exc_info.value.status_code == 403
        assert "Read access required" in str(exc_info.value.detail)


class TestRequireWriteAccess:
    """Test require_write_access dependency."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock TenantContext."""
        context = MagicMock(spec=TenantContext)
        context.can_write.return_value = True
        return context

    @pytest.mark.asyncio
    async def test_require_write_access_success(self, mock_context):
        """Test successful write access check."""
        # Setup
        checker = require_write_access()

        # Execute
        result = await checker(mock_context)

        # Verify
        assert result == mock_context
        mock_context.can_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_require_write_access_denied(self, mock_context):
        """Test write access check with access denied."""
        # Setup
        mock_context.can_write.return_value = False
        checker = require_write_access()

        # Execute & Verify
        with pytest.raises(HTTPException) as exc_info:
            await checker(mock_context)

        assert exc_info.value.status_code == 403
        assert "Write access required" in str(exc_info.value.detail)
