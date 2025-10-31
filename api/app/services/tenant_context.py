"""
Tenant context management for multi-tenant operations.

This module provides functionality to:
- Extract tenant context from user IDs and tenant identifiers
- Resolve user-tenant relationships
- Provide tenant-aware context management
"""

from fastapi import Request
from pydantic import BaseModel

from app.core.logger import get_logger
from app.models.tenant_models import TenantUser, TenantUserRole
from app.services.multi_tenant_service import get_multi_tenant_service

logger = get_logger(__name__)


class TenantContext(BaseModel):
    """Tenant context for request processing."""

    user_id: str
    tenant_id: str | None = None
    tenant_role: TenantUserRole | None = None
    is_super_admin_user: bool = False

    def is_super_admin(self) -> bool:
        """Check if user is a super admin."""
        return self.is_super_admin_user

    def has_role(self, role: TenantUserRole) -> bool:
        """Check if user has specific tenant role."""
        return self.tenant_role == role

    def has_any_role(self, *roles: TenantUserRole) -> bool:
        """Check if user has any of the specified roles."""
        return self.tenant_role in roles

    def can_read(self) -> bool:
        """Check if user can read tenant data."""
        if self.is_super_admin():
            return True
        return self.tenant_role in [
            TenantUserRole.TENANT_USER_READ,
            TenantUserRole.TENANT_USER_WRITE,
            TenantUserRole.TENANT_ADMIN,
        ]

    def can_write(self) -> bool:
        """Check if user can write tenant data."""
        if self.is_super_admin():
            return True
        return self.tenant_role in [
            TenantUserRole.TENANT_USER_WRITE,
            TenantUserRole.TENANT_ADMIN,
        ]

    def can_manage_tenant(self) -> bool:
        """Check if user can manage tenant (admin operations)."""
        if self.is_super_admin():
            return True
        return self.tenant_role == TenantUserRole.TENANT_ADMIN

    def can_manage_users(self) -> bool:
        """Check if user can manage other users in tenant."""
        if self.is_super_admin():
            return True
        return self.tenant_role in [
            TenantUserRole.TENANT_USER_WRITE,
            TenantUserRole.TENANT_ADMIN,
        ]


class TenantContextService:
    """Service for managing tenant context."""

    def __init__(self):
        """Initialize the service."""
        self.tenant_service = get_multi_tenant_service()

    async def get_tenant_context(self, user_id: str, tenant_id: str | None = None) -> TenantContext:
        """Get tenant context for a user.

        Args:
            user_id: User identifier from JWT token
            tenant_id: Optional tenant ID to check access for

        Returns:
            TenantContext with user's permissions for the tenant

        Raises:
            ValueError: If user has no access to the specified tenant
        """
        logger.info("Getting tenant context", user_id=user_id, tenant_id=tenant_id)

        # Check if user is super admin
        is_super_admin = self._is_super_admin_by_id(user_id)

        if is_super_admin:
            return TenantContext(
                user_id=user_id,
                tenant_id=tenant_id,
                tenant_role=TenantUserRole.TENANT_ADMIN,  # Super admin has all permissions
                is_super_admin_user=True,
            )

        # If no tenant specified, get default tenant
        if not tenant_id:
            tenant_id = await self.get_default_tenant_by_id(user_id)
            if not tenant_id:
                raise ValueError("User has no access to any tenant")

        # Get user's role in the specified tenant
        try:
            tenant_user = await self.tenant_service.get_tenant_user(tenant_id, user_id)
            if not tenant_user:
                raise ValueError(f"User has no access to tenant: {tenant_id}")

            return TenantContext(
                user_id=user_id,
                tenant_id=tenant_id,
                tenant_role=tenant_user.role,
                is_super_admin_user=False,
            )

        except Exception as e:
            logger.error(
                "Failed to get tenant context",
                user_id=user_id,
                tenant_id=tenant_id,
                error=str(e),
            )
            raise ValueError(f"Failed to get tenant context: {str(e)}") from e

    async def get_user_tenants_by_id(self, user_id: str) -> list[TenantUser]:
        """Get all tenants for a user by user ID.

        Args:
            user_id: User identifier

        Returns:
            List of tenant-user relationships
        """
        try:
            return await self.tenant_service.get_user_tenants(user_id)
        except Exception as e:
            logger.error("Failed to get user tenants", user_id=user_id, error=str(e))
            return []

    async def get_default_tenant_by_id(self, user_id: str) -> str | None:
        """Get default tenant for a user by user ID.

        Args:
            user_id: User identifier

        Returns:
            Default tenant ID or None if user has no tenants
        """
        tenant_users = await self.get_user_tenants_by_id(user_id)
        if not tenant_users:
            return None
        # Return first tenant as default
        return tenant_users[0].tenant_id

    def _is_super_admin_by_id(self, user_id: str) -> bool:
        """Check if user is super admin by user ID.

        Args:
            user_id: User identifier

        Returns:
            True if user is super admin

        Note:
            This is a simplified implementation. In production, this should
            check against a proper role/permission system.
        """
        # TODO: Implement proper super admin check based on roles/permissions
        # For now, we'll use a simple check (this should be configurable)
        super_admin_users = ["admin", "super-admin", "system-admin"]
        return user_id in super_admin_users

    async def extract_tenant_from_request(self, request: Request) -> str | None:
        """Extract tenant ID from request headers, query params, or path.

        Args:
            request: FastAPI request object

        Returns:
            Tenant ID if found, None otherwise
        """
        # Check header first
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id

        # Check query parameters
        tenant_id = request.query_params.get("tenant_id")
        if tenant_id:
            return tenant_id

        # Check path parameters (if tenant_id is in the path)
        path_params = request.path_params
        if "tenant_id" in path_params:
            return path_params["tenant_id"]

        return None


# Global tenant context service instance
_tenant_context_service: TenantContextService | None = None


def get_tenant_context_service() -> TenantContextService:
    """Get the global tenant context service instance."""
    global _tenant_context_service
    if _tenant_context_service is None:
        _tenant_context_service = TenantContextService()
    return _tenant_context_service
