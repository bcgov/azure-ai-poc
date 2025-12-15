import asyncio

import httpx
import pytest

from app.config import settings
from app.core.cache import provider as cache_provider
from app.http_client import cached_get_json


class _DelayedJsonTransport(httpx.AsyncBaseTransport):
    def __init__(self):
        self.calls = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        await asyncio.sleep(0.05)
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            json={"ok": True, "path": str(request.url)},
            request=request,
        )


@pytest.fixture(autouse=True)
def _isolate_cache(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cache_enabled", True, raising=False)
    settings.cache_http_negative_ttl_seconds = 0
    cache_provider._caches.clear()  # type: ignore[attr-defined]
    yield
    cache_provider._caches.clear()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_workload_smoke_cached_get_json_concurrent() -> None:
    transport = _DelayedJsonTransport()
    async with httpx.AsyncClient(base_url="https://example.test", transport=transport) as client:
        tasks = [cached_get_json(client, "/thing", params={"q": "a"}) for _ in range(50)]
        results = await asyncio.gather(*tasks)

    assert transport.calls == 1
    assert all(r == results[0] for r in results)
