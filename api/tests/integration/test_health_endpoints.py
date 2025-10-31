"""Integration tests for health check endpoints."""

from httpx import AsyncClient


class TestHealthEndpoints:
    """Integration tests for application health check endpoints."""

    async def test_basic_health_check(
        self,
        async_client: AsyncClient,
    ):
        """Test basic health check endpoint."""
        response = await async_client.get("/api/v1/health/")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["up", "healthy"]
        assert "timestamp" in data
        assert "service" in data

        print(f"✅ Basic health check: {data['status']}")

    async def test_readiness_check(
        self,
        async_client: AsyncClient,
    ):
        """Test readiness check endpoint."""
        response = await async_client.get("/api/v1/health/ready")

        # Readiness can be 200 (ready) or 503 (not ready)
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data
        assert "timestamp" in data

        if response.status_code == 200:
            assert data["status"] in ["up", "healthy"]
            if "checks" in data:
                assert "cosmosdb" in data["checks"]
                print(f"✅ Readiness check passed: {data['checks']}")
        else:
            assert data["status"] in ["down", "unhealthy", "degraded"]
            print(f"⚠️  Readiness check failed: {data['status']}")

    async def test_liveness_check(
        self,
        async_client: AsyncClient,
    ):
        """Test liveness check endpoint."""
        response = await async_client.get("/api/v1/health/live")

        # Liveness should always be 200 if app is running
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["up", "healthy", "alive"]

        print(f"✅ Liveness check: {data['status']}")

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

    async def test_health_check_response_structure(
        self,
        async_client: AsyncClient,
    ):
        """Test health check response has expected structure."""
        response = await async_client.get("/api/v1/health/")

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "status" in data
        assert "timestamp" in data

        # Validate timestamp format (ISO 8601)
        assert "T" in data["timestamp"]
        assert "Z" in data["timestamp"] or "+" in data["timestamp"]

        print("✅ Health check response structure valid")

    async def test_readiness_check_details(
        self,
        async_client: AsyncClient,
    ):
        """Test readiness check includes service details."""
        response = await async_client.get("/api/v1/health/ready")

        data = response.json()

        # If readiness check passes, it should include checks
        if response.status_code == 200 and "checks" in data:
            checks = data["checks"]
            assert isinstance(checks, dict)

            # Check for expected service checks
            if "cosmosdb" in checks:
                cosmosdb_check = checks["cosmosdb"]
                assert "status" in cosmosdb_check
                print(f"✅ CosmosDB check: {cosmosdb_check['status']}")

            if "multi_tenant" in checks:
                mt_check = checks["multi_tenant"]
                assert "status" in mt_check
                print(f"✅ Multi-tenant check: {mt_check['status']}")

    async def test_health_endpoints_accessibility(
        self,
        async_client: AsyncClient,
    ):
        """Test that health endpoints are publicly accessible."""
        endpoints = [
            "/api/v1/health/",
            "/api/v1/health/ready",
            "/api/v1/health/live",
        ]

        for endpoint in endpoints:
            response = await async_client.get(endpoint)

            # Health endpoints should not require authentication
            assert response.status_code not in [401, 403], (
                f"Health endpoint {endpoint} should be publicly accessible"
            )

        print("✅ All health endpoints are publicly accessible")
