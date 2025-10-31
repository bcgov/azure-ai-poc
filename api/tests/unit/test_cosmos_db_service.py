from types import SimpleNamespace

import pytest
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError

from app.services.cosmos_db_service import CosmosDbService


class _NullLogger:
    def debug(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


class _DummyContainer:
    def __init__(self, error_to_raise=None):
        self.error_to_raise = error_to_raise
        self.created_items = []

    def create_item(self, body):
        if self.error_to_raise is not None:
            raise self.error_to_raise
        self.created_items.append(body)
        return body


class _DummyDatabase:
    def __init__(self):
        self.create_calls: list[tuple[str, object, object | None]] = []

    def create_container_if_not_exists(self, *, id, partition_key, indexing_policy=None):
        self.create_calls.append((id, partition_key, indexing_policy))
        return SimpleNamespace(id=id)

    def delete_container(self, container_name):
        if container_name == "missing":
            error = CosmosResourceNotFoundError.__new__(CosmosResourceNotFoundError)
            error.status_code = 404
            raise error


@pytest.fixture(name="service")
def cosmos_service(monkeypatch) -> CosmosDbService:
    monkeypatch.setattr(CosmosDbService, "_initialize_client", lambda self: None)
    svc = CosmosDbService()
    svc.logger = _NullLogger()
    return svc


@pytest.mark.asyncio
async def test_create_item_with_large_payload_raises_value_error(service: CosmosDbService):
    error = CosmosHttpResponseError.__new__(CosmosHttpResponseError)
    error.status_code = 413
    error.message = "Request Entity Too Large"
    service.container = _DummyContainer(error_to_raise=error)

    payload = {"id": "doc", "content": "x" * 1024 * 1024}

    with pytest.raises(ValueError) as exc:
        await service.create_item(payload, partition_key="pk")

    assert "Document too large" in str(exc.value)


@pytest.mark.asyncio
async def test_create_container_invokes_database_factory(service: CosmosDbService):
    database = _DummyDatabase()
    service.database = database

    container = await service.create_container(
        container_name="tenant-test",
        partition_key_path="/partitionKey",
        container_properties={"indexingPolicy": {"includedPaths": []}},
    )

    assert container.id == "tenant-test"
    assert database.create_calls
    _, partition_key, indexing_policy = database.create_calls[0]
    assert indexing_policy == {"includedPaths": []}
    assert getattr(partition_key, "path", None) == "/partitionKey"


@pytest.mark.asyncio
async def test_delete_container_ignores_missing(service: CosmosDbService):
    database = _DummyDatabase()
    service.database = database

    # Should not raise even if container missing
    await service.delete_container("missing")

    # Existing container delete should also succeed
    database.create_container_if_not_exists(
        id="existing",
        partition_key=SimpleNamespace(path="/pk"),
        indexing_policy=None,
    )
    await service.delete_container("existing")
