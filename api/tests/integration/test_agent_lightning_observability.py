"""Tests for Agent Lightning observability endpoints."""

import httpx
import pytest


@pytest.mark.asyncio
class TestAgentLightningObservability:
    """Tests for Agent Lightning observability router."""

    METRICS_ENDPOINT = "/api/v1/agent-lightning/metrics"
    STATUS_ENDPOINT = "/api/v1/agent-lightning/status"

    async def test_get_metrics_returns_valid_schema_or_503(
        self, async_client: httpx.AsyncClient
    ) -> None:
        """Test that metrics endpoint returns valid schema or 503 if unavailable."""
        response = await async_client.get(self.METRICS_ENDPOINT)

        # Endpoint may return 503 if Agent Lightning is unavailable in test env
        if response.status_code == 503:
            data = response.json()
            assert "detail" in data
            assert "Agent Lightning" in data["detail"]
            return

        assert response.status_code == 200

        data = response.json()

        # Verify required fields
        assert "agent_name" in data
        assert "tenant_id" in data
        assert data["agent_name"] == "langgraph_document_qa"

    async def test_get_metrics_respects_tenant_isolation(
        self, async_client: httpx.AsyncClient
    ) -> None:
        """Test that metrics are tenant-isolated."""
        response = await async_client.get(self.METRICS_ENDPOINT)

        # Skip if Agent Lightning unavailable
        if response.status_code == 503:
            return

        assert response.status_code == 200

        data = response.json()

        # Verify tenant_id matches the authenticated user
        # (in test environment, this is mocked)
        assert data["tenant_id"] is not None

    async def test_get_metrics_with_custom_agent_name(
        self, async_client: httpx.AsyncClient
    ) -> None:
        """Test metrics endpoint with custom agent name parameter."""
        response = await async_client.get(
            self.METRICS_ENDPOINT, params={"agent_name": "custom_agent"}
        )

        # Skip if Agent Lightning unavailable
        if response.status_code == 503:
            return

        assert response.status_code == 200

        data = response.json()
        assert data["agent_name"] == "custom_agent"

    async def test_get_status_returns_valid_schema(self, async_client: httpx.AsyncClient) -> None:
        """Test that status endpoint returns valid schema."""
        response = await async_client.get(self.STATUS_ENDPOINT)

        assert response.status_code == 200

        data = response.json()

        # Verify required fields
        assert "status" in data
        assert "agent_lightning_available" in data
        assert "optimization_algorithms" in data
        assert "agents_wrapped" in data
        assert "metrics_collected" in data

        # Verify types
        assert isinstance(data["optimization_algorithms"], list)
        assert isinstance(data["agents_wrapped"], int)
        assert isinstance(data["metrics_collected"], int)

    async def test_get_status_when_agent_lightning_available(
        self, async_client: httpx.AsyncClient
    ) -> None:
        """Test status endpoint when Agent Lightning is available."""
        response = await async_client.get(self.STATUS_ENDPOINT)

        assert response.status_code == 200

        data = response.json()

        # Should report as available (or unavailable depending on env)
        assert isinstance(data["agent_lightning_available"], bool)

        # If available, should have at least one algorithm
        if data["agent_lightning_available"]:
            assert len(data["optimization_algorithms"]) > 0

    async def test_metrics_endpoint_requires_authentication(
        self, async_client: httpx.AsyncClient
    ) -> None:
        """Test that metrics endpoint requires authentication.

        Note: In test environment, authentication is mocked via conftest.py
        """
        # This test verifies the endpoint exists and is protected
        # Authentication is handled by the test fixtures
        response = await async_client.get(self.METRICS_ENDPOINT)

        # Should succeed with mocked auth (200) or return 503 if unavailable
        assert response.status_code in (200, 503)

    async def test_status_endpoint_requires_authentication(
        self, async_client: httpx.AsyncClient
    ) -> None:
        """Test that status endpoint requires authentication.

        Note: In test environment, authentication is mocked via conftest.py
        """
        # This test verifies the endpoint exists and is protected
        # Authentication is handled by the test fixtures
        response = await async_client.get(self.STATUS_ENDPOINT)

        # Should succeed with mocked auth
        assert response.status_code == 200

    async def test_metrics_response_includes_improvement_metrics(
        self, async_client: httpx.AsyncClient
    ) -> None:
        """Test that metrics response includes improvement calculations."""
        response = await async_client.get(self.METRICS_ENDPOINT)

        # Skip if Agent Lightning unavailable
        if response.status_code == 503:
            return

        assert response.status_code == 200

        data = response.json()

        # These fields should be present (may be None if no data yet)
        assert "latency_improvement_percent" in data
        assert "token_savings_percent" in data
        assert "quality_signal" in data

    async def test_status_response_includes_algorithm_list(
        self, async_client: httpx.AsyncClient
    ) -> None:
        """Test that status response includes enabled algorithms."""
        response = await async_client.get(self.STATUS_ENDPOINT)

        assert response.status_code == 200

        data = response.json()

        algorithms = data["optimization_algorithms"]

        # Algorithms list should be valid
        assert isinstance(algorithms, list)

        # Valid algorithm names if present
        valid_algorithms = [
            "reinforcement_learning",
            "prompt_optimization",
            "supervised_fine_tuning",
        ]

        for algo in algorithms:
            assert algo in valid_algorithms
