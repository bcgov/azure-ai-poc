import httpx
import pytest

from app.config import settings
from app.core.cache import provider as cache_provider
from app.http_client import cached_get_json


class _ErrorTransport(httpx.AsyncBaseTransport):
    def __init__(self, status_code: int):
        self.calls = 0
        self._status_code = status_code

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        return httpx.Response(
            self._status_code,
            headers={"Content-Type": "text/plain"},
            text="not found",
            request=request,
        )


@pytest.fixture(autouse=True)
def _isolate_cache(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cache_enabled", True, raising=False)
    cache_provider._caches.clear()  # type: ignore[attr-defined]
    yield
    cache_provider._caches.clear()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_http_negative_cache_disabled_by_default():
    transport = _ErrorTransport(status_code=404)
    async with httpx.AsyncClient(base_url="https://example.test", transport=transport) as client:
        settings.cache_http_negative_ttl_seconds = 0

        with pytest.raises(httpx.HTTPStatusError):
            await cached_get_json(client, "/missing")
        with pytest.raises(httpx.HTTPStatusError):
            await cached_get_json(client, "/missing")

    assert transport.calls == 2


@pytest.mark.asyncio
async def test_http_negative_cache_enabled_caches_404():
    transport = _ErrorTransport(status_code=404)
    async with httpx.AsyncClient(base_url="https://example.test", transport=transport) as client:
        settings.cache_http_negative_ttl_seconds = 5

        with pytest.raises(httpx.HTTPStatusError):
            await cached_get_json(client, "/missing")
        with pytest.raises(httpx.HTTPStatusError):
            await cached_get_json(client, "/missing")

    assert transport.calls == 1


@pytest.mark.asyncio
async def test_http_negative_cache_enabled_caches_410():
    transport = _ErrorTransport(status_code=410)
    async with httpx.AsyncClient(base_url="https://example.test", transport=transport) as client:
        settings.cache_http_negative_ttl_seconds = 5

        with pytest.raises(httpx.HTTPStatusError):
            await cached_get_json(client, "/gone")
        with pytest.raises(httpx.HTTPStatusError):
            await cached_get_json(client, "/gone")

    assert transport.calls == 1
