"""Authentication middleware for FastAPI application."""

from collections.abc import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth.errors import AuthError, auth_error_payload
from app.auth.service import get_auth_service
from app.logger import get_logger

logger = get_logger(__name__)

# Routes that don't require authentication
EXCLUDED_ROUTES: set[str] = {
    # Health checks
    "/health",
    "/api/health",
    "/api/v1/health",
    "/api/v1/chat/health",
    "/api/v1/research/health",
    "/api/v1/workflow-research/health",
    # Documentation
    "/docs",
    "/redoc",
    "/openapi.json",
    # Root
    "/",
    "/api/v1",
}

# Route prefixes that don't require authentication
EXCLUDED_PREFIXES: tuple[str, ...] = ("/docs", "/redoc", "/health", "/api/health")


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware that validates JWT tokens for all routes except excluded ones."""

    def _unauthorized(self, *, detail: str, code: str) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=auth_error_payload(detail=detail, code=code),
            headers={"WWW-Authenticate": "Bearer"},
        )

    def _is_excluded_route(self, path: str) -> bool:
        """Check if the request path should skip authentication."""
        # Check exact matches
        if path in EXCLUDED_ROUTES:
            return True

        # Check prefixes (for nested doc routes like /docs/oauth2-redirect)
        if path.startswith(EXCLUDED_PREFIXES):
            return True

        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check authentication for non-excluded routes."""
        path = request.url.path

        # Skip authentication for excluded routes
        if self._is_excluded_route(path):
            logger.debug("auth_skipped", path=path, reason="excluded_route")
            return await call_next(request)

        # Extract bearer token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning("auth_failed", path=path, reason="missing_authorization_header")
            return self._unauthorized(
                detail="Missing Authorization header",
                code="auth.missing_authorization_header",
            )

        # Validate bearer token format
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.warning("auth_failed", path=path, reason="invalid_authorization_format")
            return self._unauthorized(
                detail="Invalid Authorization header format. Expected: Bearer <token>",
                code="auth.invalid_authorization_format",
            )

        token = parts[1]

        # Validate token using auth service
        try:
            auth_service = get_auth_service()
            user = await auth_service.validate_token(token)

            # Store user in request state for use in route handlers
            request.state.current_user = user
            logger.debug(
                "auth_success",
                path=path,
                provider=getattr(user, "provider", None),
                subject=getattr(user, "sub", None),
                username=getattr(user, "preferred_username", None),
            )

        except AuthError as exc:
            logger.warning(
                "auth_failed",
                path=path,
                reason="token_validation_failed",
                code=exc.code,
                error=str(exc.detail),
            )
            headers = exc.headers or {"WWW-Authenticate": "Bearer"}
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.to_payload(),
                headers=headers,
            )

        except Exception as exc:
            # Log the error but return generic 401 to avoid leaking info
            logger.warning(
                "auth_failed",
                path=path,
                reason="token_validation_failed",
                code="auth.invalid_or_expired",
                error=str(exc),
            )
            return self._unauthorized(
                detail="Invalid or expired token",
                code="auth.invalid_or_expired",
            )

        return await call_next(request)
