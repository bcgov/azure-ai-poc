"""Test configuration and fixtures for the API tests."""

import os
import sys
from collections.abc import AsyncGenerator
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI

# Ensure the app directory is on the Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

# Skip expensive startup initialization when running tests
os.environ.setdefault("SKIP_STARTUP_INIT", "true")

from app.auth.dependencies import (
    get_current_user,
    get_tenant_context,
    require_super_admin,
    require_tenant_admin,
)
from app.auth.models import KeycloakUser
from app.main import create_app
from app.models.tenant_models import TenantUserRole
from app.services.cosmos_db_service import get_cosmos_db_service
from app.services.document_service import get_document_service
from app.services.langchain_service import get_langchain_ai_service
from app.services.langgraph_agent_service import get_langgraph_agent_service
from app.services.multi_tenant_service import get_multi_tenant_service
from app.services.tenant_context import TenantContext


class MockLangchainService:
    """Lightweight LangChain service stub for tests."""

    def __init__(self) -> None:
        self.initialize_client = AsyncMock()
        self.chat_completion = AsyncMock(return_value="Stubbed chat response")
        self.memory_service = SimpleNamespace(
            create_session=AsyncMock(),
            get_user_sessions=AsyncMock(return_value=[]),
            update_session_metadata=AsyncMock(),
            delete_session=AsyncMock(),
        )


class MockDocumentService:
    """Document service stub providing predictable responses."""

    async def process_document(self, uploaded_file, user_id):
        return SimpleNamespace(
            id="doc-stub",
            filename=uploaded_file.filename,
            user_id=user_id,
            chunk_ids=["chunk-1"],
            total_pages=1,
            uploaded_at="2024-01-01T00:00:00Z",
        )

    async def get_all_documents(self, user_id):
        return []

    async def get_document(self, document_id, user_id):
        return None

    async def delete_document(self, document_id, user_id):
        return True


class MockCosmosService:
    """Cosmos DB service stub for health checks."""

    async def health_check(self):
        return {
            "status": "up",
            "details": {"status": "connected", "responseTime": "0.00ms"},
        }

    async def cleanup(self):
        return None


class MockLanggraphAgentService:
    """LangGraph agent service stub returning canned responses."""

    async def process_message(self, *args, **kwargs):
        return "Stubbed agent response"

    async def initialize_client(self):
        return None


def _build_keycloak_user(context: TenantContext) -> KeycloakUser:
    roles = ["ai-poc-participant"]
    if context.is_super_admin():
        roles.append("azure-ai-poc-super-admin")
    return KeycloakUser(
        sub=context.user_id,
        preferred_username=context.user_id,
        client_roles=roles,
    )


@pytest.fixture(scope="session")
def test_app() -> FastAPI:
    """Create a FastAPI application instance for tests."""
    return create_app()


@pytest.fixture
def mock_multi_tenant_service() -> AsyncMock:
    """Create a mock multi-tenant service."""
    service = AsyncMock()
    service.initialize.return_value = None
    service.health_check.return_value = {"status": "up"}
    # Configure async methods to return actual coroutines
    service.get_tenant_stats.return_value = {
        "total_tenants": 0,
        "active_tenants": 0,
        "total_users": 0,
    }
    service.get_tenant_health.return_value = {
        "tenant_id": "test-tenant",
        "status": "healthy",
        "last_activity": "2024-01-01T00:00:00Z",
    }
    return service


@pytest.fixture
def mock_cosmos_db_service() -> MockCosmosService:
    """Provide a mock Cosmos DB service."""
    return MockCosmosService()


@pytest.fixture
def mock_langchain_service() -> MockLangchainService:
    """Provide a mock LangChain service."""
    return MockLangchainService()


@pytest.fixture
def mock_langgraph_agent_service() -> MockLanggraphAgentService:
    """Provide a mock LangGraph agent service."""
    return MockLanggraphAgentService()


@pytest.fixture
def mock_document_service() -> MockDocumentService:
    """Provide a mock document service."""
    return MockDocumentService()


@pytest.fixture
def mock_super_admin_user() -> TenantContext:
    """Mock super admin user context."""
    return TenantContext(
        user_id="admin-123",
        tenant_id=None,
        tenant_role=TenantUserRole.SUPER_ADMIN,
        is_super_admin_user=True,
    )


@pytest.fixture
def mock_tenant_admin_user() -> TenantContext:
    """Mock tenant admin user context."""
    return TenantContext(
        user_id="tenant-admin-123",
        tenant_id="tenant-123",
        tenant_role=TenantUserRole.TENANT_ADMIN,
        is_super_admin_user=False,
    )


@pytest.fixture
def mock_regular_user() -> TenantContext:
    """Mock regular tenant user context."""
    return TenantContext(
        user_id="user-123",
        tenant_id="tenant-123",
        tenant_role=TenantUserRole.TENANT_USER_READ,
        is_super_admin_user=False,
    )


