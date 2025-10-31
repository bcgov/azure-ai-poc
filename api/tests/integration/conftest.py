"""Integration test configuration and fixtures."""

import asyncio
import os
import sys

import pytest

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
    """Return a fake bearer token for authenticated integration requests."""
    return os.getenv("BEARER_TOKEN", "test-token")


@pytest.fixture(scope="session")
def auth_headers(bearer_token: str) -> dict[str, str]:
    """Create authorization headers for API requests."""
    return {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
    }


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
