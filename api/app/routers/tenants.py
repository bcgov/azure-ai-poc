"""
Tenant management API endpoints.

This router provides CRUD operations for tenants and tenant users:
- Create, read, update, delete tenants
- Manage tenant users and roles
- Tenant health and statistics
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.dependencies import (
    get_tenant_context,
    require_super_admin,
    require_tenant_admin,
)
from app.models.tenant_models import (
    CreateTenantRequest,
    CreateTenantUserRequest,
    TenantResponse,
    TenantUserResponse,
    TenantUserRole,
    UpdateTenantRequest,
)
from app.services.multi_tenant_service import get_multi_tenant_service
from app.services.search_index_service import get_search_index_service
from app.services.tenant_context import TenantContext

router = APIRouter(prefix="/tenants", tags=["tenants"])


class TenantStatsResponse(BaseModel):
    """Response model for tenant statistics."""

    tenant_count: int
    active_tenants: int
    total_users: int
    total_documents: int


class TenantHealthResponse(BaseModel):
    """Response model for tenant health check."""

    tenant_id: str
    status: str
    container_status: str
    search_index_status: str
    user_count: int
    document_count: int
    quota_usage: dict[str, Any]


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    request: CreateTenantRequest,
    current_user: dict = Depends(require_super_admin),
    multi_tenant_service=Depends(get_multi_tenant_service),
) -> TenantResponse:
    """Create a new tenant."""
    try:
        tenant = await multi_tenant_service.create_tenant(
            name=request.name,
            display_name=request.display_name,
            description=request.description,
            quotas=request.quotas,
            metadata=request.metadata,
            created_by=current_user.user_id,
        )
        return TenantResponse.from_tenant(tenant)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tenant: {str(e)}",
        ) from e


@router.get("/", response_model=list[TenantResponse])
async def list_tenants(
    current_user: dict = Depends(require_super_admin),
    multi_tenant_service=Depends(get_multi_tenant_service),
    limit: int = 100,
) -> list[TenantResponse]:
    """List all tenants."""
    try:
        tenants = await multi_tenant_service.list_tenants(limit=limit)
        return [TenantResponse.from_tenant(tenant) for tenant in tenants]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tenants: {str(e)}",
        ) from e


@router.get("/stats", response_model=TenantStatsResponse)
async def get_tenant_stats(
    current_user: dict = Depends(require_super_admin),
    multi_tenant_service=Depends(get_multi_tenant_service),
) -> TenantStatsResponse:
    """Get system-wide tenant statistics."""
    try:
        stats = await multi_tenant_service.get_tenant_stats()
        return TenantStatsResponse(**stats)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant stats: {str(e)}",
        ) from e


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    current_user: dict = Depends(require_tenant_admin),
    tenant_context: TenantContext = Depends(get_tenant_context),
    multi_tenant_service=Depends(get_multi_tenant_service),
) -> TenantResponse:
    """Get tenant details."""
    # Verify user has access to this tenant
    if tenant_context.tenant_id != tenant_id and not tenant_context.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant",
        )

    try:
        tenant = await multi_tenant_service.get_tenant(tenant_id)
        return TenantResponse.from_tenant(tenant)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant not found: {str(e)}",
        ) from e


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    request: UpdateTenantRequest,
    current_user: dict = Depends(require_tenant_admin),
    tenant_context: TenantContext = Depends(get_tenant_context),
    multi_tenant_service=Depends(get_multi_tenant_service),
) -> TenantResponse:
    """Update tenant information."""
    # Verify user has access to this tenant
    if tenant_context.tenant_id != tenant_id and not tenant_context.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant",
        )

    try:
        # Only allow non-null values to be updated
        updates = {k: v for k, v in request.model_dump().items() if v is not None}

        tenant = await multi_tenant_service.update_tenant(
            tenant_id=tenant_id,
            updates=updates,
            updated_by=current_user.user_id,
        )
        return TenantResponse.from_tenant(tenant)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tenant: {str(e)}",
        ) from e


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str,
    current_user: dict = Depends(require_super_admin),
    multi_tenant_service=Depends(get_multi_tenant_service),
) -> None:
    """Delete a tenant and all associated resources."""
    try:
        await multi_tenant_service.delete_tenant(
            tenant_id=tenant_id,
            deleted_by=current_user.user_id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tenant: {str(e)}",
        ) from e


@router.post(
    "/{tenant_id}/users",
    response_model=TenantUserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_tenant_user(
    tenant_id: str,
    request: CreateTenantUserRequest,
    current_user: dict = Depends(require_tenant_admin),
    tenant_context: TenantContext = Depends(get_tenant_context),
    multi_tenant_service=Depends(get_multi_tenant_service),
) -> TenantUserResponse:
    """Add a user to a tenant."""
    # Verify user has access to this tenant
    if tenant_context.tenant_id != tenant_id and not tenant_context.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant",
        )

    try:
        tenant_user = await multi_tenant_service.add_tenant_user(
            tenant_id=tenant_id,
            user_id=request.user_id,
            user_email=request.user_email,
            role=request.role,
            assigned_by=current_user.user_id,
        )
        return TenantUserResponse.from_tenant_user(tenant_user)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add user to tenant: {str(e)}",
        ) from e


@router.get("/{tenant_id}/users", response_model=list[TenantUserResponse])
async def list_tenant_users(
    tenant_id: str,
    current_user: dict = Depends(require_tenant_admin),
    tenant_context: TenantContext = Depends(get_tenant_context),
    multi_tenant_service=Depends(get_multi_tenant_service),
) -> list[TenantUserResponse]:
    """List users in a tenant."""
    # Verify user has access to this tenant
    if tenant_context.tenant_id != tenant_id and not tenant_context.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant",
        )

    try:
        tenant_users = await multi_tenant_service.list_tenant_users(tenant_id)
        return [TenantUserResponse.from_tenant_user(user) for user in tenant_users]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tenant users: {str(e)}",
        ) from e


@router.get("/{tenant_id}/users/{user_id}", response_model=TenantUserResponse)
async def get_tenant_user(
    tenant_id: str,
    user_id: str,
    current_user: dict = Depends(require_tenant_admin),
    tenant_context: TenantContext = Depends(get_tenant_context),
    multi_tenant_service=Depends(get_multi_tenant_service),
) -> TenantUserResponse:
    """Get tenant user details."""
    # Verify user has access to this tenant
    if tenant_context.tenant_id != tenant_id and not tenant_context.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant",
        )

    try:
        tenant_user = await multi_tenant_service.get_tenant_user(tenant_id, user_id)
        if not tenant_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in tenant",
            )
        return TenantUserResponse.from_tenant_user(tenant_user)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant user: {str(e)}",
        ) from e


class UpdateTenantUserRequest(BaseModel):
    """Request model for updating tenant user."""

    role: TenantUserRole | None = None


@router.put("/{tenant_id}/users/{user_id}", response_model=TenantUserResponse)
async def update_tenant_user(
    tenant_id: str,
    user_id: str,
    request: UpdateTenantUserRequest,
    current_user: dict = Depends(require_tenant_admin),
    tenant_context: TenantContext = Depends(get_tenant_context),
    multi_tenant_service=Depends(get_multi_tenant_service),
) -> TenantUserResponse:
    """Update tenant user role."""
    # Verify user has access to this tenant
    if tenant_context.tenant_id != tenant_id and not tenant_context.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant",
        )

    try:
        # Only allow non-null values to be updated
        updates = {k: v for k, v in request.model_dump().items() if v is not None}

        tenant_user = await multi_tenant_service.update_tenant_user(
            tenant_id=tenant_id,
            user_id=user_id,
            updates=updates,
        )

        if not tenant_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in tenant",
            )

        return TenantUserResponse.from_tenant_user(tenant_user)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tenant user: {str(e)}",
        ) from e


@router.delete("/{tenant_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_tenant_user(
    tenant_id: str,
    user_id: str,
    current_user: dict = Depends(require_tenant_admin),
    tenant_context: TenantContext = Depends(get_tenant_context),
    multi_tenant_service=Depends(get_multi_tenant_service),
) -> None:
    """Remove a user from a tenant."""
    # Verify user has access to this tenant
    if tenant_context.tenant_id != tenant_id and not tenant_context.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant",
        )

    try:
        success = await multi_tenant_service.remove_tenant_user(tenant_id, user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in tenant",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove user from tenant: {str(e)}",
        ) from e


@router.get("/{tenant_id}/health", response_model=TenantHealthResponse)
async def get_tenant_health(
    tenant_id: str,
    current_user: dict = Depends(require_tenant_admin),
    tenant_context: TenantContext = Depends(get_tenant_context),
    multi_tenant_service=Depends(get_multi_tenant_service),
) -> TenantHealthResponse:
    """Get tenant health status."""
    # Verify user has access to this tenant
    if tenant_context.tenant_id != tenant_id and not tenant_context.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant",
        )

    try:
        health = await multi_tenant_service.get_tenant_health(tenant_id)
        if not health:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found",
            )
        return TenantHealthResponse(**health)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant health: {str(e)}",
        ) from e


# Search Index Management Endpoints


@router.post("/{tenant_id}/search-index", status_code=status.HTTP_201_CREATED)
async def create_tenant_search_index(
    tenant_id: str,
    context: TenantContext = Depends(get_tenant_context),
    multi_tenant_service=Depends(get_multi_tenant_service),
    search_index_service=Depends(get_search_index_service),
):
    """Create search index for a tenant."""
    # Check permissions - tenant admin or super admin
    if not (context.can_manage_tenant() or context.is_super_admin()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to manage search index",
        )

    try:
        # Get tenant to ensure it exists
        tenant = await multi_tenant_service.get_tenant(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found",
            )

        # Create search index
        success = await search_index_service.create_tenant_index(tenant)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create search index",
            )

        return {"message": "Search index created successfully", "tenant_id": tenant_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create search index: {str(e)}",
        ) from e


@router.delete("/{tenant_id}/search-index", status_code=status.HTTP_200_OK)
async def delete_tenant_search_index(
    tenant_id: str,
    context: TenantContext = Depends(get_tenant_context),
    search_index_service=Depends(get_search_index_service),
):
    """Delete search index for a tenant."""
    # Check permissions - tenant admin or super admin
    if not (context.can_manage_tenant() or context.is_super_admin()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to manage search index",
        )

    try:
        # Delete search index
        success = await search_index_service.delete_tenant_index(tenant_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete search index",
            )

        return {"message": "Search index deleted successfully", "tenant_id": tenant_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete search index: {str(e)}",
        ) from e


@router.get("/{tenant_id}/search-index/stats")
async def get_tenant_search_index_stats(
    tenant_id: str,
    context: TenantContext = Depends(get_tenant_context),
    search_index_service=Depends(get_search_index_service),
):
    """Get search index statistics for a tenant."""
    # Check permissions - tenant user or above
    if not (context.can_read() or context.is_super_admin()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view search index stats",
        )

    try:
        stats = await search_index_service.get_tenant_index_stats(tenant_id)
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Search index not found for tenant",
            )

        return stats

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get search index stats: {str(e)}",
        ) from e


@router.post("/{tenant_id}/search-index/recreate", status_code=status.HTTP_200_OK)
async def recreate_tenant_search_index(
    tenant_id: str,
    context: TenantContext = Depends(get_tenant_context),
    multi_tenant_service=Depends(get_multi_tenant_service),
    search_index_service=Depends(get_search_index_service),
):
    """Recreate search index for a tenant (delete and create)."""
    # Check permissions - tenant admin or super admin
    if not (context.can_manage_tenant() or context.is_super_admin()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to manage search index",
        )

    try:
        # Get tenant to ensure it exists
        tenant = await multi_tenant_service.get_tenant(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found",
            )

        # Recreate search index
        success = await search_index_service.recreate_tenant_index(tenant)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to recreate search index",
            )

        return {"message": "Search index recreated successfully", "tenant_id": tenant_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to recreate search index: {str(e)}",
        ) from e


@router.get("/search-indexes", dependencies=[Depends(require_super_admin)])
async def list_all_tenant_search_indexes(
    search_index_service=Depends(get_search_index_service),
):
    """List all tenant search indexes (super admin only)."""
    try:
        indexes = await search_index_service.list_tenant_indexes()
        return {"indexes": indexes, "total": len(indexes)}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list search indexes: {str(e)}",
        ) from e
