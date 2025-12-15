"""Performance instrumentation middleware.

Captures request latency and emits a structured performance log event.
This is intentionally log-only (no response/header changes).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.cache import stats as cache_stats
from app.logger import log_request_performance


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Logs request timing + cache deltas for performance visibility."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Skip perf logs for extremely noisy endpoints.
        if path in ("/", "/health"):
            return await call_next(request)

        request_id = (
            request.headers.get("x-request-id")
            or request.headers.get("x-correlation-id")
            or request.headers.get("x-ms-client-request-id")
            or str(uuid4())
        )

        start = time.perf_counter()
        before = cache_stats.snapshot()

        status_code: int = 500
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000.0
            after = cache_stats.snapshot()
            delta = cache_stats.diff(before, after)

            log_request_performance(
                request_id=request_id,
                method=request.method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
                cache_delta=delta,
            )
