"""FastAPI dependencies for authentication and authorization."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.models import KeycloakUser
from app.auth.service import get_auth_service
from app.core.logger import get_logger

logger = get_logger(__name__)

# Security scheme for bearer token
security = HTTPBearer()


async def get_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> str:
    """Extract bearer token from Authorization header."""
    return credentials.credentials


async def get_current_user(token: Annotated[str, Depends(get_token)]) -> KeycloakUser:
    """Get current authenticated user from JWT token."""
    auth_service = get_auth_service()
    return await auth_service.validate_token(token)


def require_roles(*required_roles: str):
    """Dependency factory enforcing that user has at least one of the given roles.

    Usage: Depends(require_roles("roleA", "roleB"))
    """
    if not required_roles:
        raise ValueError("require_roles() requires at least one role")

    roles = tuple(required_roles)

    async def checker(
        current_user: Annotated[KeycloakUser, Depends(get_current_user)],
    ) -> KeycloakUser:
        user_roles = current_user.client_roles or []
        if not user_roles or not any(r in user_roles for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(roles)}",
            )
        return current_user

    return checker


# Common role dependencies
RequireAuth = Depends(get_current_user)
RequireParticipant = Depends(require_roles("ai-poc-participant"))
