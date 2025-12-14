"""FastAPI dependencies for authentication and authorization."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.models import KeycloakUser
from app.auth.service import get_auth_service
from app.logger import get_logger

logger = get_logger(__name__)

# Security scheme for bearer token
# MAJOR: Use auto_error=False to avoid fastapi's automatic 403/401 behavior and
# allow consistent, explicit 401 responses matching middleware semantics.
security = HTTPBearer(auto_error=False)


async def get_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> str:
    """Extract bearer token from Authorization header.

    Returns a bearer token string or raises explicit 401 if missing/invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


async def get_current_user(token: Annotated[str, Depends(get_token)]) -> KeycloakUser:
    """Get current authenticated user from JWT token."""
    auth_service = get_auth_service()
    return await auth_service.validate_token(token)


async def get_current_user_from_request(request: Request) -> KeycloakUser:
    """Get current user from request state (set by AuthMiddleware).

    Use this dependency when AuthMiddleware is enabled to avoid re-validating the token.
    Falls back to token validation if user not in request state.
    """
    # Try to get user from request state (set by AuthMiddleware)
    if hasattr(request.state, "current_user"):
        return request.state.current_user

    # Fallback: validate token directly (for cases where middleware is bypassed)
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
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
        request: Request,
    ) -> KeycloakUser:
        # Prefer middleware-populated user to avoid re-validating the token.
        current_user = await get_current_user_from_request(request)

        user_roles = current_user.client_roles or []
        if not user_roles or not any(r in user_roles for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(roles)}",
            )
        return current_user

    return checker


# Common role dependencies
# Prefer middleware-populated user to avoid redundant token validation.
RequireAuth = Depends(get_current_user_from_request)
RequireParticipant = Depends(require_roles("ai-poc-participant"))
