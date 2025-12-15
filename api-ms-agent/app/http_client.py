"""
Shared HTTP client with connection pooling.

This module provides a centralized httpx.AsyncClient instance
for efficient HTTP connection reuse across the application.
"""

from __future__ import annotations

import json

import httpx

from app.config import settings
from app.core.cache.keys import canonical_json, hash_text
from app.core.cache.provider import get_cache
from app.logger import get_logger

logger = get_logger(__name__)

# Global shared HTTP client for general-purpose requests
_shared_client: httpx.AsyncClient | None = None

# Default configuration for connection pooling
DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
DEFAULT_LIMITS = httpx.Limits(
    max_connections=100,
    max_keepalive_connections=20,
    keepalive_expiry=30.0,
)


async def get_http_client() -> httpx.AsyncClient:
    """
    Get or create the shared HTTP client.

    This client is configured with connection pooling for efficient
    reuse of TCP connections across multiple requests.

    Returns:
        httpx.AsyncClient: The shared HTTP client instance
    """
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT,
            limits=DEFAULT_LIMITS,
            http2=True,  # Enable HTTP/2 for multiplexing
        )
        logger.info(
            "http_client_created",
            max_connections=DEFAULT_LIMITS.max_connections,
            max_keepalive=DEFAULT_LIMITS.max_keepalive_connections,
        )
    return _shared_client


async def close_http_client() -> None:
    """
    Close the shared HTTP client.

    Should be called during application shutdown to properly
    release all connections.
    """
    global _shared_client
    if _shared_client is not None and not _shared_client.is_closed:
        await _shared_client.aclose()
        logger.info("http_client_closed")
    _shared_client = None


def create_scoped_client(
    base_url: str,
    timeout: float = 30.0,
    headers: dict[str, str] | None = None,
    max_connections: int = 10,
    max_keepalive_connections: int = 5,
) -> httpx.AsyncClient:
    """
    Create a scoped HTTP client for specific API integrations.

    Use this for clients that need a dedicated base_url or custom headers,
    such as MCP wrappers or external service clients.

    Args:
        base_url: Base URL for all requests
        timeout: Request timeout in seconds
        headers: Optional default headers for all requests
        max_connections: Maximum number of connections
        max_keepalive_connections: Maximum number of keepalive connections

    Returns:
        httpx.AsyncClient: A new scoped client instance
    """
    return httpx.AsyncClient(
        base_url=base_url,
        timeout=httpx.Timeout(timeout),
        headers=headers or {},
        limits=httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=30.0,
        ),
        http2=True,
    )


def _is_request_cacheable(client: httpx.AsyncClient) -> bool:
    # Conservative: do not cache requests that are likely user/session specific.
    headers = getattr(client, "headers", None) or {}
    for key in ["authorization", "cookie", "x-api-key"]:
        if key in {str(k).lower() for k in headers.keys()}:
            return False
    return True


async def cached_get_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict[str, object] | None = None,
    timeout_seconds: float | None = None,
) -> dict[str, object]:
    """GET request with unified caching.

    - GET-only (idempotent)
    - Best-effort caching (never raises due to cache issues)
    - Skips caching for authenticated requests
    """
    effective_timeout = (
        settings.http_request_timeout_seconds if timeout_seconds is None else timeout_seconds
    )

    if not _is_request_cacheable(client):
        response = await client.get(url, params=params, timeout=effective_timeout)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type or "json" in content_type:
            try:
                return response.json()
            except Exception:
                return {"raw_text": response.text}
        return {"raw_text": response.text}

    cache = get_cache("http")
    payload = {
        "base_url": str(getattr(client, "base_url", "")),
        "url": url,
        "params": params or {},
    }
    cache_key = f"http_get:{hash_text(canonical_json(payload))}"

    negative_ttl = int(settings.cache_http_negative_ttl_seconds)

    async def factory() -> bytes:
        response = await client.get(url, params=params, timeout=effective_timeout)

        if negative_ttl > 0 and response.status_code in (404, 410):
            # Cache a sentinel that will re-raise an equivalent HTTPStatusError.
            # Do not cache other error classes (429/5xx) since they may be transient.
            return canonical_json(
                {
                    "error": {
                        "status": response.status_code,
                        "text": (response.text or "")[:512],
                    }
                }
            ).encode("utf-8")

        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type or "json" in content_type:
            try:
                data: object = response.json()
                return canonical_json({"data": data}).encode("utf-8")
            except Exception:
                return canonical_json({"raw_text": response.text}).encode("utf-8")
        return canonical_json({"raw_text": response.text}).encode("utf-8")

    try:
        raw = await cache.get_or_set(cache_key, factory)
        decoded = json.loads(raw.decode("utf-8"))

        if isinstance(decoded, dict) and "error" in decoded:
            err = decoded.get("error")
            if isinstance(err, dict):
                status = int(err.get("status", 500))
                text = str(err.get("text", ""))

                # Ensure a short TTL for negative cache entries.
                if negative_ttl > 0:
                    cache.set(cache_key, raw, ttl_seconds=negative_ttl)

                base_url = str(getattr(client, "base_url", "") or "")
                full_url = str(httpx.URL(base_url).join(url)) if base_url else url
                request = httpx.Request("GET", full_url, params=params)
                response = httpx.Response(status_code=status, request=request, text=text)
                raise httpx.HTTPStatusError(
                    f"Cached HTTP error response: {status}",
                    request=request,
                    response=response,
                )

        if isinstance(decoded, dict) and "data" in decoded:
            data = decoded["data"]
            return data if isinstance(data, dict) else {"data": data}
        return decoded if isinstance(decoded, dict) else {"data": decoded}
    except (httpx.HTTPStatusError, httpx.RequestError, TimeoutError):
        raise
    except Exception:
        # Cache is best-effort; fall back to uncached.
        response = await client.get(url, params=params, timeout=effective_timeout)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type or "json" in content_type:
            try:
                return response.json()
            except Exception:
                return {"raw_text": response.text}
        return {"raw_text": response.text}
