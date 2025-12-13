"""Test fixtures and configuration."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.models import KeycloakUser
from app.main import app


# Mock user for tests
MOCK_USER = KeycloakUser(
    sub="test-user-123",
    email="test@example.com",
    preferred_username="testuser",
    given_name="Test",
    family_name="User",
    client_roles=["ai-poc-participant"],
    roles=["ai-poc-participant"],
    aud="azure-poc-6086",
)


@pytest.fixture
def mock_auth_service():
    """Mock the auth service to return a test user."""
    with patch("app.middleware.auth_middleware.get_auth_service") as mock:
        mock_service = AsyncMock()
        mock_service.validate_token = AsyncMock(return_value=MOCK_USER)
        mock.return_value = mock_service
        yield mock_service


@pytest.fixture
def client(mock_auth_service) -> TestClient:
    """Create a test client with mocked authentication."""
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Return authorization headers for authenticated requests."""
    return {"Authorization": "Bearer test-token-123"}


@pytest.fixture
def unauthenticated_client() -> TestClient:
    """Create a test client without mocked authentication (for testing auth failures)."""
    return TestClient(app)
