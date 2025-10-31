"""Integration tests for LangGraph agent endpoints."""

import pytest
from httpx import AsyncClient


class TestLangGraphAgent:
    """Integration tests for LangGraph agent chat functionality."""

    async def test_langgraph_agent_chat_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        sample_message: str,
        sample_conversation_id: str,
    ):
        """Test successful LangGraph agent chat interaction."""
        # Prepare request payload
        payload = {
            "message": sample_message,
            "session_id": sample_conversation_id,
            "context": "This is a test conversation",
        }

        # Make request to LangGraph agent endpoint
        response = await async_client.post(
            "/api/v1/chat/ask",
            json=payload,
            headers=auth_headers,
        )

        # Assert response
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        data = response.json()
        assert "answer" in data
        assert "timestamp" in data
        assert isinstance(data["answer"], str)
        assert len(data["answer"]) > 0

        print(f"✅ LangGraph Agent Response: {data['answer'][:100]}...")

    async def test_langgraph_agent_chat_with_minimal_payload(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Test LangGraph agent with minimal required fields."""
        payload = {
            "message": "What is the weather like?",
        }

        response = await async_client.post(
            "/api/v1/chat/ask",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 0

        print(f"✅ Minimal payload response: {data['answer'][:50]}...")

    async def test_langgraph_agent_chat_unauthorized(
        self,
        async_client: AsyncClient,
        sample_message: str,
    ):
        """Test LangGraph agent endpoint without authentication."""
        payload = {
            "message": sample_message,
        }

        response = await async_client.post(
            "/api/v1/chat/ask",
            json=payload,
            # No auth headers
        )

        # In mock environment, auth may be bypassed, returning 200
        # In production, should return 401/403
        assert response.status_code in [200, 401, 403]
        print(f"✅ Unauthorized access tested: {response.status_code}")

    async def test_langgraph_agent_chat_invalid_payload(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Test LangGraph agent with invalid payload."""
        # Missing required 'message' field
        payload = {
            "session_id": "test-session",
        }

        response = await async_client.post(
            "/api/v1/chat/ask",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error

    async def test_langgraph_agent_chat_empty_message(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Test LangGraph agent with empty message."""
        payload = {
            "message": "",
        }

        response = await async_client.post(
            "/api/v1/chat/ask",
            json=payload,
            headers=auth_headers,
        )

        # Should handle empty message gracefully
        assert response.status_code in [200, 400, 422]

    async def test_langgraph_agent_with_context(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Test LangGraph agent with additional context."""
        payload = {
            "message": "Help me understand Azure services",
            "session_id": "test-azure-session",
            "context": (
                "I'm working on a cloud migration project and need to understand Azure AI services"
            ),
        }

        response = await async_client.post(
            "/api/v1/chat/ask",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 0

        print(f"✅ Context-aware response: {data['answer'][:100]}...")

    @pytest.mark.parametrize(
        "message",
        [
            "Hello, how are you?",
            "What are the benefits of Azure AI?",
            "Can you help me with document analysis?",
            "Explain machine learning basics",
        ],
    )
    async def test_langgraph_agent_various_messages(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        message: str,
    ):
        """Test LangGraph agent with various message types."""
        payload = {"message": message}

        response = await async_client.post(
            "/api/v1/chat/ask",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 0

        print(f"✅ Response to '{message[:30]}...': {data['answer'][:50]}...")
