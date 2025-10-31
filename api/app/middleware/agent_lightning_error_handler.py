"""Agent Lightning Error Handler Middleware.

This middleware provides comprehensive error handling for Agent Lightning operations,
ensuring graceful degradation when optimization services are unavailable or encounter
issues.
"""

import traceback
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logger import get_logger

logger = get_logger(__name__)


class AgentLightningErrorHandler(BaseHTTPMiddleware):
    """Middleware for handling Agent Lightning-specific errors.

    Provides graceful error handling for:
    - Agent Lightning SDK unavailable
    - Insufficient training data for optimization
    - Metrics collection failures
    - Missing or invalid tenant context
    - Optimization algorithm failures

    Ensures that Agent Lightning errors don't break the main application
    and that agents continue working even when optimization is unavailable.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and handle Agent Lightning errors.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain

        Returns:
            Response: HTTP response (possibly modified if error occurred)
        """
        try:
            response = await call_next(request)
            return response

        except ImportError as e:
            # Agent Lightning SDK not available
            if "agentlightning" in str(e).lower():
                logger.warning(
                    "Agent Lightning SDK not available - continuing without optimization",
                    extra={
                        "error": str(e),
                        "path": request.url.path,
                        "method": request.method,
                    },
                )
                # Continue without Agent Lightning (graceful degradation)
                return await self._handle_sdk_unavailable(request, call_next)
            raise

        except ValueError as e:
            # Insufficient training data or invalid configuration
            if any(
                keyword in str(e).lower()
                for keyword in ["insufficient", "not enough", "minimum", "required"]
            ):
                logger.info(
                    f"Insufficient data for Agent Lightning optimization: {e}",
                    extra={
                        "error": str(e),
                        "path": request.url.path,
                        "tenant_id": self._extract_tenant_id(request),
                    },
                )
                # Skip optimization, continue with baseline agent
                return await self._handle_insufficient_data(request, call_next)
            raise

        except PermissionError as e:
            # Missing or invalid tenant context
            logger.error(
                f"Agent Lightning tenant context error: {e}",
                extra={
                    "error": str(e),
                    "path": request.url.path,
                    "method": request.method,
                },
            )
            # Return 403 Forbidden for missing tenant context
            return Response(
                content='{"detail": "Missing or invalid tenant context"}',
                status_code=403,
                media_type="application/json",
            )

        except Exception as e:
            # Catch-all for unexpected Agent Lightning errors
            if self._is_agent_lightning_error(e):
                logger.error(
                    f"Agent Lightning error - continuing with baseline agent: {e}",
                    extra={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "traceback": traceback.format_exc(),
                        "path": request.url.path,
                        "tenant_id": self._extract_tenant_id(request),
                    },
                )
                # Continue without Agent Lightning
                return await self._handle_optimization_error(request, call_next)
            # Re-raise non-Agent Lightning errors
            raise

    async def _handle_sdk_unavailable(self, request: Request, call_next: Callable) -> Response:
        """Handle case where Agent Lightning SDK is unavailable.

        Args:
            request: HTTP request
            call_next: Next handler

        Returns:
            Response: Response from baseline agent (without optimization)
        """
        # Set flag in request state to skip Agent Lightning wrapping
        request.state.agent_lightning_disabled = True

        try:
            response = await call_next(request)
            # Add header indicating optimization was skipped
            response.headers["X-Agent-Lightning-Status"] = "unavailable"
            return response
        except Exception:
            # If fallback also fails, let normal error handling take over
            raise

    async def _handle_insufficient_data(self, request: Request, call_next: Callable) -> Response:
        """Handle case where insufficient training data exists.

        Args:
            request: HTTP request
            call_next: Next handler

        Returns:
            Response: Response from baseline agent (optimization skipped)
        """
        # Set flag to skip optimization but continue metrics collection
        request.state.agent_lightning_skip_optimization = True

        response = await call_next(request)
        response.headers["X-Agent-Lightning-Status"] = "collecting-baseline"
        return response

    async def _handle_optimization_error(self, request: Request, call_next: Callable) -> Response:
        """Handle optimization algorithm failure.

        Args:
            request: HTTP request
            call_next: Next handler

        Returns:
            Response: Response from baseline agent (optimization failed)
        """
        # Set flag to use baseline agent
        request.state.agent_lightning_optimization_failed = True

        response = await call_next(request)
        response.headers["X-Agent-Lightning-Status"] = "optimization-failed"
        return response

    def _extract_tenant_id(self, request: Request) -> str | None:
        """Extract tenant ID from request for logging.

        Args:
            request: HTTP request

        Returns:
            Tenant ID if available, None otherwise
        """
        # Try to get tenant_id from request state (set by auth middleware)
        if hasattr(request.state, "user"):
            user = getattr(request.state, "user", None)
            if user and hasattr(user, "sub"):
                return user.sub

        # Try to get from headers
        return request.headers.get("X-Tenant-ID")

    def _is_agent_lightning_error(self, exception: Exception) -> bool:
        """Determine if exception is Agent Lightning-related.

        Args:
            exception: Exception that occurred

        Returns:
            True if exception is from Agent Lightning operations
        """
        # Check if exception message contains Agent Lightning keywords
        error_str = str(exception).lower()
        agent_lightning_keywords = [
            "agent lightning",
            "agentlightning",
            "optimization",
            "rl training",
            "prompt optimization",
            "fine-tuning",
            "agent_wrapper",
            "optimization_service",
        ]

        if any(keyword in error_str for keyword in agent_lightning_keywords):
            return True

        # Check if exception originated from Agent Lightning modules
        tb = traceback.extract_tb(exception.__traceback__)
        agent_lightning_modules = [
            "agent_lightning",
            "agent_wrapper_service",
            "optimization_service",
            "rl_optimization_strategy",
            "prompt_optimization_strategy",
            "sft_optimization_strategy",
        ]

        for frame in tb:
            if any(module in frame.filename for module in agent_lightning_modules):
                return True

        return False


class MetricsCollectionError(Exception):
    """Exception raised when metrics collection fails.

    This is a non-fatal error - the agent should continue working
    even if metrics collection fails.
    """

    pass


class OptimizationError(Exception):
    """Exception raised when optimization algorithm fails.

    This is a non-fatal error - the agent should fall back to baseline
    performance when optimization fails.
    """

    pass


class InsufficientDataError(ValueError):
    """Exception raised when insufficient training data exists.

    Raised when:
    - Less than minimum required samples collected
    - Data quality too low for training
    - Missing required metric fields
    """

    pass


class TenantContextError(PermissionError):
    """Exception raised when tenant context is missing or invalid.

    This is a fatal error - requests must have valid tenant context
    for multi-tenant isolation.
    """

    pass
