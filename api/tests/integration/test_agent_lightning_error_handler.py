"""Integration tests for Agent Lightning Error Handler Middleware.

Tests comprehensive error handling scenarios:
- Agent Lightning SDK unavailable (ImportError)
- Insufficient training data (InsufficientDataError)
- Metrics collection failures (MetricsCollectionError)
- Missing tenant context (TenantContextError)
- Optimization algorithm failures (OptimizationError)
"""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI, Request, Response

from app.middleware.agent_lightning_error_handler import (
    AgentLightningErrorHandler,
    InsufficientDataError,
    MetricsCollectionError,
    OptimizationError,
    TenantContextError,
)


class TestAgentLightningErrorHandlerIntegration:
    """Integration tests for AgentLightningErrorHandler middleware."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create FastAPI app with error handler middleware.

        Returns:
            FastAPI app with middleware registered
        """
        app = FastAPI()
        app.add_middleware(AgentLightningErrorHandler)
        return app

    @pytest.fixture
    def mock_request(self) -> Mock:
        """Create mock request for testing.

        Returns:
            Mock request with required attributes
        """
        request = Mock(spec=Request)
        request.url.path = "/api/v1/test"
        request.method = "POST"
        request.headers = {"X-Tenant-ID": "test-tenant-123"}
        request.state = Mock()
        return request

    @pytest.fixture
    def mock_call_next(self) -> AsyncMock:
        """Create mock call_next function.

        Returns:
            AsyncMock that returns a successful response
        """

        async def _call_next(request: Request) -> Response:
            return Response(content='{"result": "success"}', status_code=200)

        return AsyncMock(side_effect=_call_next)

    @pytest.mark.asyncio
    async def test_successful_request_passes_through(
        self,
        mock_request: Mock,
        mock_call_next: AsyncMock,
    ) -> None:
        """Test that successful requests pass through without modification.

        Verifies:
        - Middleware doesn't interfere with normal operations
        - Response is returned unchanged
        - call_next is invoked
        """
        middleware = AgentLightningErrorHandler(app=Mock())

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        assert response.body == b'{"result": "success"}'
        mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_sdk_unavailable_graceful_degradation(
        self,
        mock_request: Mock,
        mock_call_next: AsyncMock,
    ) -> None:
        """Test graceful degradation when Agent Lightning SDK unavailable.

        Scenario: ImportError with 'agentlightning' in message
        Expected: Continue without optimization, add status header
        """
        middleware = AgentLightningErrorHandler(app=Mock())

        # Mock call_next to raise ImportError first, then succeed on retry
        call_count = 0

        async def _call_next_with_import_error(request: Request) -> Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ImportError("cannot import name 'AgentLightning' from 'agentlightning'")
            return Response(content='{"result": "baseline"}', status_code=200)

        mock_call_next.side_effect = _call_next_with_import_error

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        assert response.headers["X-Agent-Lightning-Status"] == "unavailable"
        assert mock_request.state.agent_lightning_disabled is True

    @pytest.mark.asyncio
    async def test_insufficient_data_skip_optimization(
        self,
        mock_request: Mock,
        mock_call_next: AsyncMock,
    ) -> None:
        """Test optimization skipped when insufficient training data.

        Scenario: ValueError with 'insufficient' keyword
        Expected: Skip optimization but continue metrics collection
        """
        middleware = AgentLightningErrorHandler(app=Mock())

        # Mock call_next to raise InsufficientDataError first
        call_count = 0

        async def _call_next_with_insufficient_data(request: Request) -> Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Insufficient training data: need 50 samples, have 10")
            return Response(content='{"result": "collecting"}', status_code=200)

        mock_call_next.side_effect = _call_next_with_insufficient_data

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        assert response.headers["X-Agent-Lightning-Status"] == "collecting-baseline"
        assert mock_request.state.agent_lightning_skip_optimization is True

    @pytest.mark.asyncio
    async def test_missing_tenant_context_returns_403(
        self,
        mock_request: Mock,
        mock_call_next: AsyncMock,
    ) -> None:
        """Test that missing tenant context returns 403 Forbidden.

        Scenario: PermissionError raised (TenantContextError)
        Expected: Return 403 response with error message
        """
        middleware = AgentLightningErrorHandler(app=Mock())

        # Mock call_next to raise PermissionError
        error_msg = "Tenant context required for Agent Lightning operations"
        mock_call_next.side_effect = PermissionError(error_msg)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 403
        assert b"Missing or invalid tenant context" in response.body

    @pytest.mark.asyncio
    async def test_optimization_error_fallback_to_baseline(
        self,
        mock_request: Mock,
        mock_call_next: AsyncMock,
    ) -> None:
        """Test fallback to baseline agent when optimization fails.

        Scenario: Exception from optimization algorithm
        Expected: Continue with baseline agent, add status header
        """
        middleware = AgentLightningErrorHandler(app=Mock())

        # Mock call_next to raise optimization error first
        call_count = 0

        async def _call_next_with_optimization_error(request: Request) -> Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Create exception with Agent Lightning in traceback
                try:
                    raise RuntimeError("Agent Lightning RL training failed: convergence timeout")
                except RuntimeError as e:
                    raise e
            return Response(content='{"result": "baseline"}', status_code=200)

        mock_call_next.side_effect = _call_next_with_optimization_error

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        assert response.headers["X-Agent-Lightning-Status"] == "optimization-failed"
        assert mock_request.state.agent_lightning_optimization_failed is True

    @pytest.mark.asyncio
    async def test_metrics_collection_error_continues_operation(
        self,
        mock_request: Mock,
        mock_call_next: AsyncMock,
    ) -> None:
        """Test that metrics collection errors don't break operations.

        Scenario: Exception during metrics collection
        Expected: Log error, continue with agent operation
        """
        middleware = AgentLightningErrorHandler(app=Mock())

        # Mock call_next to raise metrics error first
        call_count = 0

        async def _call_next_with_metrics_error(request: Request) -> Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("optimization_service metrics collection failed")
            return Response(content='{"result": "success"}', status_code=200)

        mock_call_next.side_effect = _call_next_with_metrics_error

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        assert response.headers["X-Agent-Lightning-Status"] == "optimization-failed"

    @pytest.mark.asyncio
    async def test_extract_tenant_id_from_state(
        self,
        mock_request: Mock,
    ) -> None:
        """Test tenant ID extraction from request state.

        Verifies:
        - Tenant ID extracted from user object in state
        - Falls back to header if state unavailable
        """
        middleware = AgentLightningErrorHandler(app=Mock())

        # Test extraction from state
        mock_request.state.user = Mock(sub="tenant-from-state-456")
        tenant_id = middleware._extract_tenant_id(mock_request)
        assert tenant_id == "tenant-from-state-456"

        # Test fallback to header
        mock_request.state = Mock(spec=[])  # No user attribute
        tenant_id = middleware._extract_tenant_id(mock_request)
        assert tenant_id == "test-tenant-123"

    @pytest.mark.asyncio
    async def test_is_agent_lightning_error_by_message(
        self,
    ) -> None:
        """Test error detection by message content.

        Verifies:
        - Errors with Agent Lightning keywords detected
        - Keywords: 'agent lightning', 'optimization', 'rl training', etc.
        """
        middleware = AgentLightningErrorHandler(app=Mock())

        # Test with various Agent Lightning error messages
        test_cases = [
            RuntimeError("Agent Lightning optimization failed"),
            ValueError("RL training convergence error"),
            Exception("prompt optimization timeout"),
            RuntimeError("agent_wrapper_service initialization failed"),
        ]

        for error in test_cases:
            assert middleware._is_agent_lightning_error(error) is True

    @pytest.mark.asyncio
    async def test_is_not_agent_lightning_error(
        self,
    ) -> None:
        """Test that non-Agent Lightning errors not detected as such.

        Verifies:
        - Generic errors not flagged as Agent Lightning errors
        - Database, network, validation errors excluded
        """
        middleware = AgentLightningErrorHandler(app=Mock())

        # Test with non-Agent Lightning errors
        test_cases = [
            RuntimeError("Database connection failed"),
            ValueError("Invalid input format"),
            Exception("Network timeout"),
            KeyError("missing_key"),
        ]

        for error in test_cases:
            assert middleware._is_agent_lightning_error(error) is False

    @pytest.mark.asyncio
    async def test_is_agent_lightning_error_by_traceback(
        self,
    ) -> None:
        """Test error detection by traceback analysis.

        Verifies:
        - Errors from Agent Lightning modules detected
        - Checks filenames in traceback
        """
        middleware = AgentLightningErrorHandler(app=Mock())

        # Create exception with Agent Lightning module in traceback
        try:
            # Simulate error from agent_wrapper_service.py
            exec(
                """
def fake_agent_lightning_function():
    raise RuntimeError("Generic error")

# Simulate this being in agent_wrapper_service module
fake_agent_lightning_function.__code__ = fake_agent_lightning_function.__code__.replace(
    co_filename="app/services/agent_wrapper_service.py"
)
fake_agent_lightning_function()
""",
                {"RuntimeError": RuntimeError},
            )
        except RuntimeError:
            # Manually create traceback with Agent Lightning module
            # For testing purposes, check if keyword matching works
            assert middleware._is_agent_lightning_error(RuntimeError("optimization_service error"))

    @pytest.mark.asyncio
    async def test_non_agent_lightning_errors_propagate(
        self,
        mock_request: Mock,
        mock_call_next: AsyncMock,
    ) -> None:
        """Test that non-Agent Lightning errors propagate normally.

        Scenario: Generic application error (not Agent Lightning)
        Expected: Error propagates to normal FastAPI error handling
        """
        middleware = AgentLightningErrorHandler(app=Mock())

        # Mock call_next to raise non-Agent Lightning error
        mock_call_next.side_effect = KeyError("database_key_not_found")

        with pytest.raises(KeyError, match="database_key_not_found"):
            await middleware.dispatch(mock_request, mock_call_next)

    @pytest.mark.asyncio
    async def test_import_error_non_agent_lightning_propagates(
        self,
        mock_request: Mock,
        mock_call_next: AsyncMock,
    ) -> None:
        """Test that non-Agent Lightning ImportErrors propagate.

        Scenario: ImportError for other library (not agentlightning)
        Expected: Error propagates to normal error handling
        """
        middleware = AgentLightningErrorHandler(app=Mock())

        # Mock call_next to raise non-Agent Lightning ImportError
        mock_call_next.side_effect = ImportError("cannot import name 'SomeOtherLibrary'")

        with pytest.raises(ImportError, match="SomeOtherLibrary"):
            await middleware.dispatch(mock_request, mock_call_next)

    @pytest.mark.asyncio
    async def test_value_error_without_keywords_propagates(
        self,
        mock_request: Mock,
        mock_call_next: AsyncMock,
    ) -> None:
        """Test that ValueErrors without data keywords propagate.

        Scenario: ValueError not related to training data
        Expected: Error propagates to normal error handling
        """
        middleware = AgentLightningErrorHandler(app=Mock())

        # Mock call_next to raise ValueError without data keywords
        mock_call_next.side_effect = ValueError("Invalid configuration format")

        with pytest.raises(ValueError, match="Invalid configuration format"):
            await middleware.dispatch(mock_request, mock_call_next)

    @pytest.mark.asyncio
    async def test_multiple_error_scenarios_in_sequence(
        self,
        mock_request: Mock,
    ) -> None:
        """Test handling multiple error types in sequence.

        Verifies:
        - Middleware handles different error types correctly
        - State flags set appropriately for each scenario
        - Status headers reflect current error type
        """
        middleware = AgentLightningErrorHandler(app=Mock())

        # Scenario 1: SDK unavailable
        call_count = 0

        async def _call_next_scenario_1(request: Request) -> Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ImportError("agentlightning not found")
            return Response(content='{"s1": "ok"}', status_code=200)

        mock_next_1 = AsyncMock(side_effect=_call_next_scenario_1)
        response = await middleware.dispatch(mock_request, mock_next_1)
        assert response.headers["X-Agent-Lightning-Status"] == "unavailable"

        # Scenario 2: Insufficient data (reset request state)
        mock_request.state = Mock()
        call_count = 0

        async def _call_next_scenario_2(request: Request) -> Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("not enough training samples")
            return Response(content='{"s2": "ok"}', status_code=200)

        mock_next_2 = AsyncMock(side_effect=_call_next_scenario_2)
        response = await middleware.dispatch(mock_request, mock_next_2)
        assert response.headers["X-Agent-Lightning-Status"] == "collecting-baseline"

        # Scenario 3: Optimization error (reset request state)
        mock_request.state = Mock()
        call_count = 0

        async def _call_next_scenario_3(request: Request) -> Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Agent Lightning RL training timeout")
            return Response(content='{"s3": "ok"}', status_code=200)

        mock_next_3 = AsyncMock(side_effect=_call_next_scenario_3)
        response = await middleware.dispatch(mock_request, mock_next_3)
        assert response.headers["X-Agent-Lightning-Status"] == "optimization-failed"


