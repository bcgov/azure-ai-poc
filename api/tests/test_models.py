"""Tests for tenant models."""

from datetime import datetime

import pytest

from app.models.tenant_models import (
    AssignUserToTenantRequest,
    AuditLog,
    CreateTenantRequest,
    Tenant,
    TenantMetadata,
    TenantQuotas,
    TenantStatus,
    TenantUser,
    TenantUserRole,
    UpdateTenantRequest,
)


class TestTenantModels:
    """Test cases for tenant models."""

    def test_tenant_creation(self):
        """Test tenant model creation with defaults."""
        tenant = Tenant(
            id="test-tenant",
            name="Test Tenant",
            display_name="Test Tenant",
            created_by="admin@example.com",
        )

        assert tenant.id == "test-tenant"
        assert tenant.name == "Test Tenant"
        assert tenant.created_by == "admin@example.com"
        assert tenant.status == TenantStatus.ACTIVE
        assert tenant.type == "tenant"
        assert tenant.partitionKey == "tenant"
        assert isinstance(tenant.created_at, datetime)
        assert isinstance(tenant.quotas, TenantQuotas)
        assert isinstance(tenant.metadata, TenantMetadata)

    def test_tenant_with_custom_quotas(self):
        """Test tenant with custom quotas."""
        custom_quotas = TenantQuotas(
            max_documents=5000,
            max_storage_mb=10000,
            max_users=200,
        )

        tenant = Tenant(
            id="test-tenant",
            name="Test Tenant",
            display_name="Test Tenant",
            created_by="admin@example.com",
            quotas=custom_quotas,
        )

        assert tenant.quotas.max_documents == 5000
        assert tenant.quotas.max_storage_mb == 10000
        assert tenant.quotas.max_users == 200

    def test_tenant_with_metadata(self):
        """Test tenant with custom metadata."""
        metadata = TenantMetadata(
            organization="Test Org",
            contact_email="contact@test.org",
            department="IT",
            custom_fields={"project_code": "TEST-001"},
            tags=["test", "development"],
        )

        tenant = Tenant(
            id="test-tenant",
            name="Test Tenant",
            display_name="Test Tenant",
            created_by="admin@example.com",
            metadata=metadata,
        )

        assert tenant.metadata.organization == "Test Org"
        assert tenant.metadata.contact_email == "contact@test.org"
        assert tenant.metadata.custom_fields["project_code"] == "TEST-001"
        assert "test" in tenant.metadata.tags

    def test_tenant_user_creation(self):
        """Test tenant user model creation."""
        tenant_user = TenantUser(
            id="tu-123",
            tenant_id="test-tenant",
            user_id="user-123",
            user_email="user@example.com",
            role=TenantUserRole.TENANT_USER_WRITE,
            assigned_by="admin@example.com",
        )

        assert tenant_user.id == "tu-123"
        assert tenant_user.tenant_id == "test-tenant"
        assert tenant_user.user_id == "user-123"
        assert tenant_user.role == TenantUserRole.TENANT_USER_WRITE
        assert tenant_user.is_active is True
        assert tenant_user.type == "tenant_user"
        assert tenant_user.partitionKey == "tenant"

    def test_audit_log_creation(self):
        """Test audit log model creation."""
        audit_log = AuditLog(
            id="audit-123",
            action="tenant.created",
            performed_by="admin@example.com",
            tenant_id="test-tenant",
            details={"tenant_name": "Test Tenant"},
        )

        assert audit_log.id == "audit-123"
        assert audit_log.action == "tenant.created"
        assert audit_log.performed_by == "admin@example.com"
        assert audit_log.tenant_id == "test-tenant"
        assert audit_log.details["tenant_name"] == "Test Tenant"
        assert audit_log.type == "audit_log"
        assert audit_log.partitionKey == "audit"

    def test_create_tenant_request(self):
        """Test create tenant request DTO."""
        request = CreateTenantRequest(
            name="New Tenant",
            display_name="New Tenant",
            description="A new tenant for testing",
            quotas=TenantQuotas(max_documents=2000),
            metadata=TenantMetadata(organization="Test Org"),
        )

        assert request.name == "New Tenant"
        assert request.description == "A new tenant for testing"
        assert request.quotas.max_documents == 2000
        assert request.metadata.organization == "Test Org"

    def test_update_tenant_request(self):
        """Test update tenant request DTO."""
        request = UpdateTenantRequest(
            name="Updated Tenant",
            status=TenantStatus.INACTIVE,
        )

        assert request.name == "Updated Tenant"
        assert request.status == TenantStatus.INACTIVE
        assert request.description is None

    def test_assign_user_request(self):
        """Test assign user to tenant request DTO."""
        request = AssignUserToTenantRequest(
            user_email="user@example.com",
            role=TenantUserRole.TENANT_ADMIN,
        )

        assert request.user_email == "user@example.com"
        assert request.role == TenantUserRole.TENANT_ADMIN

    def test_tenant_status_enum(self):
        """Test tenant status enumeration."""
        assert TenantStatus.ACTIVE == "active"
        assert TenantStatus.INACTIVE == "inactive"
        assert TenantStatus.SUSPENDED == "suspended"
        assert TenantStatus.PENDING == "pending"

    def test_tenant_user_role_enum(self):
        """Test tenant user role enumeration."""
        assert TenantUserRole.SUPER_ADMIN == "super_admin"
        assert TenantUserRole.TENANT_ADMIN == "tenant_admin"
        assert TenantUserRole.TENANT_USER_READ == "tenant_user_read"
        assert TenantUserRole.TENANT_USER_WRITE == "tenant_user_write"

    def test_tenant_quotas_defaults(self):
        """Test tenant quotas default values."""
        quotas = TenantQuotas()

        assert quotas.max_documents == 1000
        assert quotas.max_storage_mb == 5000
        assert quotas.max_users == 50
        assert quotas.max_api_calls_per_hour == 10000
        assert quotas.max_chat_sessions == 100

    def test_tenant_metadata_defaults(self):
        """Test tenant metadata default values."""
        metadata = TenantMetadata()

        assert metadata.organization is None
        assert metadata.contact_email is None
        assert metadata.environment == "production"
        assert metadata.custom_fields == {}
        assert metadata.tags == []

    def test_tenant_validation(self):
        """Test tenant model validation."""
        # Test name validation
        with pytest.raises(ValueError):
            Tenant(
                id="test-tenant",
                name="",  # Empty name should fail
                created_by="admin@example.com",
            )

        # Test name length validation
        with pytest.raises(ValueError):
            Tenant(
                id="test-tenant",
                name="x" * 101,  # Name too long should fail
                display_name="Test Display",
                created_by="admin@example.com",
            )
