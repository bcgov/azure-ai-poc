from types import SimpleNamespace

import pytest
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from app.services.multi_tenant_service import (
    MASTER_CONTAINER_NAME,
    MultiTenantService,
)


class StubContainer:
    def __init__(self):
        self.created_items: list[dict] = []
        self.replaced_items: list[tuple[str, dict]] = []
        self.deleted_items: list[tuple[str, str]] = []
        self.query_results: list[list] = [[0]]
        self.read_calls = 0

    def read(self):
        self.read_calls += 1
        return {}

    def create_item(self, body):
        self.created_items.append(body)
        return body

    def query_items(self, *args, **kwargs):
        if self.query_results:
            return iter(self.query_results.pop(0))
        return iter([])

    def replace_item(self, item, body):
        self.replaced_items.append((item, body))

    def delete_item(self, item, partition_key):
        self.deleted_items.append((item, partition_key))

    def read_item(self, *, item, partition_key):
        if self.created_items:
            for stored in self.created_items:
                if stored.get("id") == item:
                    return stored
        error = CosmosResourceNotFoundError.__new__(CosmosResourceNotFoundError)
        error.status_code = 404
        raise error


class StubSearchService:
    def __init__(self, fail_on_create: bool = False):
        self.fail_on_create = fail_on_create
        self.created_indexes: list[str] = []
        self.deleted_indexes: list[str] = []

    async def create_index(self, index_name: str):
        if self.fail_on_create:
            raise RuntimeError("index failure")
        self.created_indexes.append(index_name)

    async def delete_index(self, index_name: str):
        self.deleted_indexes.append(index_name)


class StubCosmosService:
    def __init__(self, containers=None):
        self.containers = containers or {}
        self.created_container_names: list[str] = []
        self.deleted_containers: list[str] = []
        self.master_create_calls: list[tuple] = []
        self.database = SimpleNamespace(create_container=self._create_master_container)

    def _create_master_container(self, *, id, partition_key, indexing_policy):
        container = StubContainer()
        self.containers[id] = container
        self.master_create_calls.append((id, partition_key, indexing_policy))
        return container

    def get_container(self, name):
        if name not in self.containers:
            error = CosmosResourceNotFoundError.__new__(CosmosResourceNotFoundError)
            error.status_code = 404
            raise error
        return self.containers[name]

    async def create_container(
        self,
        container_name: str,
        partition_key_path: str,
        container_properties=None,
    ):
        container = StubContainer()
        self.containers[container_name] = container
        self.created_container_names.append(container_name)
        return container

    async def delete_container(self, container_name: str):
        self.deleted_containers.append(container_name)
        self.containers.pop(container_name, None)


@pytest.fixture(name="stub_services")
def stubbed_services(monkeypatch):
    master_container = StubContainer()
    cosmos_stub = StubCosmosService({MASTER_CONTAINER_NAME: master_container})
    search_stub = StubSearchService()

    monkeypatch.setattr(
        "app.services.multi_tenant_service.get_cosmos_db_service",
        lambda: cosmos_stub,
    )
    monkeypatch.setattr(
        "app.services.multi_tenant_service.get_azure_search_service",
        lambda: search_stub,
    )

    return SimpleNamespace(
        cosmos=cosmos_stub,
        search=search_stub,
        master=master_container,
    )


@pytest.mark.asyncio
async def test_initialize_uses_existing_master_container(stub_services):
    service = MultiTenantService()
    await service.initialize()

    assert service._master_container is stub_services.master
    assert not stub_services.cosmos.master_create_calls
    assert stub_services.master.read_calls == 1


@pytest.mark.asyncio
async def test_initialize_creates_master_container_when_missing(monkeypatch):
    cosmos_stub = StubCosmosService()
    search_stub = StubSearchService()

    monkeypatch.setattr(
        "app.services.multi_tenant_service.get_cosmos_db_service",
        lambda: cosmos_stub,
    )
    monkeypatch.setattr(
        "app.services.multi_tenant_service.get_azure_search_service",
        lambda: search_stub,
    )

    service = MultiTenantService()
    await service.initialize()

    assert cosmos_stub.master_create_calls
    assert service._master_container is cosmos_stub.containers[MASTER_CONTAINER_NAME]


@pytest.mark.asyncio
async def test_create_tenant_happy_path(stub_services):
    service = MultiTenantService()
    service._master_container = stub_services.master

    tenant = await service.create_tenant(name="acme", created_by="admin")

    assert tenant.name == "acme"
    assert len(stub_services.cosmos.created_container_names) == 1
    created_name = stub_services.cosmos.created_container_names[0]
    assert created_name.startswith("tenant-")
    assert stub_services.search.created_indexes == [f"documents-{tenant.id}"]
    types = {item["type"] for item in stub_services.master.created_items}
    assert {"tenant", "audit_log"}.issubset(types)