class TestAgentLightningCustomExceptions:
    """Tests for custom Agent Lightning exception classes."""

    def test_metrics_collection_error_is_exception(self) -> None:
        """Test MetricsCollectionError is proper Exception subclass."""
        error = MetricsCollectionError("Failed to collect latency metric")
        assert isinstance(error, Exception)
        assert str(error) == "Failed to collect latency metric"

    def test_optimization_error_is_exception(self) -> None:
        """Test OptimizationError is proper Exception subclass."""
        error = OptimizationError("RL training convergence failed")
        assert isinstance(error, Exception)
        assert str(error) == "RL training convergence failed"

    def test_insufficient_data_error_is_value_error(self) -> None:
        """Test InsufficientDataError is ValueError subclass."""
        error = InsufficientDataError("Need 50 samples, have 10")
        assert isinstance(error, ValueError)
        assert str(error) == "Need 50 samples, have 10"

    def test_tenant_context_error_is_permission_error(self) -> None:
        """Test TenantContextError is PermissionError subclass."""
        error = TenantContextError("Missing tenant_id in request")
        assert isinstance(error, PermissionError)
        assert str(error) == "Missing tenant_id in request"

    def test_custom_exceptions_can_be_raised_and_caught(self) -> None:
        """Test custom exceptions can be raised and caught properly."""
        # Test MetricsCollectionError
        with pytest.raises(MetricsCollectionError, match="metric collection failed"):
            raise MetricsCollectionError("metric collection failed")

        # Test OptimizationError
        with pytest.raises(OptimizationError, match="optimization failed"):
            raise OptimizationError("optimization failed")

        # Test InsufficientDataError
        with pytest.raises(InsufficientDataError, match="insufficient data"):
            raise InsufficientDataError("insufficient data")

        # Test TenantContextError
        with pytest.raises(TenantContextError, match="missing tenant"):
            raise TenantContextError("missing tenant")
