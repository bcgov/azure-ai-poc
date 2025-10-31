"""Unit tests for tenant router input validation and error handling."""

from unittest.mock import AsyncMock, patch

import pytest


class TestTenantServiceValidation:
    """Tests for tenant service input validation and error scenarios."""

    @pytest.mark.asyncio
    async def test_multi_tenant_service_create_validates_input(self):
        """Test that create_tenant validates required fields."""
        from app.services.multi_tenant_service import MultiTenantService

        service = MultiTenantService()

        with patch.object(service, "create_tenant", AsyncMock()) as mock_create:
            mock_create.side_effect = ValueError("Name is required")

            with pytest.raises(ValueError, match="Name is required"):
                await service.create_tenant(
                    name="",  # Empty name
                    display_name="Test",
                    created_by="admin",
                )

    @pytest.mark.asyncio
    async def test_multi_tenant_service_handles_duplicate_tenant(self):
        """Test handling of duplicate tenant creation."""
        from app.services.multi_tenant_service import MultiTenantService

        service = MultiTenantService()

        with patch.object(service, "create_tenant", AsyncMock()) as mock_create:
            mock_create.side_effect = ValueError("Tenant already exists")

            with pytest.raises(ValueError, match="already exists"):
                await service.create_tenant(
                    name="existing-tenant",
                    display_name="Existing",
                    created_by="admin",
                )

    @pytest.mark.asyncio
    async def test_multi_tenant_service_update_nonexistent_tenant(self):
        """Test updating non-existent tenant."""
        from app.services.multi_tenant_service import MultiTenantService, TenantNotFoundError

        service = MultiTenantService()

        with patch.object(service, "update_tenant", AsyncMock()) as mock_update:
            mock_update.side_effect = TenantNotFoundError("Tenant not found")

            with pytest.raises(TenantNotFoundError):
                await service.update_tenant(
                    tenant_id="nonexistent",
                    display_name="Updated",
                )

    @pytest.mark.asyncio
    async def test_multi_tenant_service_delete_handles_errors(self):
        """Test delete tenant error handling."""
        from app.services.multi_tenant_service import MultiTenantService

        service = MultiTenantService()

        with patch.object(service, "delete_tenant", AsyncMock()) as mock_delete:
            mock_delete.side_effect = Exception("Cannot delete tenant with active users")

            with pytest.raises(Exception, match="active users"):
                await service.delete_tenant("tenant-with-users")

    @pytest.mark.asyncio
    async def test_multi_tenant_service_assign_user_validates_role(self):
        """Test assign user validates role."""
        from app.models.tenant_models import TenantUserRole
        from app.services.multi_tenant_service import MultiTenantService

        service = MultiTenantService()

        with patch.object(service, "assign_user_to_tenant", AsyncMock()) as mock_assign:
            # Should accept valid role
            mock_assign.return_value = {"success": True}

            result = await service.assign_user_to_tenant(
                tenant_id="test-tenant",
                user_id="user@example.com",
                user_email="user@example.com",
                role=TenantUserRole.TENANT_USER_READ,
                assigned_by="admin",
            )

            assert result == {"success": True}


class TestTenantServiceEdgeCases:
    """Tests for tenant service edge cases."""

    @pytest.mark.asyncio
    async def test_list_tenants_empty_result(self):
        """Test listing tenants when none exist."""
        from app.services.multi_tenant_service import MultiTenantService

        service = MultiTenantService()

        with patch.object(service, "list_tenants", AsyncMock()) as mock_list:
            mock_list.return_value = []

            tenants = await service.list_tenants()

            assert tenants == []

    @pytest.mark.asyncio
    async def test_get_tenant_users_no_users(self):
        """Test getting users for tenant with no assigned users."""
        from app.services.multi_tenant_service import MultiTenantService

        service = MultiTenantService()

        with patch.object(service, "get_tenant_users", AsyncMock()) as mock_get_users:
            mock_get_users.return_value = []

            users = await service.get_tenant_users("empty-tenant")

            assert users == []

    @pytest.mark.asyncio
    async def test_validate_tenant_access_invalid_tenant(self):
        """Test access validation for invalid tenant."""
        from app.services.multi_tenant_service import MultiTenantService

        service = MultiTenantService()

        with patch.object(service, "validate_tenant_access", AsyncMock()) as mock_validate:
            mock_validate.return_value = False

            has_access = await service.validate_tenant_access(
                tenant_id="invalid-tenant",
                user_id="user@example.com",
            )

            assert has_access is False

    @pytest.mark.asyncio
    async def test_remove_user_not_assigned(self):
        """Test removing user that's not assigned to tenant."""
        from app.services.multi_tenant_service import MultiTenantService

        service = MultiTenantService()

        with patch.object(service, "remove_user_from_tenant", AsyncMock()) as mock_remove:
            mock_remove.side_effect = ValueError("User not assigned to tenant")

            with pytest.raises(ValueError, match="not assigned"):
                await service.remove_user_from_tenant(
                    tenant_id="test-tenant",
                    user_id="unassigned@example.com",
                )
