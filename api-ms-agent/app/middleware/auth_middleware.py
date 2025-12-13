"""Authentication middleware for FastAPI application."""

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from jose import jwt
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth.errors import AuthError, auth_error_payload
from app.auth.service import get_auth_service
from app.logger import get_logger
from app.observability.auth_metrics import get_auth_metrics

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
    # Metrics
    "/api/v1/auth/metrics",
}

# Route prefixes that don't require authentication
EXCLUDED_PREFIXES: tuple[str, ...] = ("/docs", "/redoc", "/health", "/api/health")


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware that validates JWT tokens for all routes except excluded ones."""

    def _get_request_id(self, request: Request) -> str:
        return (
            request.headers.get("X-Request-ID")
            or request.headers.get("X-Correlation-ID")
            or request.headers.get("traceparent")
            or uuid.uuid4().hex
        )

    def _get_unverified_claims(self, token: str) -> dict:
        try:
            return dict(jwt.get_unverified_claims(token))
        except Exception:
            return {}

    def _extract_observability_fields(self, claims: dict) -> tuple[str | None, str | None]:
        # Best-effort extraction; fields may not exist for all providers.
        tenant_id = claims.get("tid") or claims.get("tenant") or claims.get("tenant_id")
        app_id = claims.get("appid") or claims.get("azp") or claims.get("client_id")
        return (str(tenant_id) if tenant_id else None, str(app_id) if app_id else None)

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
        request_id = self._get_request_id(request)
        request.state.request_id = request_id
        metrics = get_auth_metrics()

        # Skip authentication for excluded routes
        if self._is_excluded_route(path):
            logger.debug("auth_skipped", path=path, reason="excluded_route")
            return await call_next(request)

        # Extract bearer token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning(
                "auth_failed",
                request_id=request_id,
                path=path,
                reason="missing_authorization_header",
            )
            metrics.inc_auth_failure(
                reason="missing_authorization_header",
                code="auth.missing_authorization_header",
            )
            return self._unauthorized(
                detail="Missing Authorization header",
                code="auth.missing_authorization_header",
            )

        # Validate bearer token format
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.warning(
                "auth_failed",
                request_id=request_id,
                path=path,
                reason="invalid_authorization_format",
            )
            metrics.inc_auth_failure(
                reason="invalid_authorization_format",
                code="auth.invalid_authorization_format",
            )
            return self._unauthorized(
                detail="Invalid Authorization header format. Expected: Bearer <token>",
                code="auth.invalid_authorization_format",
            )

        token = parts[1]
        unverified_claims = self._get_unverified_claims(token)
        tenant_id, app_id = self._extract_observability_fields(unverified_claims)

        # Validate token using auth service
        try:
            start = time.perf_counter()
            auth_service = get_auth_service()
            user = await auth_service.validate_token(token)
            duration_ms = (time.perf_counter() - start) * 1000
            provider = getattr(user, "provider", None) or "unknown"
            metrics.inc_auth_success(provider=str(provider))
            metrics.observe_validation_duration_ms(provider=str(provider), duration_ms=duration_ms)

            # Store user in request state for use in route handlers
            request.state.current_user = user
            logger.info(
                "auth_success",
                request_id=request_id,
                path=path,
                provider=provider,
                token_issuer=getattr(user, "iss", None),
                tenant_id=tenant_id,
                app_id=app_id,
                subject=getattr(user, "sub", None),
                username=getattr(user, "preferred_username", None),
                roles_count=len(getattr(user, "roles", None) or []),
                validation_duration_ms=round(duration_ms, 2),
            )

        except AuthError as exc:
            metrics.inc_auth_failure(reason="token_validation_failed", code=exc.code)
            logger.warning(
                "auth_failed",
                request_id=request_id,
                path=path,
                reason="token_validation_failed",
                code=exc.code,
                error=str(exc.detail),
                token_issuer=str(unverified_claims.get("iss") or "") or None,
                tenant_id=tenant_id,
                app_id=app_id,
            )
            headers = exc.headers or {"WWW-Authenticate": "Bearer"}
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.to_payload(),
                headers=headers,
            )

        except Exception as exc:
            # Log the error but return generic 401 to avoid leaking info
            metrics.inc_auth_failure(
                reason="token_validation_failed",
                code="auth.invalid_or_expired",
            )
            logger.warning(
                "auth_failed",
                request_id=request_id,
                path=path,
                reason="token_validation_failed",
                code="auth.invalid_or_expired",
                error_type=type(exc).__name__,
                token_issuer=str(unverified_claims.get("iss") or "") or None,
                tenant_id=tenant_id,
                app_id=app_id,
            )
            return self._unauthorized(
                detail="Invalid or expired token",
                code="auth.invalid_or_expired",
            )

        return await call_next(request)
