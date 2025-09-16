"""FastAPI dependencies for authentication and authorization."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.models import KeycloakUser
from app.auth.service import auth_service

# Security scheme for bearer token
security = HTTPBearer()


async def get_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> str:
    """Extract bearer token from Authorization header."""
    return credentials.credentials


async def get_current_user(token: Annotated[str, Depends(get_token)]) -> KeycloakUser:
    """Get current authenticated user from JWT token."""
    return await auth_service.validate_token(token)


def require_roles(*required_roles: str):
    """Create a dependency that requires specific roles."""

    async def check_roles(
        current_user: Annotated[KeycloakUser, Depends(get_current_user)],
    ) -> KeycloakUser:
        """Check if user has required roles."""
        if not current_user.client_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="User roles not found"
            )

        if required_roles:
            has_role = any(auth_service.has_role(current_user, role) for role in required_roles)

            if not has_role:
                detail_msg = f"Access denied. Required roles: {', '.join(required_roles)}"
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=detail_msg,
                )

        return current_user

    return check_roles


# Common role dependencies
RequireAuth = Depends(get_current_user)
RequireParticipant = Depends(require_roles("ai-poc-participant"))
