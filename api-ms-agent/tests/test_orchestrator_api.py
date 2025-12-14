"""Tests for orchestrator API session continuity."""

from unittest.mock import AsyncMock, patch

from app.main import app
from app.services.cosmos_db_service import get_cosmos_db_service


def test_orchestrator_endpoint_returns_session_id_and_persists_messages(client, auth_headers):
    """Orchestrator should resolve a session_id (user-scoped) and persist messages."""

    mock_cosmos = AsyncMock()
    mock_cosmos.get_user_sessions.return_value = [
        type("Sess", (), {"session_id": "orch_latest_2"})()
    ]
    mock_cosmos.get_chat_history.return_value = []
    mock_cosmos.save_message.return_value = None

    mock_orchestrator = AsyncMock()
    mock_orchestrator.process_query.return_value = {
        "response": "Result",
        "sources": [
            {
                "source_type": "llm_knowledge",
                "description": "Mock",
                "confidence": "high",
            }
        ],
        "has_sufficient_info": True,
        "key_findings": [],
    }

    app.dependency_overrides[get_cosmos_db_service] = lambda: mock_cosmos

    try:
        with patch(
            "app.routers.orchestrator.get_orchestrator_agent", return_value=mock_orchestrator
        ):
            response = client.post(
                "/api/v1/orchestrator/query",
                json={"query": "Hello"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["session_id"] == "orch_latest_2"
        assert payload["response"] == "Result"
        assert len(payload["sources"]) >= 1

        # Ensure we query only orchestrator-scoped sessions
        get_sessions_kwargs = mock_cosmos.get_user_sessions.await_args.kwargs
        assert get_sessions_kwargs.get("session_id_prefix") == "orch_"

        # Ensure messages were persisted
        assert mock_cosmos.save_message.await_count >= 2  # user + assistant
        assert mock_orchestrator.process_query.await_count == 1
        orch_kwargs = mock_orchestrator.process_query.await_args.kwargs
        assert orch_kwargs["session_id"] == "orch_latest_2"
        assert orch_kwargs["user_id"] == "test-user-123"
    finally:
        app.dependency_overrides.clear()
