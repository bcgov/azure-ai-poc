"""Contract tests for Agent Lightning optimization endpoints.

T027: Contract tests to ensure consistent API schemas across calls.
"""

import pytest
from fastapi import status
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
class TestOptimizationEndpointsContract:
    """Contract tests for optimization endpoints."""

    async def test_metrics_endpoint_contract(self) -> None:
        """Test GET /metrics endpoint returns consistent schema."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Make multiple calls
            response1 = await client.get(
                "/api/v1/agent-lightning/metrics",
                headers={"x-tenant-id": "test-tenant"},
            )
            response2 = await client.get(
                "/api/v1/agent-lightning/metrics",
                headers={"x-tenant-id": "test-tenant"},
            )

            # Both should succeed
            assert response1.status_code == status.HTTP_200_OK
            assert response2.status_code == status.HTTP_200_OK

            data1 = response1.json()
            data2 = response2.json()

            # Schema should be consistent
            assert set(data1.keys()) == set(data2.keys())

            # Should have required fields
            assert "tenant_id" in data1
            assert "agent_name" in data1
            assert "baseline_metrics" in data1
            assert "optimization_status" in data1

    async def test_start_optimization_endpoint_contract(self) -> None:
        """Test POST /start-optimization endpoint returns consistent schema."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_body = {
                "agent_name": "document_qa",
                "metric_target": "answer_quality",
            }

            # Make multiple calls
            response1 = await client.post(
                "/api/v1/agent-lightning/start-optimization",
                json=request_body,
                headers={"x-tenant-id": "test-tenant"},
            )
            response2 = await client.post(
                "/api/v1/agent-lightning/start-optimization",
                json=request_body,
                headers={"x-tenant-id": "test-tenant"},
            )

            # Both should return accepted or success
            assert response1.status_code in [
                status.HTTP_200_OK,
                status.HTTP_202_ACCEPTED,
            ]
            assert response2.status_code in [
                status.HTTP_200_OK,
                status.HTTP_202_ACCEPTED,
            ]

            data1 = response1.json()
            data2 = response2.json()

            # Schema should be consistent
            assert set(data1.keys()) == set(data2.keys())

            # Should have required fields
            assert "status" in data1
            assert "agent_name" in data1
            assert data1["status"] in ["started", "running", "queued", "completed"]

    async def test_roi_report_endpoint_contract(self) -> None:
        """Test GET /roi-report endpoint returns consistent schema."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Make multiple calls
            response1 = await client.get(
                "/api/v1/agent-lightning/roi-report",
                headers={"x-tenant-id": "test-tenant"},
            )
            response2 = await client.get(
                "/api/v1/agent-lightning/roi-report",
                headers={"x-tenant-id": "test-tenant"},
            )

            # Both should succeed
            assert response1.status_code == status.HTTP_200_OK
            assert response2.status_code == status.HTTP_200_OK

            data1 = response1.json()
            data2 = response2.json()

            # Schema should be consistent
            assert set(data1.keys()) == set(data2.keys())

            # Should have required fields
            assert "tenant_id" in data1
            assert "baseline_metrics" in data1
            assert "current_metrics" in data1
            assert "improvement" in data1
            assert "token_savings" in data1
            assert "cost_roi" in data1

            # Improvement should have expected structure
            improvement1 = data1["improvement"]
            assert "quality_improvement" in improvement1
            assert "latency_improvement" in improvement1
            assert "token_improvement" in improvement1

            # Token savings should have expected structure
            token_savings1 = data1["token_savings"]
            assert "tokens_saved_per_query" in token_savings1
            assert "total_tokens_saved" in token_savings1

            # Cost ROI should have expected structure
            cost_roi1 = data1["cost_roi"]
            assert "cost_saved_usd" in cost_roi1
            assert "net_roi_usd" in cost_roi1
            assert "roi_percent" in cost_roi1

    async def test_tenant_isolation_in_optimization_endpoints(self) -> None:
        """Test optimization endpoints respect tenant isolation."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Request from tenant 1
            response1 = await client.get(
                "/api/v1/agent-lightning/roi-report",
                headers={"x-tenant-id": "tenant-1"},
            )

            # Request from tenant 2
            response2 = await client.get(
                "/api/v1/agent-lightning/roi-report",
                headers={"x-tenant-id": "tenant-2"},
            )

            assert response1.status_code == status.HTTP_200_OK
            assert response2.status_code == status.HTTP_200_OK

            data1 = response1.json()
            data2 = response2.json()

            # Each tenant should see their own data
            assert data1["tenant_id"] == "tenant-1"
            assert data2["tenant_id"] == "tenant-2"

    async def test_optimization_endpoints_require_tenant_header(self) -> None:
        """Test optimization endpoints require x-tenant-id header."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Request without tenant header
            response = await client.get("/api/v1/agent-lightning/roi-report")

            # Should return 400 or 401
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_401_UNAUTHORIZED,
            ]