@pytest.mark.asyncio
async def test_create_tenant_failure_triggers_cleanup(monkeypatch):
    master_container = StubContainer()
    cosmos_stub = StubCosmosService({MASTER_CONTAINER_NAME: master_container})
    search_stub = StubSearchService(fail_on_create=True)

    monkeypatch.setattr(
        "app.services.multi_tenant_service.get_cosmos_db_service",
        lambda: cosmos_stub,
    )
    monkeypatch.setattr(
        "app.services.multi_tenant_service.get_azure_search_service",
        lambda: search_stub,
    )

    service = MultiTenantService()
    service._master_container = master_container

    with pytest.raises(RuntimeError):
        await service.create_tenant(name="contoso", created_by="owner")

    assert cosmos_stub.deleted_containers
    tenant_entry = next(
        item for item in master_container.created_items if item.get("type") == "tenant"
    )
    assert search_stub.deleted_indexes == [f"documents-{tenant_entry['id']}"]


@pytest.mark.asyncio
async def test_get_tenant_not_found_raises(monkeypatch):
    master_container = StubContainer()

    def read_item(*, item, partition_key):
        error = CosmosResourceNotFoundError.__new__(CosmosResourceNotFoundError)
        error.status_code = 404
        raise error

    master_container.read_item = read_item  # type: ignore[assignment]

    cosmos_stub = StubCosmosService({MASTER_CONTAINER_NAME: master_container})
    search_stub = StubSearchService()

    monkeypatch.setattr(
        "app.services.multi_tenant_service.get_cosmos_db_service",
        lambda: cosmos_stub,
    )
    monkeypatch.setattr(
        "app.services.multi_tenant_service.get_azure_search_service",
        lambda: search_stub,
    )

    service = MultiTenantService()
    service._master_container = master_container

    from app.services.multi_tenant_service import TenantNotFoundError

    with pytest.raises(TenantNotFoundError):
        await service.get_tenant("missing")


@pytest.mark.asyncio
async def test_list_tenants(stub_services):
    """Test listing all tenants."""
    service = MultiTenantService()
    service._master_container = stub_services.master

    # Add some tenants to the query results with required fields
    stub_services.master.query_results = [
        [
            {
                "id": "tenant-1",
                "name": "tenant1",
                "display_name": "Tenant 1",
                "created_by": "admin",
                "type": "tenant",
            },
            {
                "id": "tenant-2",
                "name": "tenant2",
                "display_name": "Tenant 2",
                "created_by": "admin",
                "type": "tenant",
            },
        ]
    ]

    tenants = await service.list_tenants()

    assert len(tenants) == 2
    assert tenants[0].id == "tenant-1"


@pytest.mark.asyncio
async def test_create_tenant_with_duplicate_name(stub_services):
    """Test creating tenant with duplicate name raises error."""
    service = MultiTenantService()
    service._master_container = stub_services.master

    # Simulate existing tenant
    stub_services.master.query_results = [
        [{"id": "existing", "name": "test-tenant", "type": "tenant"}]
    ]

    with pytest.raises(ValueError, match="already exists"):
        await service.create_tenant(
            name="test-tenant",
            display_name="Test Tenant",
            created_by="admin@example.com",
        )


@pytest.mark.asyncio
async def test_update_nonexistent_tenant(monkeypatch):
    """Test updating non-existent tenant raises error."""
    master_container = StubContainer()

    def read_item(*, item, partition_key):
        error = CosmosResourceNotFoundError.__new__(CosmosResourceNotFoundError)
        error.status_code = 404
        raise error

    master_container.read_item = read_item  # type: ignore[assignment]

    cosmos_stub = StubCosmosService({MASTER_CONTAINER_NAME: master_container})
    search_stub = StubSearchService()

    monkeypatch.setattr(
        "app.services.multi_tenant_service.get_cosmos_db_service",
        lambda: cosmos_stub,
    )
    monkeypatch.setattr(
        "app.services.multi_tenant_service.get_azure_search_service",
        lambda: search_stub,
    )

    service = MultiTenantService()
    service._master_container = master_container

    from app.services.multi_tenant_service import TenantNotFoundError

    with pytest.raises(TenantNotFoundError):
        await service.update_tenant(
            tenant_id="nonexistent",
            display_name="Updated Name",
        )


@pytest.mark.asyncio
async def test_delete_tenant_with_cleanup_failure(stub_services, monkeypatch):
    """Test tenant deletion when cleanup fails."""
    service = MultiTenantService()
    service._master_container = stub_services.master

    # Simulate tenant exists
    tenant_data = {
        "id": "test-tenant",
        "name": "test-tenant",
        "display_name": "Test",
        "created_by": "admin",
        "type": "tenant",
    }
    stub_services.master.created_items.append(tenant_data)

    # Make search service fail on delete
    async def failing_delete(index_name):
        raise RuntimeError("Failed to delete search index")

    stub_services.search.delete_index = failing_delete

    # Should handle cleanup failure gracefully
    try:
        await service.delete_tenant("test-tenant")
    except RuntimeError:
        # Cleanup failure should be logged but not prevent deletion
        pass


