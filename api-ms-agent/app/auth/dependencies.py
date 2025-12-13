"""FastAPI dependencies for authentication and authorization."""

import time
from typing import Annotated

from fastapi import Depends, Request, status

from app.auth.errors import AuthError
from app.auth.models import AuthenticatedUser
from app.auth.service import get_auth_service
from app.logger import get_logger
from app.observability.auth_metrics import get_auth_metrics

logger = get_logger(__name__)


async def get_current_user_from_request(request: Request) -> AuthenticatedUser:
    """Get current user from request state (set by AuthMiddleware).

    Use this dependency when AuthMiddleware is enabled to avoid re-validating the token.

        Fallback behavior:
        - In the normal application runtime, `AuthMiddleware` should set
            `request.state.current_user`.
        - If middleware is bypassed (e.g., certain unit tests or alternate app wiring),
            this dependency will parse and validate the bearer token exactly once.
    """
    # Try to get user from request state (set by AuthMiddleware)
    if hasattr(request.state, "current_user"):
        return request.state.current_user

    logger.debug(
        "auth_user_missing_from_request_state_falling_back_to_header_validation",
        path=str(getattr(request, "url", "")),
    )

    # Fallback: validate token directly (for cases where middleware is bypassed)
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise AuthError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            code="auth.missing_authorization_header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
            code="auth.invalid_authorization_format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = get_auth_service()
    return await auth_service.validate_token(parts[1])


def require_roles(*required_roles: str):
    """Dependency factory enforcing that user has at least one of the given roles.

    Usage: Depends(require_roles("roleA", "roleB"))
    """
    if not required_roles:
        raise ValueError("require_roles() requires at least one role")

    roles = tuple(required_roles)

    async def checker(
        current_user: Annotated[AuthenticatedUser, Depends(get_current_user_from_request)],
    ) -> AuthenticatedUser:
        start = time.perf_counter()
        user_roles = current_user.roles or []
        if not user_roles or not any(r in user_roles for r in roles):
            # Authorization denial (token is valid but required role missing)
            metrics = get_auth_metrics()
            required_roles_label = "|".join(sorted(roles))
            provider = getattr(current_user, "provider", None) or "unknown"

            metrics.inc_role_denied(role=required_roles_label)
            metrics.observe_authorization_duration_ms(
                provider=str(provider),
                outcome="denied",
                duration_ms=(time.perf_counter() - start) * 1000,
            )

            logger.warning(
                "auth_role_denied",
                provider=provider,
                subject=getattr(current_user, "sub", None),
                token_issuer=getattr(current_user, "iss", None),
                required_roles=list(roles),
                user_roles=user_roles,
            )
            raise AuthError(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(roles)}",
                code="auth.missing_role",
            )

        # Allowed
        metrics = get_auth_metrics()
        provider = getattr(current_user, "provider", None) or "unknown"
        metrics.observe_authorization_duration_ms(
            provider=str(provider),
            outcome="allowed",
            duration_ms=(time.perf_counter() - start) * 1000,
        )
        return current_user

    return checker


def require_role(role: str):
    """Dependency factory enforcing a single required role.

    Usage: Depends(require_role("ai-poc-participant"))
    """

    if not role:
        raise ValueError("require_role() requires a non-empty role")

    return require_roles(role)
