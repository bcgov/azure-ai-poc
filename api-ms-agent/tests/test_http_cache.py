import httpx
import pytest

from app.config import settings
from app.core.cache import provider as cache_provider
from app.services.mcp.base import MCPWrapper


class _CountingTransport(httpx.AsyncBaseTransport):
    def __init__(self):
        self.calls = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            json={"ok": True, "path": str(request.url)},
            request=request,
        )


class _TestWrapper(MCPWrapper):
    @property
    def tools(self):
        return []

    async def execute_tool(self, tool_name: str, arguments: dict):
        raise NotImplementedError


@pytest.fixture(autouse=True)
def _isolate_cache(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cache_enabled", True, raising=False)
    cache_provider._caches.clear()  # type: ignore[attr-defined]
    yield
    cache_provider._caches.clear()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_mcp_get_requests_are_cached():
    transport = _CountingTransport()
    client = httpx.AsyncClient(base_url="https://example.test", transport=transport)

    wrapper = _TestWrapper(base_url="https://example.test")

    async def _get_client():
        return client

    wrapper._get_client = _get_client  # type: ignore[method-assign]

    out1 = await wrapper._request("GET", "/thing", params={"q": "a"})
    out2 = await wrapper._request("GET", "/thing", params={"q": "a"})

    assert out1 == out2
    assert transport.calls == 1

    await client.aclose()
