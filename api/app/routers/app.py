"""Basic application router."""

from typing import Annotated

from fastapi import APIRouter

from app.auth.dependencies import RequireAuth
from app.auth.models import KeycloakUser

router = APIRouter(tags=["app"])


@router.get(
    "/",
    summary="Get welcome message",
    description="Returns a welcome message for authenticated users",
    response_description="Welcome message",
    responses={
        200: {
            "description": "Welcome message",
            "content": {"application/json": {"example": "Hello World!"}},
        },
        401: {"description": "Unauthorized - Invalid or missing JWT token"},
    },
)
async def get_hello(current_user: Annotated[KeycloakUser, RequireAuth]) -> str:
    """Get welcome message (requires authentication to match NestJS behavior)."""
    return "Hello World!"


@router.get("/protected")
async def get_protected(
    current_user: Annotated[KeycloakUser, RequireAuth],
) -> dict[str, str | list[str] | None]:
    """Get protected content (requires authentication)."""
    return {
        "message": f"Hello {current_user.preferred_username or current_user.sub}!",
        "user_id": current_user.sub,
        "roles": current_user.client_roles,
    }
