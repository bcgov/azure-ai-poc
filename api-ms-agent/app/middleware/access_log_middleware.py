"""Access log middleware for FastAPI application."""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.logger import get_logger

logger = get_logger(__name__)


class AccessLogMiddleware(BaseHTTPMiddleware):
    """
    Access log middleware that logs HTTP requests with timing and content length.

    Produces logs like:
    INFO:     [hostname:pid] 169.254.129.4:33194 - "GET /api/v1/chat/sessions HTTP/1.1" 200 1234B 45.2ms
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and log access details."""
        start_time = time.perf_counter()

        # Get path for filtering
        path = request.url.path

        # Skip logging for health check and root endpoints
        if path in ("/", "/health"):
            return await call_next(request)

        # Get client info
        client_host = request.client.host if request.client else "-"
        client_port = request.client.port if request.client else "-"
        method = request.method
        query = request.url.query
        full_path = f"{path}?{query}" if query else path
        http_version = request.scope.get("http_version", "1.1")

        # Process request
        response: Response = await call_next(request)

        # Calculate timing
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Get content length
        content_length = response.headers.get("content-length", "-")
        if content_length != "-":
            content_length = f"{content_length}B"

        # Log in Uvicorn-like format with timing and size
        logger.info(
            "http_request",
            client=f"{client_host}:{client_port}",
            request=f'"{method} {full_path} HTTP/{http_version}"',
            status=response.status_code,
            size=content_length,
            duration=f"{duration_ms:.1f}ms",
        )

        return response
