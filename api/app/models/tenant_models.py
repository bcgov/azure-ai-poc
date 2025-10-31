"""Multi-tenant data models for the application."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TenantStatus(str, Enum):
    """Tenant status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class TenantUserRole(str, Enum):
    """Tenant user role enumeration."""

    SUPER_ADMIN = "super_admin"  # Global super admin
    TENANT_ADMIN = "tenant_admin"  # Tenant administrator
    TENANT_USER_READ = "tenant_user_read"  # Read-only tenant user
    TENANT_USER_WRITE = "tenant_user_write"  # Read-write tenant user


class TenantQuotas(BaseModel):
    """Tenant quotas configuration."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "max_documents": 1000,
                "max_storage_mb": 5000,
                "max_users": 50,
                "max_api_calls_per_hour": 10000,
                "max_chat_sessions": 100,
            }
        }
    )

    max_documents: int | None = Field(default=1000, description="Maximum documents allowed")
    max_storage_mb: int | None = Field(default=5000, description="Maximum storage in MB")
    max_users: int | None = Field(default=50, description="Maximum users allowed")
    max_api_calls_per_hour: int | None = Field(
        default=10000, description="Maximum API calls per hour"
    )
    max_chat_sessions: int | None = Field(
        default=100, description="Maximum concurrent chat sessions"
    )


class TenantMetadata(BaseModel):
    """Custom tenant metadata."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "organization": "BC Government",
                "contact_email": "admin@example.gov.bc.ca",
                "department": "Natural Resources",
                "region": "British Columbia",
                "environment": "production",
                "custom_fields": {"project_code": "NRS-AI-2025", "cost_center": "12345"},
                "tags": ["government", "ai", "documents"],
            }
        }
    )

    organization: str | None = Field(default=None, description="Organization name")
    contact_email: str | None = Field(default=None, description="Primary contact email")
    department: str | None = Field(default=None, description="Department or division")
    region: str | None = Field(default=None, description="Geographic region")
    environment: str | None = Field(default="production", description="Environment type")
    custom_fields: dict[str, Any] | None = Field(
        default_factory=dict, description="Custom key-value metadata"
    )
    tags: list[str] | None = Field(default_factory=list, description="Tenant tags")


class Tenant(BaseModel):
    """Tenant model for multi-tenancy."""

    id: str = Field(..., description="Unique tenant identifier")
    name: str = Field(..., description="Tenant slug/identifier", min_length=1, max_length=100)
    display_name: str = Field(..., description="Tenant display name", min_length=1, max_length=100)
    description: str | None = Field(default=None, description="Tenant description")
    status: TenantStatus = Field(default=TenantStatus.ACTIVE, description="Tenant status")
    created_by: str = Field(..., description="User ID who created the tenant")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last update timestamp"
    )
    quotas: TenantQuotas = Field(default_factory=TenantQuotas, description="Tenant quotas")
    metadata: TenantMetadata = Field(default_factory=TenantMetadata, description="Tenant metadata")

    # Internal fields for Cosmos DB
    type: str = Field(default="tenant", description="Document type for Cosmos DB")
    partitionKey: str = Field(default="tenant", description="Partition key for Cosmos DB")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "tenant-nrs-2025",
                "name": "Natural Resources Sector",
                "description": "AI PoC for Natural Resources document processing",
                "status": "active",
                "created_by": "admin@gov.bc.ca",
                "quotas": {
                    "max_documents": 2000,
                    "max_storage_mb": 10000,
                    "max_users": 100,
                },
                "metadata": {
                    "organization": "BC Government",
                    "department": "Natural Resources",
                    "contact_email": "nrs-admin@gov.bc.ca",
                },
            }
        }
    )


class TenantUser(BaseModel):
    """Tenant user relationship model."""

    id: str = Field(..., description="Unique relationship identifier")
    tenant_id: str = Field(..., description="Tenant identifier")
    user_id: str = Field(..., description="User identifier (from Keycloak sub)")
    user_email: str = Field(..., description="User email")
    role: TenantUserRole = Field(..., description="User role within the tenant")
    assigned_by: str = Field(..., description="User ID who assigned this role")
    assigned_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Assignment timestamp"
    )
    last_accessed: datetime | None = Field(default=None, description="Last access timestamp")
    is_active: bool = Field(default=True, description="Whether the user assignment is active")

    # Internal fields for Cosmos DB
    type: str = Field(default="tenant_user", description="Document type for Cosmos DB")
    partitionKey: str = Field(default="tenant", description="Partition key for Cosmos DB")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "tu-123456",
                "tenant_id": "tenant-nrs-2025",
                "user_id": "auth0|123456789",
                "user_email": "user@gov.bc.ca",
                "role": "tenant_user_write",
                "assigned_by": "admin@gov.bc.ca",
            }
        }
    )


