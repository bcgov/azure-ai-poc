"""
Multi-tenant service for managing tenant isolation and operations.

This service provides:
- Tenant CRUD operations
- Dynamic container and search index management
- Tenant-user relationship management
- Quota tracking and enforcement
- Audit logging
"""

import uuid
from datetime import datetime
from typing import Any

from azure.cosmos import ContainerProxy
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError

from app.core.logger import get_logger
from app.models.tenant_models import (
    AuditLog,
    Tenant,
    TenantStatus,
    TenantUser,
    TenantUserRole,
)
from app.services.azure_search_service import get_azure_search_service
from app.services.cosmos_db_service import get_cosmos_db_service

logger = get_logger(__name__)

# Constants
MASTER_CONTAINER_NAME = "tenants"
TENANT_CONTAINER_PREFIX = "tenant"
SEARCH_INDEX_PREFIX = "documents"


class TenantNotFoundError(Exception):
    """Raised when a tenant is not found."""

    pass


class TenantUserNotFoundError(Exception):
    """Raised when a tenant user relationship is not found."""

    pass


class QuotaExceededError(Exception):
    """Raised when a quota limit is exceeded."""

    pass


class MultiTenantService:
    """Service for managing multi-tenant operations."""

    def __init__(self):
        """Initialize the multi-tenant service."""
        self._cosmos_service = get_cosmos_db_service()
        self._search_service = get_azure_search_service()
        self._master_container: ContainerProxy | None = None

    async def initialize(self) -> None:
        """Initialize the multi-tenant service."""
        logger.info("Initializing multi-tenant service...")

        # Ensure master container exists
        await self._ensure_master_container()

        # Validate master container health
        await self._validate_master_container()

        logger.info("Multi-tenant service initialized successfully")

    async def _ensure_master_container(self) -> None:
        """Ensure the master container exists for tenant metadata."""
        try:
            # Try to get existing master container and verify it exists
            container = self._cosmos_service.get_container(MASTER_CONTAINER_NAME)

            # Try to read container properties to verify it actually exists
            _ = container.read()

            # If we get here, container exists
            self._master_container = container
            logger.info("Master container exists", container_name=MASTER_CONTAINER_NAME)
        except (CosmosResourceNotFoundError, CosmosHttpResponseError) as e:
            # Log the exception details for debugging
            logger.info(
                "Container not found, checking exception details",
                exception_type=type(e).__name__,
                has_status_code=hasattr(e, "status_code"),
                status_code=getattr(e, "status_code", None),
            )

            # Check if it's a not found error (status code 404 or CosmosResourceNotFoundError)
            is_not_found = isinstance(e, CosmosResourceNotFoundError) or (
                hasattr(e, "status_code") and e.status_code == 404
            )

            if is_not_found:
                # Create master container if it doesn't exist
                logger.info("Creating master container", container_name=MASTER_CONTAINER_NAME)

                # Create container with appropriate partition key and indexing
                container_properties = {
                    "id": MASTER_CONTAINER_NAME,
                    "partitionKey": {"paths": ["/partitionKey"], "kind": "Hash"},
                    "indexingPolicy": {
                        "indexingMode": "consistent",
                        "includedPaths": [{"path": "/*"}],
                        "excludedPaths": [{"path": "/embedding/?"}],
                        "compositeIndexes": [
                            [
                                {"path": "/partitionKey", "order": "ascending"},
                                {"path": "/type", "order": "ascending"},
                            ],
                            [
                                {"path": "/tenant_id", "order": "ascending"},
                                {"path": "/type", "order": "ascending"},
                            ],
                            [
                                {"path": "/user_id", "order": "ascending"},
                                {"path": "/type", "order": "ascending"},
                            ],
                            [
                                {"path": "/performed_by", "order": "ascending"},
                                {"path": "/timestamp", "order": "descending"},
                            ],
                        ],
                    },
                }

                # Use database client to create container since cosmos service
                # doesn't have create_container method
                container = self._cosmos_service.database.create_container(
                    id=MASTER_CONTAINER_NAME,
                    partition_key=container_properties["partitionKey"],
                    indexing_policy=container_properties["indexingPolicy"],
                )
                self._master_container = container

                logger.info(
                    "Master container created successfully", container_name=MASTER_CONTAINER_NAME
                )
            else:
                # Re-raise if it's not a not-found error
                logger.error(
                    "Failed to access master container",
                    error=str(e),
                    exception_type=type(e).__name__,
                )
                raise

    async def _validate_master_container(self) -> None:
        """Validate master container health and basic functionality."""
        if not self._master_container:
            raise RuntimeError("Master container not initialized")

        try:
            # Test basic query functionality
            test_query = "SELECT VALUE COUNT(1) FROM c WHERE c.type = 'tenant'"
            results = list(
                self._master_container.query_items(
                    query=test_query, enable_cross_partition_query=True
                )
            )

            tenant_count = results[0] if results else 0
            logger.info("Master container validated", tenant_count=tenant_count)

        except Exception as e:
            logger.error("Master container validation failed", error=str(e))
            raise RuntimeError(f"Master container validation failed: {str(e)}") from e

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on multi-tenant service."""
        try:
            if not self._master_container:
                return {"status": "unhealthy", "error": "Master container not initialized"}

            # Check master container accessibility
            test_query = "SELECT VALUE COUNT(1) FROM c WHERE c.type = 'tenant'"
            results = list(
                self._master_container.query_items(
                    query=test_query, enable_cross_partition_query=True
                )
            )

            tenant_count = results[0] if results else 0

            # Get basic statistics
            user_query = (
                "SELECT VALUE COUNT(1) FROM c WHERE c.type = 'tenant_user' AND c.is_active = true"
            )
            user_results = list(
                self._master_container.query_items(
                    query=user_query, enable_cross_partition_query=True
                )
            )

            active_users = user_results[0] if user_results else 0

            return {
                "status": "healthy",
                "master_container": MASTER_CONTAINER_NAME,
                "statistics": {
                    "total_tenants": tenant_count,
                    "active_users": active_users,
                },
            }

        except Exception as e:
            logger.error("Multi-tenant service health check failed", error=str(e))
            return {"status": "unhealthy", "error": str(e)}

    async def create_tenant(
        self,
        name: str,
        display_name: str | None = None,
        description: str | None = None,
        quotas: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        created_by: str | None = None,
    ) -> Tenant:
        """Create a new tenant with isolated resources."""
        tenant_id = str(uuid.uuid4())
        logger.info("Creating tenant", tenant_id=tenant_id, name=name, created_by=created_by)

        # Create tenant object
        tenant = Tenant(
            id=tenant_id,
            name=name,
            display_name=display_name or name,
            description=description,
            created_by=created_by,
            quotas=quotas or {},
            metadata=metadata or {},
        )

        try:
            # Store tenant in master container
            self._master_container.create_item(tenant.model_dump())

            # Create dedicated container for tenant
            await self._create_tenant_container(tenant_id)

            # Create dedicated search index for tenant
            await self._create_tenant_search_index(tenant_id)

            # Log tenant creation
            await self._log_audit_action(
                action="tenant.created",
                performed_by=created_by,
                tenant_id=tenant_id,
                details={"tenant_name": name, "description": description},
            )

            logger.info("Tenant created successfully", tenant_id=tenant_id)
            return tenant

        except Exception as e:
            logger.error("Failed to create tenant", tenant_id=tenant_id, error=str(e))
            # Cleanup on failure
            await self._cleanup_tenant_resources(tenant_id)
            raise

    async def _create_tenant_container(self, tenant_id: str) -> ContainerProxy:
        """Create a dedicated Cosmos DB container for a tenant."""
        container_name = f"{TENANT_CONTAINER_PREFIX}-{tenant_id}"

        logger.info("Creating tenant container", tenant_id=tenant_id, container_name=container_name)

        # Container configuration optimized for document storage
        container_properties = {
            "id": container_name,
            "partitionKey": {"paths": ["/partitionKey"], "kind": "Hash"},
            "indexingPolicy": {
                "indexingMode": "consistent",
                "includedPaths": [{"path": "/*"}],
                "excludedPaths": [{"path": "/embedding/?"}],
                "compositeIndexes": [
                    [
                        {"path": "/partitionKey", "order": "ascending"},
                        {"path": "/type", "order": "ascending"},
                    ],
                    [
                        {"path": "/documentId", "order": "ascending"},
                        {"path": "/partitionKey", "order": "ascending"},
                        {"path": "/type", "order": "ascending"},
                    ],
                    [
                        {"path": "/uploadedAt", "order": "descending"},
                        {"path": "/type", "order": "ascending"},
                    ],
                ],
            },
        }

        container = await self._cosmos_service.create_container(
            container_name=container_name,
            partition_key_path="/partitionKey",
            container_properties=container_properties,
        )

        logger.info("Tenant container created", tenant_id=tenant_id, container_name=container_name)
        return container

    async def _create_tenant_search_index(self, tenant_id: str) -> None:
        """Create a dedicated Azure AI Search index for a tenant."""
        index_name = f"{SEARCH_INDEX_PREFIX}-{tenant_id}"

        logger.info("Creating tenant search index", tenant_id=tenant_id, index_name=index_name)

        # Create search index with document schema
        await self._search_service.create_index(index_name)

        logger.info("Tenant search index created", tenant_id=tenant_id, index_name=index_name)

    async def get_tenant(self, tenant_id: str) -> Tenant:
        """Get a tenant by ID."""
        try:
            result = self._master_container.read_item(item=tenant_id, partition_key="tenant")
            return Tenant(**result)
        except CosmosResourceNotFoundError as e:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found") from e

    async def list_tenants(
        self, status: TenantStatus | None = None, limit: int = 100
    ) -> list[Tenant]:
        """List tenants with optional status filter."""
        query = "SELECT * FROM c WHERE c.type = 'tenant'"
        parameters: list[dict[str, Any]] = []

        if status:
            query += " AND c.status = @status"
            parameters.append({"name": "@status", "value": status.value})

        query += " ORDER BY c.created_at DESC"

        results = self._master_container.query_items(
            query=query,
            parameters=parameters,
            max_item_count=limit,
            enable_cross_partition_query=True,
        )

        return [Tenant(**item) for item in results]

    async def update_tenant(
        self, tenant_id: str, updates: dict[str, Any], updated_by: str
    ) -> Tenant:
        """Update tenant information."""
        tenant = await self.get_tenant(tenant_id)

        # Update fields
        for key, value in updates.items():
            if hasattr(tenant, key) and value is not None:
                setattr(tenant, key, value)

        tenant.updated_at = datetime.utcnow()

        # Save updated tenant
        self._master_container.replace_item(item=tenant_id, body=tenant.model_dump())

        # Log update
        await self._log_audit_action(
            action="tenant.updated",
            performed_by=updated_by,
            tenant_id=tenant_id,
            details={"updates": updates},
        )

        return tenant

    async def delete_tenant(self, tenant_id: str, deleted_by: str) -> None:
        """Delete a tenant and all associated resources."""
        logger.info("Deleting tenant", tenant_id=tenant_id, deleted_by=deleted_by)

        tenant = await self.get_tenant(tenant_id)

        # Log deletion before cleanup
        await self._log_audit_action(
            action="tenant.deleted",
            performed_by=deleted_by,
            tenant_id=tenant_id,
            details={"tenant_name": tenant.name},
        )

        # Cleanup tenant resources
        await self._cleanup_tenant_resources(tenant_id)

        # Delete tenant record
        self._master_container.delete_item(item=tenant_id, partition_key="tenant")

        logger.info("Tenant deleted successfully", tenant_id=tenant_id)

    async def _cleanup_tenant_resources(self, tenant_id: str) -> None:
        """Cleanup all resources associated with a tenant."""
        logger.info("Cleaning up tenant resources", tenant_id=tenant_id)

        try:
            # Delete tenant container
            container_name = f"{TENANT_CONTAINER_PREFIX}-{tenant_id}"
            await self._cosmos_service.delete_container(container_name)
            logger.info("Tenant container deleted", container_name=container_name)
        except Exception as e:
            logger.warning("Failed to delete tenant container", tenant_id=tenant_id, error=str(e))

        try:
            # Delete tenant search index
            index_name = f"{SEARCH_INDEX_PREFIX}-{tenant_id}"
            await self._search_service.delete_index(index_name)
            logger.info("Tenant search index deleted", index_name=index_name)
        except Exception as e:
            logger.warning(
                "Failed to delete tenant search index", tenant_id=tenant_id, error=str(e)
            )

    async def assign_user_to_tenant(
        self,
        tenant_id: str,
        user_id: str,
        user_email: str,
        role: TenantUserRole,
        assigned_by: str,
    ) -> TenantUser:
        """Assign a user to a tenant with a specific role."""
        logger.info(
            "Assigning user to tenant",
            tenant_id=tenant_id,
            user_id=user_id,
            role=role.value,
            assigned_by=assigned_by,
        )

        # Verify tenant exists
        await self.get_tenant(tenant_id)

        # Check if user is already assigned
        existing = await self.get_tenant_user(tenant_id, user_id)
        if existing:
            logger.warning("User already assigned to tenant", tenant_id=tenant_id, user_id=user_id)
            return existing

        # Create tenant user relationship
        tenant_user_id = str(uuid.uuid4())
        tenant_user = TenantUser(
            id=tenant_user_id,
            tenant_id=tenant_id,
            user_id=user_id,
            user_email=user_email,
            role=role,
            assigned_by=assigned_by,
        )

        # Store in master container
        self._master_container.create_item(tenant_user.model_dump())

        # Log assignment
        await self._log_audit_action(
            action="tenant.user.assigned",
            performed_by=assigned_by,
            tenant_id=tenant_id,
            target_user_id=user_id,
            details={"user_email": user_email, "role": role.value},
        )

        logger.info("User assigned to tenant successfully", tenant_id=tenant_id, user_id=user_id)
        return tenant_user

    async def get_tenant_user(self, tenant_id: str, user_id: str) -> TenantUser | None:
        """Get tenant user relationship."""
        query = """
        SELECT * FROM c 
        WHERE c.type = 'tenant_user' 
        AND c.tenant_id = @tenant_id 
        AND c.user_id = @user_id 
        AND c.is_active = true
        """

        parameters = [
            {"name": "@tenant_id", "value": tenant_id},
            {"name": "@user_id", "value": user_id},
        ]

        results = self._master_container.query_items(
            query=query, parameters=parameters, enable_cross_partition_query=True
        )

        items = list(results)
        if items:
            return TenantUser(**items[0])
        return None

    async def get_user_tenants(self, user_id: str) -> list[TenantUser]:
        """Get all tenants a user is assigned to."""
        query = """
        SELECT * FROM c 
        WHERE c.type = 'tenant_user' 
        AND c.user_id = @user_id 
        AND c.is_active = true
        """

        parameters = [{"name": "@user_id", "value": user_id}]

        results = self._master_container.query_items(
            query=query, parameters=parameters, enable_cross_partition_query=True
        )

        return [TenantUser(**item) for item in results]

    async def list_tenant_users(self, tenant_id: str) -> list[TenantUser]:
        """List all users assigned to a tenant."""
        query = """
        SELECT * FROM c 
        WHERE c.type = 'tenant_user' 
        AND c.tenant_id = @tenant_id 
        AND c.is_active = true
        """

        parameters = [{"name": "@tenant_id", "value": tenant_id}]

        results = self._master_container.query_items(
            query=query, parameters=parameters, enable_cross_partition_query=True
        )

        return [TenantUser(**item) for item in results]

    async def remove_user_from_tenant(self, tenant_id: str, user_id: str, removed_by: str) -> None:
        """Remove a user from a tenant."""
        logger.info(
            "Removing user from tenant",
            tenant_id=tenant_id,
            user_id=user_id,
            removed_by=removed_by,
        )

        tenant_user = await self.get_tenant_user(tenant_id, user_id)
        if not tenant_user:
            raise TenantUserNotFoundError(f"User {user_id} not found in tenant {tenant_id}")

        # Deactivate the relationship instead of deleting
        tenant_user.is_active = False
        self._master_container.replace_item(item=tenant_user.id, body=tenant_user.model_dump())

        # Log removal
        await self._log_audit_action(
            action="tenant.user.removed",
            performed_by=removed_by,
            tenant_id=tenant_id,
            target_user_id=user_id,
            details={"user_email": tenant_user.user_email},
        )

        logger.info("User removed from tenant successfully", tenant_id=tenant_id, user_id=user_id)

    def get_tenant_container(self, tenant_id: str) -> ContainerProxy:
        """Get the Cosmos DB container for a specific tenant."""
        container_name = f"{TENANT_CONTAINER_PREFIX}-{tenant_id}"
        return self._cosmos_service.get_container(container_name)

    def get_tenant_search_index(self, tenant_id: str) -> str:
        """Get the search index name for a specific tenant."""
        return f"{SEARCH_INDEX_PREFIX}-{tenant_id}"

    async def _log_audit_action(
        self,
        action: str,
        performed_by: str,
        tenant_id: str | None = None,
        target_user_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Log an audit action."""
        audit_log = AuditLog(
            id=str(uuid.uuid4()),
            action=action,
            performed_by=performed_by,
            tenant_id=tenant_id,
            target_user_id=target_user_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        try:
            self._master_container.create_item(audit_log.model_dump())
            logger.info("Audit action logged", action=action, performed_by=performed_by)
        except Exception as e:
            logger.error("Failed to log audit action", action=action, error=str(e))

    async def get_audit_logs(
        self,
        tenant_id: str | None = None,
        performed_by: str | None = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Get audit logs with optional filters."""
        query = "SELECT * FROM c WHERE c.type = 'audit_log'"
        parameters: list[dict[str, Any]] = []

        if tenant_id:
            query += " AND c.tenant_id = @tenant_id"
            parameters.append({"name": "@tenant_id", "value": tenant_id})

        if performed_by:
            query += " AND c.performed_by = @performed_by"
            parameters.append({"name": "@performed_by", "value": performed_by})

        query += " ORDER BY c.timestamp DESC"

        results = self._master_container.query_items(
            query=query,
            parameters=parameters,
            max_item_count=limit,
            enable_cross_partition_query=True,
        )

        return [AuditLog(**item) for item in results]

    async def add_tenant_user(
        self,
        tenant_id: str,
        user_id: str,
        user_email: str,
        role: TenantUserRole,
        assigned_by: str,
    ) -> TenantUser:
        """Add a user to a tenant with a specific role."""
        return await self.assign_user_to_tenant(
            tenant_id=tenant_id,
            user_id=user_id,
            user_email=user_email,
            role=role,
            assigned_by=assigned_by,
        )

    async def update_tenant_user(
        self,
        tenant_id: str,
        user_id: str,
        updates: dict[str, Any],
    ) -> TenantUser | None:
        """Update a tenant user relationship."""
        tenant_user = await self.get_tenant_user(tenant_id, user_id)
        if not tenant_user:
            return None

        # Update fields
        for key, value in updates.items():
            if hasattr(tenant_user, key) and value is not None:
                setattr(tenant_user, key, value)

        # Save updated tenant user
        self._master_container.replace_item(
            item=tenant_user.id,
            body=tenant_user.model_dump(),
        )

        return tenant_user

    async def remove_tenant_user(self, tenant_id: str, user_id: str) -> bool:
        """Remove a user from a tenant."""
        tenant_user = await self.get_tenant_user(tenant_id, user_id)
        if not tenant_user:
            return False

        # Deactivate the relationship
        tenant_user.is_active = False
        self._master_container.replace_item(
            item=tenant_user.id,
            body=tenant_user.model_dump(),
        )

        return True

    async def get_tenant_stats(self) -> dict[str, Any]:
        """Get system-wide tenant statistics."""
        # Count total tenants
        tenant_query = "SELECT VALUE COUNT(1) FROM c WHERE c.type = 'tenant'"
        tenant_results = list(
            self._master_container.query_items(
                query=tenant_query,
                enable_cross_partition_query=True,
            )
        )
        tenant_count = tenant_results[0] if tenant_results else 0

        # Count active tenants
        active_query = (
            "SELECT VALUE COUNT(1) FROM c WHERE c.type = 'tenant' AND c.status = 'active'"
        )
        active_results = list(
            self._master_container.query_items(
                query=active_query,
                enable_cross_partition_query=True,
            )
        )
        active_tenants = active_results[0] if active_results else 0

        # Count total users
        user_query = (
            "SELECT VALUE COUNT(1) FROM c WHERE c.type = 'tenant_user' AND c.is_active = true"
        )
        user_results = list(
            self._master_container.query_items(
                query=user_query,
                enable_cross_partition_query=True,
            )
        )
        total_users = user_results[0] if user_results else 0

        # Approximate document count (placeholder)
        total_documents = 0

        return {
            "tenant_count": tenant_count,
            "active_tenants": active_tenants,
            "total_users": total_users,
            "total_documents": total_documents,
        }

    async def get_tenant_health(self, tenant_id: str) -> dict[str, Any] | None:
        """Get health status for a specific tenant."""
        try:
            tenant = await self.get_tenant(tenant_id)
            if not tenant:
                return None

            # Check container status
            container_status = "healthy"
            try:
                container = self.get_tenant_container(tenant_id)
                # Test container connectivity
                test_query = "SELECT VALUE COUNT(1) FROM c"
                list(container.query_items(query=test_query, max_item_count=1))
            except Exception:
                container_status = "unhealthy"

            # Check search index status
            search_index_status = "healthy"
            try:
                self.get_tenant_search_index(tenant_id)
                # Basic check - would need actual search service validation
            except Exception:
                search_index_status = "unhealthy"

            # Get user count
            user_count_query = (
                "SELECT VALUE COUNT(1) FROM c "
                "WHERE c.type = 'tenant_user' AND c.tenant_id = @tenant_id "
                "AND c.is_active = true"
            )
            user_results = list(
                self._master_container.query_items(
                    query=user_count_query,
                    parameters=[{"name": "@tenant_id", "value": tenant_id}],
                    enable_cross_partition_query=True,
                )
            )
            user_count = user_results[0] if user_results else 0

            # Document count (placeholder)
            document_count = 0

            # Quota usage (placeholder)
            quota_usage = {
                "storage": 0.0,
                "users": user_count / 100.0 if user_count else 0.0,
            }

            # Determine overall status
            overall_status = (
                "healthy"
                if container_status == "healthy" and search_index_status == "healthy"
                else "unhealthy"
            )

            return {
                "tenant_id": tenant_id,
                "status": overall_status,
                "container_status": container_status,
                "search_index_status": search_index_status,
                "user_count": user_count,
                "document_count": document_count,
                "quota_usage": quota_usage,
            }

        except TenantNotFoundError:
            return None


# Global service instance
_multi_tenant_service: MultiTenantService | None = None


def get_multi_tenant_service() -> MultiTenantService:
    """Get the global multi-tenant service instance."""
    global _multi_tenant_service
    if _multi_tenant_service is None:
        _multi_tenant_service = MultiTenantService()
    return _multi_tenant_service
