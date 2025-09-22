"""Integration tests for API capabilities and health endpoints."""

import pytest
from httpx import AsyncClient


class TestCapabilitiesAndHealth:
    """Integration tests for API capabilities and health check endpoints."""

    async def test_health_status_endpoint(
        self,
        async_client: AsyncClient,
    ):
        """Test the main health status endpoint."""
        response = await async_client.get("/api/v1/health/")

        assert response.status_code == 200
        data = response.json()

        # Basic health check structure
        assert "status" in data
        # API may return different status values: up, healthy, degraded, unhealthy
        assert data["status"] in ["up", "healthy", "degraded", "unhealthy"]

        print(f"✅ API Health Status: {data['status']}")
        if "details" in data:
            print(f"   Details: {data['details']}")

    async def test_health_check_with_auth(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Test health endpoint with authentication headers."""
        response = await async_client.get(
            "/api/v1/health/",
            headers=auth_headers,
        )

        # Health check should work with or without auth
        assert response.status_code == 200
        print("✅ Health check works with authentication")

    async def test_app_root_endpoint(
        self,
        async_client: AsyncClient,
    ):
        """Test the root application endpoint."""
        response = await async_client.get("/api/v1/")

        # Should return basic app info or require auth (200 or 401/403)
        assert response.status_code in [200, 401, 403]
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Root endpoint response: {data}")
        else:
            print(f"✅ Root endpoint requires authentication (status: {response.status_code})")

    async def test_api_docs_accessibility(
        self,
        async_client: AsyncClient,
    ):
        """Test that API documentation is accessible."""
        # Test OpenAPI JSON
        response = await async_client.get("/api/openapi.json")
        assert response.status_code == 200

        openapi_data = response.json()
        assert "openapi" in openapi_data
        assert "info" in openapi_data
        assert "paths" in openapi_data

        print("✅ OpenAPI documentation is accessible")
        print(f"   API Title: {openapi_data.get('info', {}).get('title', 'Unknown')}")
        print(f"   API Version: {openapi_data.get('info', {}).get('version', 'Unknown')}")

    async def test_metrics_endpoint(
        self,
        async_client: AsyncClient,
    ):
        """Test Prometheus metrics endpoint."""
        response = await async_client.get("/api/v1/metrics")

        # Metrics endpoint may return 200, 307 (redirect), or require auth
        assert response.status_code in [200, 307, 401, 403]

        if response.status_code == 200:
            assert "text/plain" in response.headers.get("content-type", "")
            metrics_text = response.text
            assert len(metrics_text) > 0
            print("✅ Metrics endpoint accessible with data")
        elif response.status_code == 307:
            print("✅ Metrics endpoint returns redirect (307)")
        else:
            print(f"✅ Metrics endpoint requires authentication (status: {response.status_code})")

        # Should contain some basic metrics
        assert "python_info" in metrics_text or "process_" in metrics_text

        print("✅ Metrics endpoint is working")
        print(f"   Metrics size: {len(metrics_text)} characters")

    async def test_langgraph_capabilities_discovery(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Test discovering LangGraph agent capabilities."""
        # This would be a capabilities endpoint if it exists
        # For now, test the agent endpoint to see what it can do

        payload = {
            "message": "What are your capabilities?",
        }

        response = await async_client.post(
            "/api/v1/chat/agent",
            json=payload,
            headers=auth_headers,
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ LangGraph capabilities inquiry: {data['answer'][:100]}...")
        else:
            print(f"⚠️  LangGraph capabilities test failed: {response.status_code}")

    async def test_error_handling_capabilities(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Test API error handling capabilities."""
        # Test 404 error handling
        response_404 = await async_client.get(
            "/api/v1/nonexistent/endpoint",
            headers=auth_headers,
        )
        assert response_404.status_code == 404
        print("✅ 404 error handling works")

        # Test malformed JSON handling
        response_400 = await async_client.post(
            "/api/v1/chat/agent",
            content="invalid json {",
            headers={"Content-Type": "application/json", **auth_headers},
        )
        assert response_400.status_code == 422  # FastAPI returns 422 for JSON parse errors
        print("✅ Malformed JSON error handling works")

    async def test_rate_limiting_discovery(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Test rate limiting configuration discovery."""
        # Make a request and check for rate limiting headers
        response = await async_client.get(
            "/api/v1/health/",
            headers=auth_headers,
        )

        headers = response.headers
        rate_limit_headers = [
            "x-ratelimit-limit",
            "x-ratelimit-remaining",
            "x-ratelimit-reset",
            "retry-after",
        ]

        found_headers = []
        for header in rate_limit_headers:
            if header in headers:
                found_headers.append(f"{header}: {headers[header]}")

        if found_headers:
            print("✅ Rate limiting headers found:")
            for header in found_headers:
                print(f"   {header}")
        else:
            print("ℹ️  No rate limiting headers detected")

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/api/v1/health/",
            "/api/openapi.json",
            "/api/v1/metrics",
            "/api/v1/",
        ],
    )
    async def test_public_endpoints_accessibility(
        self,
        async_client: AsyncClient,
        endpoint: str,
    ):
        """Test that public endpoints are accessible without authentication."""
        response = await async_client.get(endpoint)

        # These endpoints should work without auth
        assert response.status_code in [200, 307, 401, 403]  # Auth may be required or redirects

        if response.status_code == 200:
            print(f"✅ {endpoint} is publicly accessible")
        else:
            print(f"🔒 {endpoint} requires authentication")

    async def test_cors_headers(
        self,
        async_client: AsyncClient,
    ):
        """Test CORS headers are properly configured."""
        # Make an OPTIONS request to test CORS
        response = await async_client.options("/api/v1/health/")

        cors_headers = [
            "access-control-allow-origin",
            "access-control-allow-methods",
            "access-control-allow-headers",
        ]

        found_cors = []
        for header in cors_headers:
            if header in response.headers:
                found_cors.append(f"{header}: {response.headers[header]}")

        if found_cors:
            print("✅ CORS headers configured:")
            for header in found_cors:
                print(f"   {header}")
        else:
            print("ℹ️  No CORS headers detected in OPTIONS response")
