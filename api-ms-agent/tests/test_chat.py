"""Tests for the chat API."""

from unittest.mock import AsyncMock

from app.main import app
from app.services.chat_agent import ChatResult, SourceInfo, get_chat_agent_service
from app.services.cosmos_db_service import get_cosmos_db_service

# Note: client and auth_headers fixtures are now provided by conftest.py


def test_root(client, auth_headers):
    """Test root endpoint."""
    # Root endpoint is excluded from auth, so no headers needed
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_health(client, auth_headers):
    """Test health endpoint."""
    # Health endpoint is excluded from auth, so no headers needed
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_chat_health(client, auth_headers):
    """Test chat health endpoint."""
    # Chat health endpoint is excluded from auth
    response = client.get("/api/v1/chat/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_endpoint(client, auth_headers):
    """Test chat endpoint with mocked service."""
    # Create mock service with new ChatResult structure
    mock_service = AsyncMock()
    mock_service.chat.return_value = ChatResult(
        response="Hello! I'm doing well, thank you.",
        sources=[
            SourceInfo(
                source_type="llm_knowledge",
                description="Based on AI model's training knowledge",
                confidence="high",
            )
        ],
        has_sufficient_info=True,
    )

    # Override dependency
    app.dependency_overrides[get_chat_agent_service] = lambda: mock_service

    try:
        response = client.post(
            "/api/v1/chat/",
            json={"message": "Hello, how are you?"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert data["response"] == "Hello! I'm doing well, thank you."
        assert "session_id" in data
        # Verify sources are included in response
        assert "sources" in data
        assert len(data["sources"]) > 0
        assert data["sources"][0]["source_type"] == "llm_knowledge"
        assert "has_sufficient_info" in data
        assert data["has_sufficient_info"] is True
    finally:
        # Clean up override
        app.dependency_overrides.clear()


def test_chat_endpoint_reuses_latest_session_when_missing_session_id(client, auth_headers):
    """If session_id is omitted, the API should reuse the user's latest Cosmos session."""

    # Mock chat agent
    mock_agent = AsyncMock()
    mock_agent.chat.return_value = ChatResult(
        response="OK",
        sources=[
            SourceInfo(
                source_type="llm_knowledge",
                description="Based on AI model's training knowledge",
                confidence="high",
            )
        ],
        has_sufficient_info=True,
    )

    # Mock Cosmos
    mock_cosmos = AsyncMock()
    mock_cosmos.get_user_sessions.return_value = [
        type("Sess", (), {"session_id": "session_latest_1"})()
    ]
    mock_cosmos.get_chat_history.return_value = []
    mock_cosmos.save_message.return_value = None

    app.dependency_overrides[get_chat_agent_service] = lambda: mock_agent
    app.dependency_overrides[get_cosmos_db_service] = lambda: mock_cosmos

    try:
        response = client.post(
            "/api/v1/chat/",
            json={"message": "Hello"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        payload = response.json()

        assert payload["session_id"] == "session_latest_1"

        # Ensure we query only chat-scoped sessions
        get_sessions_kwargs = mock_cosmos.get_user_sessions.await_args.kwargs
        assert get_sessions_kwargs.get("session_id_prefix") == "session_"

        # Save-message should be called at least once with the selected session
        assert mock_cosmos.save_message.await_count >= 1
        first_call_kwargs = mock_cosmos.save_message.await_args_list[0].kwargs
        assert first_call_kwargs["session_id"] == "session_latest_1"
    finally:
        app.dependency_overrides.clear()


def test_chat_endpoint_insufficient_info(client, auth_headers):
    """Test chat endpoint when AI doesn't have sufficient information."""
    # Create mock service with insufficient info response
    mock_service = AsyncMock()
    mock_service.chat.return_value = ChatResult(
        response="I don't have enough information to answer this question accurately.",
        sources=[],
        has_sufficient_info=False,
    )

    # Override dependency
    app.dependency_overrides[get_chat_agent_service] = lambda: mock_service

    try:
        response = client.post(
            "/api/v1/chat/",
            json={"message": "What is the exact revenue of company X in 2025?"},
            headers=auth_headers,
        )

        assert response.status_code == 500
        data = response.json()
        assert "citations" in data.get("detail", "").lower()
    finally:
        # Clean up override
        app.dependency_overrides.clear()
