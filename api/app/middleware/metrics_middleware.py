"""Prometheus metrics middleware."""

import time
from collections.abc import Callable

from fastapi import Request, Response
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

# Prometheus metrics
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status_code"]
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Prometheus metrics collection middleware."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Collect metrics for requests."""
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Extract endpoint path
        endpoint = request.url.path
        method = request.method
        status_code = str(response.status_code)

        # Update metrics
        REQUEST_COUNT.labels(
            method=method, endpoint=endpoint, status_code=status_code
        ).inc()

        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

        return response
