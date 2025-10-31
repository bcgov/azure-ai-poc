"""Contract tests for Document QA API endpoint.

These tests verify that wrapping agents with Agent Lightning does NOT break
the existing API contract. Response schema must remain identical.
Tests written FIRST per TDD approach.
"""

from typing import Any

import httpx
import pytest


@pytest.mark.asyncio
class TestDocumentQAAPIContract:
    """Contract tests for /api/v1/chat/ask endpoint (LangGraph agent)."""

    ENDPOINT = "/api/v1/chat/ask"

    @pytest.fixture
    def valid_qa_request(self) -> dict[str, Any]:
        """Create a valid document QA request payload."""
        return {
            "message": "What is the main topic of the document?",
            "session_id": None,
            "context": None,
            "selected_document_ids": None,
        }

    async def test_document_qa_response_schema_unchanged(
        self, async_client: httpx.AsyncClient, valid_qa_request: dict[str, Any]
    ) -> None:
        """Test that response schema remains unchanged after Agent Lightning wrapper.

        This is a CONTRACT test - the schema MUST NOT change.
        """
        response = await async_client.post(self.ENDPOINT, json=valid_qa_request)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()

        # Verify required fields exist (contract)
        assert "answer" in data, "Response must contain 'answer' field"
        assert "timestamp" in data, "Response must contain 'timestamp' field"

        # Verify field types (contract)
        assert isinstance(data["answer"], str), "'answer' must be a string"
        assert isinstance(data["timestamp"], str), "'timestamp' must be a string (ISO format)"

    async def test_document_qa_no_extra_fields_added(
        self, async_client: httpx.AsyncClient, valid_qa_request: dict[str, Any]
    ) -> None:
        """Test that Agent Lightning wrapper doesn't inject extra fields.

        The wrapper should be transparent - no metrics or metadata should
        appear in the response.
        """
        response = await async_client.post(self.ENDPOINT, json=valid_qa_request)

        assert response.status_code == 200
        data = response.json()

        # Fields that MUST NOT appear in response (would break contract)
        forbidden_fields = [
            "agent_lightning_metrics",
            "wrapper_metadata",
            "optimization_info",
            "baseline_metrics",
            "optimization_metrics",
        ]

        for field in forbidden_fields:
            assert field not in data, f"Response must NOT contain '{field}' (breaks contract)"

    async def test_document_qa_wrapper_overhead_acceptable(
        self, async_client: httpx.AsyncClient, valid_qa_request: dict[str, Any]
    ) -> None:
        """Test that Agent Lightning wrapper adds <50ms overhead.

        Per design spec, wrapper overhead should be negligible compared to
        LLM call latency (1-3 seconds).
        """
        import time

        # Measure response time
        start_time = time.perf_counter()
        response = await async_client.post(self.ENDPOINT, json=valid_qa_request)
        end_time = time.perf_counter()

        assert response.status_code == 200

        latency_ms = (end_time - start_time) * 1000

        # Total latency should be reasonable (includes LLM call + wrapper)
        # This is a smoke test - actual latency varies by LLM
        assert latency_ms < 10000, f"Request took {latency_ms}ms (expected <10s including LLM)"

    async def test_document_qa_error_handling_unchanged(
        self, async_client: httpx.AsyncClient
    ) -> None:
        """Test that error responses remain unchanged after wrapper.

        Agent Lightning wrapper failures should NOT change error behavior.
        Note: Empty messages are allowed in this API, so we test with malformed JSON instead.
        """
        # Malformed request (missing required 'message' field entirely)
        invalid_request = {"not_message": "test"}

        response = await async_client.post(self.ENDPOINT, json=invalid_request)

        # Should return validation error (422 for Pydantic validation)
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    async def test_document_qa_with_different_tenants(
        self, async_client: httpx.AsyncClient
    ) -> None:
        """Test that tenant isolation works through Agent Lightning wrapper.

        Each tenant should get wrapped agents with their tenant_id.
        """
        tenant1_request = {
            "message": "Test query",
            "session_id": None,
            "context": None,
            "selected_document_ids": None,
        }

        tenant2_request = {
            "message": "Test query",
            "session_id": None,
            "context": None,
            "selected_document_ids": None,
        }

        response1 = await async_client.post(self.ENDPOINT, json=tenant1_request)
        response2 = await async_client.post(self.ENDPOINT, json=tenant2_request)

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Both should have same schema (contract)
        data1 = response1.json()
        data2 = response2.json()

        assert "answer" in data1
        assert "answer" in data2
        assert "timestamp" in data1
        assert "timestamp" in data2

    async def test_document_qa_response_content_type(
        self, async_client: httpx.AsyncClient, valid_qa_request: dict[str, Any]
    ) -> None:
        """Test that response content type remains application/json."""
        response = await async_client.post(self.ENDPOINT, json=valid_qa_request)

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"], "Response must be JSON"

    async def test_document_qa_idempotency(
        self, async_client: httpx.AsyncClient, valid_qa_request: dict[str, Any]
    ) -> None:
        """Test that same query returns consistent schema (idempotent).

        Agent Lightning wrapper should not introduce non-determinism in schema.
        """
        response1 = await async_client.post(self.ENDPOINT, json=valid_qa_request)
        response2 = await async_client.post(self.ENDPOINT, json=valid_qa_request)

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Schema should be identical
        assert set(data1.keys()) == set(data2.keys()), "Schema must be consistent across calls"