class AuditLog(BaseModel):
    """Audit log model for tracking tenant operations."""

    id: str = Field(..., description="Unique audit log identifier")
    action: str = Field(..., description="Action performed")
    performed_by: str = Field(..., description="User ID who performed the action")
    performed_by_email: str | None = Field(default=None, description="User email")
    tenant_id: str | None = Field(default=None, description="Affected tenant ID")
    target_user_id: str | None = Field(
        default=None, description="Target user ID (for user operations)"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Action timestamp"
    )
    details: dict[str, Any] | None = Field(
        default_factory=dict, description="Additional action details"
    )
    ip_address: str | None = Field(default=None, description="Client IP address")
    user_agent: str | None = Field(default=None, description="Client user agent")

    # Internal fields for Cosmos DB
    type: str = Field(default="audit_log", description="Document type for Cosmos DB")
    partitionKey: str = Field(default="audit", description="Partition key for Cosmos DB")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "audit-123456",
                "action": "tenant.created",
                "performed_by": "admin@gov.bc.ca",
                "tenant_id": "tenant-nrs-2025",
                "details": {"tenant_name": "Natural Resources Sector"},
                "ip_address": "192.168.1.100",
            }
        }
    )


# DTOs for API requests/responses
class CreateTenantRequest(BaseModel):
    """Request model for creating a tenant."""

    name: str = Field(..., description="Tenant name", min_length=1, max_length=100)
    display_name: str = Field(..., description="Tenant display name", min_length=1, max_length=100)
    description: str | None = Field(default=None, description="Tenant description")
    quotas: TenantQuotas | None = Field(default=None, description="Custom tenant quotas")
    metadata: TenantMetadata | None = Field(default=None, description="Tenant metadata")


class UpdateTenantRequest(BaseModel):
    """Request model for updating a tenant."""

    name: str | None = Field(
        default=None, description="Tenant display name", min_length=1, max_length=100
    )
    description: str | None = Field(default=None, description="Tenant description")
    status: TenantStatus | None = Field(default=None, description="Tenant status")
    quotas: TenantQuotas | None = Field(default=None, description="Tenant quotas")
    metadata: TenantMetadata | None = Field(default=None, description="Tenant metadata")


class AssignUserToTenantRequest(BaseModel):
    """Request model for assigning a user to a tenant."""

    user_email: str = Field(..., description="User email to assign")
    role: TenantUserRole = Field(..., description="Role to assign to the user")


class CreateTenantUserRequest(BaseModel):
    """Request model for creating/adding a tenant user."""

    user_id: str = Field(..., description="User ID to add to tenant")
    user_email: str = Field(..., description="User email")
    role: TenantUserRole = Field(..., description="Role to assign to the user")


class UpdateTenantUserRequest(BaseModel):
    """Request model for updating a tenant user."""

    role: TenantUserRole | None = Field(default=None, description="New role for the user")


class TenantUserResponse(BaseModel):
    """Response model for tenant user information."""

    id: str
    tenant_id: str
    user_id: str
    user_email: str
    role: TenantUserRole
    assigned_by: str
    assigned_at: datetime
    last_accessed: datetime | None
    is_active: bool

    @classmethod
    def from_tenant_user(cls, tenant_user: "TenantUser") -> "TenantUserResponse":
        """Create a TenantUserResponse from a TenantUser object."""
        return cls(
            id=tenant_user.id,
            tenant_id=tenant_user.tenant_id,
            user_id=tenant_user.user_id,
            user_email=tenant_user.user_email,
            role=tenant_user.role,
            assigned_by=tenant_user.assigned_by,
            assigned_at=tenant_user.assigned_at,
            last_accessed=tenant_user.last_accessed,
            is_active=tenant_user.is_active,
        )


class TenantResponse(BaseModel):
    """Response model for tenant information."""

    id: str
    name: str
    display_name: str
    description: str | None
    status: TenantStatus
    created_by: str
    created_at: datetime
    updated_at: datetime
    quotas: TenantQuotas
    metadata: TenantMetadata
    user_count: int | None = Field(default=None, description="Number of users in tenant")
    document_count: int | None = Field(default=None, description="Number of documents in tenant")

    @classmethod
    def from_tenant(
        cls, tenant: "Tenant", user_count: int | None = None, document_count: int | None = None
    ) -> "TenantResponse":
        """Create a TenantResponse from a Tenant object."""
        return cls(
            id=tenant.id,
            name=tenant.name,
            display_name=tenant.display_name,
            description=tenant.description,
            status=tenant.status,
            created_by=tenant.created_by,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
            quotas=tenant.quotas,
            metadata=tenant.metadata,
            user_count=user_count,
            document_count=document_count,
        )