class TestDependencyOverrides:
    """Helper class to manage dependency overrides for tests."""

    def __init__(
        self,
        app: FastAPI,
        multi_tenant_service: AsyncMock,
        cosmos_service: MockCosmosService,
        langchain_service: MockLangchainService,
        langgraph_agent_service: MockLanggraphAgentService,
        document_service: MockDocumentService,
    ) -> None:
        self.app = app
        self.multi_tenant_service = multi_tenant_service
        self.cosmos_service = cosmos_service
        self.langchain_service = langchain_service
        self.langgraph_agent_service = langgraph_agent_service
        self.document_service = document_service
        self._applied_keys: set = set()
        self.current_user: KeycloakUser | None = None

    def _set_override(self, dependency, handler) -> None:
        self.app.dependency_overrides[dependency] = handler
        self._applied_keys.add(dependency)

    def set_user_context(self, user_context: TenantContext) -> None:
        """Set the user context for authentication dependencies."""
        self.current_user = _build_keycloak_user(user_context)

        async def override_current_user():
            return self.current_user

        def mock_require_super_admin():
            if not user_context.is_super_admin():
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied. Super admin required.",
                )
            return user_context

        def mock_require_tenant_admin():
            has_admin_role = user_context.has_role(TenantUserRole.TENANT_ADMIN)
            if not has_admin_role and not user_context.is_super_admin():
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied. Tenant admin required.",
                )
            return user_context

        def mock_get_tenant_context():
            return user_context

        self._set_override(get_current_user, override_current_user)
        self._set_override(get_multi_tenant_service, lambda: self.multi_tenant_service)
        self._set_override(get_cosmos_db_service, lambda: self.cosmos_service)
        self._set_override(get_langchain_ai_service, lambda: self.langchain_service)
        self._set_override(get_langgraph_agent_service, lambda: self.langgraph_agent_service)
        self._set_override(get_document_service, lambda: self.document_service)
        self._set_override(require_super_admin, mock_require_super_admin)
        self._set_override(require_tenant_admin, mock_require_tenant_admin)
        self._set_override(get_tenant_context, mock_get_tenant_context)

    def clear_overrides(self) -> None:
        """Clear all dependency overrides."""
        for dependency in self._applied_keys:
            self.app.dependency_overrides.pop(dependency, None)
        self._applied_keys.clear()
        self.current_user = None


@pytest.fixture
async def async_client(
    test_app: FastAPI,
    mock_multi_tenant_service: AsyncMock,
    mock_cosmos_db_service: MockCosmosService,
    mock_langchain_service: MockLangchainService,
    mock_langgraph_agent_service: MockLanggraphAgentService,
    mock_document_service: MockDocumentService,
    mock_super_admin_user: TenantContext,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create an async test client with dependency overrides."""

    override_manager = TestDependencyOverrides(
        test_app,
        mock_multi_tenant_service,
        mock_cosmos_db_service,
        mock_langchain_service,
        mock_langgraph_agent_service,
        mock_document_service,
    )

    override_manager.set_user_context(mock_super_admin_user)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        client.override_manager = override_manager
        yield client

    override_manager.clear_overrides()


@pytest.fixture
async def async_client_tenant_admin(
    test_app: FastAPI,
    mock_multi_tenant_service: AsyncMock,
    mock_cosmos_db_service: MockCosmosService,
    mock_langchain_service: MockLangchainService,
    mock_langgraph_agent_service: MockLanggraphAgentService,
    mock_document_service: MockDocumentService,
    mock_tenant_admin_user: TenantContext,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create an async test client with tenant admin context."""

    override_manager = TestDependencyOverrides(
        test_app,
        mock_multi_tenant_service,
        mock_cosmos_db_service,
        mock_langchain_service,
        mock_langgraph_agent_service,
        mock_document_service,
    )

    override_manager.set_user_context(mock_tenant_admin_user)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        client.override_manager = override_manager
        yield client

    override_manager.clear_overrides()


@pytest.fixture
async def async_client_regular_user(
    test_app: FastAPI,
    mock_multi_tenant_service: AsyncMock,
    mock_cosmos_db_service: MockCosmosService,
    mock_langchain_service: MockLangchainService,
    mock_langgraph_agent_service: MockLanggraphAgentService,
    mock_document_service: MockDocumentService,
    mock_regular_user: TenantContext,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create an async test client with regular user context."""

    override_manager = TestDependencyOverrides(
        test_app,
        mock_multi_tenant_service,
        mock_cosmos_db_service,
        mock_langchain_service,
        mock_langgraph_agent_service,
        mock_document_service,
    )

    override_manager.set_user_context(mock_regular_user)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        client.override_manager = override_manager
        yield client

    override_manager.clear_overrides()
