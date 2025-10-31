"""Rate limiting setup using slowapi."""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def get_request_identifier(request: Request) -> str:
    """Get identifier for rate limiting (IP address or user ID)."""
    # Try to get user ID from JWT token first
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"

    # Fall back to IP address
    return get_remote_address(request)


# Create limiter instance for use in route decorators
limiter = Limiter(
    key_func=get_request_identifier,
    default_limits=[f"{settings.RATE_LIMIT_MAX_REQUESTS}/minute"],
)

# Export limiter for use in route decorators
__all__ = ["limiter", "get_request_identifier"]