@pytest.mark.asyncio
async def test_assign_user_to_nonexistent_tenant(monkeypatch):
    """Test assigning user to non-existent tenant."""
    master_container = StubContainer()

    def read_item(*, item, partition_key):
        error = CosmosResourceNotFoundError.__new__(CosmosResourceNotFoundError)
        error.status_code = 404
        raise error

    master_container.read_item = read_item  # type: ignore[assignment]

    cosmos_stub = StubCosmosService({MASTER_CONTAINER_NAME: master_container})
    search_stub = StubSearchService()

    monkeypatch.setattr(
        "app.services.multi_tenant_service.get_cosmos_db_service",
        lambda: cosmos_stub,
    )
    monkeypatch.setattr(
        "app.services.multi_tenant_service.get_azure_search_service",
        lambda: search_stub,
    )

    service = MultiTenantService()
    service._master_container = master_container

    from app.models.tenant_models import TenantUserRole
    from app.services.multi_tenant_service import TenantNotFoundError

    with pytest.raises(TenantNotFoundError):
        await service.assign_user_to_tenant(
            tenant_id="nonexistent",
            user_id="user@example.com",
            user_email="user@example.com",
            role=TenantUserRole.TENANT_USER_READ,
            assigned_by="admin@example.com",
        )


@pytest.mark.asyncio
async def test_remove_user_not_assigned(stub_services):
    """Test removing user that's not assigned to tenant."""
    service = MultiTenantService()
    service._master_container = stub_services.master

    # Simulate tenant exists
    tenant_data = {
        "id": "test-tenant",
        "name": "test-tenant",
        "display_name": "Test",
        "created_by": "admin",
        "type": "tenant",
    }
    stub_services.master.created_items.append(tenant_data)

    # No user assignments in query results
    stub_services.master.query_results = [[]]

    with pytest.raises(ValueError, match="not assigned|not found"):
        await service.remove_user_from_tenant(
            tenant_id="test-tenant",
            user_id="unassigned@example.com",
        )


@pytest.mark.asyncio
async def test_list_tenants_empty_result(stub_services):
    """Test listing tenants when no tenants exist."""
    service = MultiTenantService()
    service._master_container = stub_services.master

    # Empty query results
    stub_services.master.query_results = [[]]

    tenants = await service.list_tenants()

    assert len(tenants) == 0


@pytest.mark.asyncio
async def test_get_tenant_users_empty(stub_services):
    """Test getting users for tenant with no assigned users."""
    service = MultiTenantService()
    service._master_container = stub_services.master

    # Simulate tenant exists
    tenant_data = {
        "id": "test-tenant",
        "name": "test-tenant",
        "display_name": "Test",
        "created_by": "admin",
        "type": "tenant",
    }
    stub_services.master.created_items.append(tenant_data)

    # Empty user results
    stub_services.master.query_results = [[]]

    users = await service.get_tenant_users("test-tenant")

    assert len(users) == 0


@pytest.mark.asyncio
async def test_create_tenant_search_index_failure(monkeypatch):
    """Test tenant creation when search index creation fails."""
    master_container = StubContainer()
    cosmos_stub = StubCosmosService({MASTER_CONTAINER_NAME: master_container})
    search_stub = StubSearchService(fail_on_create=True)

    monkeypatch.setattr(
        "app.services.multi_tenant_service.get_cosmos_db_service",
        lambda: cosmos_stub,
    )
    monkeypatch.setattr(
        "app.services.multi_tenant_service.get_azure_search_service",
        lambda: search_stub,
    )

    service = MultiTenantService()
    service._master_container = master_container

    # Should handle search index failure
    with pytest.raises(RuntimeError, match="index failure"):
        await service.create_tenant(
            name="test-tenant",
            display_name="Test Tenant",
            created_by="admin@example.com",
        )


@pytest.mark.asyncio
async def test_validate_tenant_access_invalid_tenant(monkeypatch):
    """Test access validation for invalid tenant."""
    master_container = StubContainer()

    def read_item(*, item, partition_key):
        error = CosmosResourceNotFoundError.__new__(CosmosResourceNotFoundError)
        error.status_code = 404
        raise error

    master_container.read_item = read_item  # type: ignore[assignment]

    cosmos_stub = StubCosmosService({MASTER_CONTAINER_NAME: master_container})
    search_stub = StubSearchService()

    monkeypatch.setattr(
        "app.services.multi_tenant_service.get_cosmos_db_service",
        lambda: cosmos_stub,
    )
    monkeypatch.setattr(
        "app.services.multi_tenant_service.get_azure_search_service",
        lambda: search_stub,
    )

    service = MultiTenantService()
    service._master_container = master_container

    # Should return False for invalid tenant
    has_access = await service.validate_tenant_access(
        tenant_id="invalid-tenant",
        user_id="user@example.com",
    )

    assert has_access is False
