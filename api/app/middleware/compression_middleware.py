"""Compression middleware for optimizing response sizes."""

import gzip
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logger import get_logger

logger = get_logger(__name__)


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    Middleware for compressing HTTP responses.

    Supports gzip compression for responses larger than min_size.
    Automatically detects client support via Accept-Encoding header.
    """

    def __init__(
        self,
        app: ASGIApp,
        min_size: int = 1024,  # Only compress responses > 1KB
        compression_level: int = 6,  # gzip compression level (1-9)
        excluded_paths: list[str] | None = None,
    ):
        """
        Initialize compression middleware.

        Args:
            app: ASGI application
            min_size: Minimum response size in bytes to compress
            compression_level: gzip compression level (1=fast, 9=best)
            excluded_paths: List of path prefixes to exclude from compression
        """
        super().__init__(app)
        self.min_size = min_size
        self.compression_level = compression_level
        self.excluded_paths = excluded_paths or [
            "/metrics",  # Prometheus metrics
            "/health",  # Health checks
            "/api/docs",  # API documentation
            "/api/redoc",  # API documentation
            "/api/openapi.json",  # OpenAPI schema
        ]
        self._compressed_count = 0
        self._total_bytes_saved = 0

    async def dispatch(self, request: Request, call_next):
        """Process request and compress response if appropriate."""
        start_time = time.time()

        # Check if path is excluded
        for excluded in self.excluded_paths:
            if request.url.path.startswith(excluded):
                return await call_next(request)

        # Check if client supports gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        supports_gzip = "gzip" in accept_encoding.lower()

        if not supports_gzip:
            return await call_next(request)

        # Get response
        response = await call_next(request)

        # Only compress specific content types
        content_type = response.headers.get("content-type", "")
        compressible_types = [
            "application/json",
            "text/html",
            "text/plain",
            "text/csv",
            "application/xml",
            "text/xml",
        ]

        should_compress = any(ct in content_type for ct in compressible_types)

        if not should_compress:
            return response

        # Read response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        original_size = len(body)

        # Only compress if body is large enough
        if original_size < self.min_size:
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        # Compress body
        try:
            compressed_body = gzip.compress(body, compresslevel=self.compression_level)
            compressed_size = len(compressed_body)

            # Only use compression if it actually reduces size
            if compressed_size < original_size:
                compression_ratio = (1 - compressed_size / original_size) * 100
                process_time = (time.time() - start_time) * 1000

                self._compressed_count += 1
                self._total_bytes_saved += original_size - compressed_size

                logger.debug(
                    f"Compressed response: {original_size} -> {compressed_size} bytes "
                    f"({compression_ratio:.1f}% reduction) in {process_time:.2f}ms"
                )

                headers = dict(response.headers)
                headers["content-encoding"] = "gzip"
                headers["content-length"] = str(compressed_size)

                return Response(
                    content=compressed_body,
                    status_code=response.status_code,
                    headers=headers,
                    media_type=response.media_type,
                )

        except Exception as e:
            logger.warning(f"Failed to compress response: {e}")

        # Return uncompressed if compression failed or didn't help
        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

    def get_stats(self) -> dict[str, any]:  # type: ignore[valid-type]
        """Get compression statistics."""
        return {
            "compressed_responses": self._compressed_count,
            "total_bytes_saved": self._total_bytes_saved,
            "total_mb_saved": round(self._total_bytes_saved / (1024 * 1024), 2),
        }
