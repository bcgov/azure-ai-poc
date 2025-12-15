from datetime import UTC, datetime
from typing import Any

import pytest

from app.config import settings
from app.core.cache import provider as cache_provider
from app.services.cosmos_db_service import CosmosDbService


class _AsyncIter:
    def __init__(self, items: list[dict[str, Any]]):
        self._items = items

    def __aiter__(self):
        async def gen():
            for item in self._items:
                yield item

        return gen()


class _FakeContainer:
    def __init__(self, *, items: list[dict[str, Any]] | None = None):
        self.items = items or []
        self.query_calls = 0
        self.read_calls = 0

    def query_items(self, *args, **kwargs):
        self.query_calls += 1
        return _AsyncIter(self.items)

    async def read_item(self, *args, **kwargs):
        self.read_calls += 1
        return self.items[0]


@pytest.fixture(autouse=True)
def _isolate_cache(monkeypatch: pytest.MonkeyPatch):
    # Ensure cache is enabled and cleared between tests.
    monkeypatch.setattr(settings, "cache_enabled", True, raising=False)
    cache_provider._caches.clear()  # type: ignore[attr-defined]
    yield
    cache_provider._caches.clear()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_cosmos_chat_history_cached_on_second_call():
    svc = CosmosDbService()
    svc._initialized = True

    now = datetime.now(UTC)
    svc.chat_container = _FakeContainer(
        items=[
            {
                "id": "m1",
                "session_id": "s1",
                "user_id": "u1",
                "role": "user",
                "content": "hello",
                "timestamp": now.isoformat(),
                "sources": [],
                "metadata": {},
            },
            {
                "id": "m2",
                "session_id": "s1",
                "user_id": "u1",
                "role": "assistant",
                "content": "hi",
                "timestamp": now.isoformat(),
                "sources": [],
                "metadata": {},
            },
        ]
    )

    # First call populates cache.
    out1 = await svc.get_chat_history("s1", "u1", limit=2)
    assert len(out1) == 2

    # Second call should hit cache (no additional query_items call).
    out2 = await svc.get_chat_history("s1", "u1", limit=2)
    assert len(out2) == 2
    assert svc.chat_container.query_calls == 1


@pytest.mark.asyncio
async def test_cosmos_workflow_state_cached_on_second_call():
    svc = CosmosDbService()
    svc._initialized = True

    now = datetime.now(UTC)
    svc.workflows_container = _FakeContainer(
        items=[
            {
                "id": "wf_w1",
                "workflow_id": "w1",
                "user_id": "u1",
                "workflow_type": "research",
                "status": "running",
                "current_step": "step1",
                "context": {},
                "result": None,
                "error": None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        ]
    )

    state1 = await svc.get_workflow_state("w1", "u1")
    assert state1 is not None
    state2 = await svc.get_workflow_state("w1", "u1")
    assert state2 is not None

    assert svc.workflows_container.read_calls == 1
