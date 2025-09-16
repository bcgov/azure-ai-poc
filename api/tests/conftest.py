"""Test configuration and fixtures for Azure AI POC API tests."""

import os
import sys
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add the app directory to the Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from app.main import create_app


@pytest.fixture(scope="session")
def test_app() -> FastAPI:
    """Create a test FastAPI application."""
    # Set test environment variables
    os.environ["ENVIRONMENT"] = "test"
    os.environ["LOG_LEVEL"] = "DEBUG"

    # Create test app
    app = create_app()
    return app


@pytest.fixture(scope="session")
def client(test_app: FastAPI) -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(test_app)


@pytest_asyncio.fixture
async def async_client(test_app: FastAPI) -> AsyncGenerator[TestClient, None]:
    """Create an async test client for the FastAPI application."""
    async with TestClient(test_app) as client:
        yield client


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    test_env_vars = {
        "ENVIRONMENT": "test",
        "LOG_LEVEL": "DEBUG",
        "RATE_LIMIT_MAX_REQUESTS": "100",
        "RATE_LIMIT_TTL": "60000",
        "AZURE_OPENAI_LLM_ENDPOINT": "https://test.openai.azure.com",
        "AZURE_OPENAI_LLM_DEPLOYMENT_NAME": "test-gpt-4",
        "AZURE_OPENAI_EMBEDDING_ENDPOINT": "https://test.openai.azure.com",
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME": "test-embedding",
        "COSMOS_DB_ENDPOINT": "https://test.documents.azure.com:443/",
        "COSMOS_DB_DATABASE_NAME": "test-db",
        "COSMOS_DB_CONTAINER_NAME": "test-container",
    }

    for key, value in test_env_vars.items():
        monkeypatch.setenv(key, value)

    return test_env_vars


@pytest.fixture
def sample_document_content():
    """Sample document content for testing."""
    return {
        "text": (
            "This is a sample document for testing purposes. It contains "
            "information about Azure AI services and document processing."
        ),
        "filename": "test_document.txt",
        "total_pages": 1,
    }


@pytest.fixture
def sample_embedding():
    """Sample embedding vector for testing."""
    return [0.1, 0.2, 0.3, 0.4, 0.5] * 200  # 1000-dimensional vector


@pytest.fixture
def sample_jwt_token():
    """Sample JWT token for testing authentication."""
    return (
        "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6InRlc3QifQ."
        "eyJzdWIiOiJ0ZXN0LXVzZXIiLCJyZWFsbV9hY2Nlc3MiOnsicm9sZXMi"
        "OlsiYWktcG9jLXBhcnRpY2lwYW50Il19fQ.test-signature"
    )


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "sub": "test-user-123",
        "email": "test@example.com",
        "preferred_username": "testuser",
        "given_name": "Test",
        "family_name": "User",
        "realm_access": {"roles": ["ai-poc-participant"]},
    }
