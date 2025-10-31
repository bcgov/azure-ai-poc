"""FastAPI dependencies for authentication and authorization."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.models import KeycloakUser
from app.auth.service import get_auth_service
from app.core.logger import get_logger
from app.models.tenant_models import TenantUserRole
from app.services.tenant_context import TenantContext, get_tenant_context_service

logger = get_logger(__name__)

# Security scheme for bearer token
security = HTTPBearer()


async def get_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> str:
    """Extract bearer token from Authorization header."""
    return credentials.credentials


async def get_current_user(token: Annotated[str, Depends(get_token)]) -> KeycloakUser:
    """Get current authenticated user from JWT token."""
    auth_service = get_auth_service()
    return await auth_service.validate_token(token)


def require_roles(*required_roles: str):
    """Dependency factory enforcing that user has at least one of the given roles.

    Usage: Depends(require_roles("roleA", "roleB"))
    """
    if not required_roles:
        raise ValueError("require_roles() requires at least one role")

    roles = tuple(required_roles)

    async def checker(
        current_user: Annotated[KeycloakUser, Depends(get_current_user)],
    ) -> KeycloakUser:
        user_roles = current_user.client_roles or []
        if not user_roles or not any(r in user_roles for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(roles)}",
            )
        return current_user

    return checker


# Common role dependencies
RequireAuth = Depends(get_current_user)
RequireParticipant = Depends(require_roles("ai-poc-participant"))


# Tenant-aware authentication dependencies


async def get_tenant_context(
    current_user: Annotated[KeycloakUser, Depends(get_current_user)],
    tenant_id: str | None = None,
) -> TenantContext:
    """Get tenant context for the current user.

    Args:
        current_user: Authenticated user from JWT token
        tenant_id: Optional tenant ID (from path/query params)

    Returns:
        TenantContext with user's tenant information and permissions

    Raises:
        HTTPException: If user has no access to the specified tenant
    """
    context_service = get_tenant_context_service()
    try:
        context = await context_service.get_tenant_context(current_user.sub, tenant_id)
        return context
    except ValueError as e:
        logger.error(
            "Tenant context error", user_id=current_user.sub, tenant_id=tenant_id, error=str(e)
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


def require_tenant_role(*required_roles: TenantUserRole):
    """Dependency factory enforcing tenant-specific role requirements.

    Usage: Depends(require_tenant_role(TenantUserRole.TENANT_ADMIN, TenantUserRole.USER))
    """
    if not required_roles:
        raise ValueError("require_tenant_role() requires at least one role")

    roles = tuple(required_roles)

    async def checker(
        tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    ) -> TenantContext:
        if not tenant_context.has_any_role(*roles):
            role_names = [role.value for role in roles]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required tenant roles: {', '.join(role_names)}",
            )
        return tenant_context

    return checker


def require_super_admin():
    """Dependency requiring super admin access."""

    async def checker(
        tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    ) -> TenantContext:
        if not tenant_context.is_super_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Super admin required."
            )
        return tenant_context

    return checker


def require_tenant_admin():
    """Dependency requiring tenant admin or super admin access."""

    async def checker(
        tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    ) -> TenantContext:
        if not tenant_context.can_manage_tenant():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Tenant admin or super admin required.",
            )
        return tenant_context

    return checker


def require_read_access():
    """Dependency requiring at least read access to tenant."""

    async def checker(
        tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    ) -> TenantContext:
        if not tenant_context.can_read():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Read access required."
            )
        return tenant_context

    return checker


def require_write_access():
    """Dependency requiring write access to tenant."""

    async def checker(
        tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    ) -> TenantContext:
        if not tenant_context.can_write():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Write access required.",
            )
        return tenant_context

    return checker


# Common tenant role dependencies
RequireTenantContext = Depends(get_tenant_context)
RequireSuperAdmin = Depends(require_super_admin())
RequireTenantAdmin = Depends(require_tenant_admin())
RequireReadAccess = Depends(require_read_access())
RequireWriteAccess = Depends(require_write_access())
