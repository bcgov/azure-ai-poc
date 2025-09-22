"""Integration test configuration and fixtures."""

import asyncio
import os
import sys
from collections.abc import AsyncGenerator, Generator

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app

# Fix for Windows event loop issues
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    if sys.platform.startswith("win"):
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def bearer_token() -> str:
    """Get Bearer token for authentication.

    First tries environment variable, then prompts user if needed.
    """
    token = os.getenv("BEARER_TOKEN")
    if not token:
        print("\n" + "=" * 60)
        print("BEARER TOKEN REQUIRED FOR INTEGRATION TESTS")
        print("=" * 60)
        print("Please paste your Bearer token (without 'Bearer ' prefix):")
        token = input().strip()
        if not token:
            pytest.skip("No Bearer token provided - skipping integration tests")
    return token


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """Get API base URL from environment or use default."""
    return os.getenv("API_BASE_URL", "http://localhost:3001")


@pytest.fixture(scope="session")
def auth_headers(bearer_token: str) -> dict[str, str]:
    """Create authorization headers for API requests."""
    return {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
    }


@pytest.fixture(scope="session")
async def async_client(api_base_url: str) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create async HTTP client for integration tests."""
    # Use a context manager that handles cleanup better
    client = httpx.AsyncClient(
        base_url=api_base_url,
        timeout=httpx.Timeout(30.0),  # 30 second timeout for AI operations
    )
    try:
        yield client
    finally:
        # Use a try-except to handle any cleanup issues
        try:
            await client.aclose()
        except Exception:
            pass  # Ignore cleanup errors on Windows


@pytest.fixture(scope="session")
def sync_client(api_base_url: str) -> Generator[httpx.Client, None, None]:
    """Create sync HTTP client for integration tests."""
    with httpx.Client(
        base_url=api_base_url,
        timeout=httpx.Timeout(30.0),
    ) as client:
        yield client


@pytest.fixture(scope="session")
def test_client() -> Generator[TestClient, None, None]:
    """Create FastAPI test client for integration tests."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_message() -> str:
    """Sample message for testing chat endpoints."""
    return "Hello, this is a test message. Please respond briefly."


@pytest.fixture
def sample_conversation_id() -> str:
    """Sample conversation ID for testing."""
    return "test-conversation-123"


@pytest.fixture
def sample_workflow_id() -> str:
    """Sample workflow ID for testing advanced agent."""
    return "test-workflow-456"
