import pytest

from app.config import settings
from app.core.cache import provider as cache_provider
from app.services.prompt_builder import build_history_augmented_query


@pytest.fixture(autouse=True)
def _isolate_cache(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cache_enabled", True, raising=False)
    cache_provider._caches.clear()  # type: ignore[attr-defined]
    yield
    cache_provider._caches.clear()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_prompt_history_query_cached_per_user():
    history = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]

    out1 = await build_history_augmented_query(
        query="What time is it?",
        history=history,
        user_id="u1",
        max_history_chars=10_000,
    )
    out2 = await build_history_augmented_query(
        query="What time is it?",
        history=history,
        user_id="u1",
        max_history_chars=10_000,
    )

    assert out1 == out2

    # Cache should have stored exactly one entry in the prompt namespace.
    cache = cache_provider.get_cache("prompt")
    backend = cache.backend
    assert hasattr(backend, "_entries")
    assert len(getattr(backend, "_entries")) == 1


@pytest.mark.asyncio
async def test_prompt_history_query_not_cached_without_user_id():
    history = [{"role": "user", "content": "hello"}]

    out1 = await build_history_augmented_query(
        query="What time is it?",
        history=history,
        user_id=None,
        max_history_chars=10_000,
    )
    out2 = await build_history_augmented_query(
        query="What time is it?",
        history=history,
        user_id=None,
        max_history_chars=10_000,
    )

    assert out1 == out2

    cache = cache_provider.get_cache("prompt")
    backend = cache.backend
    assert hasattr(backend, "_entries")
    assert len(getattr(backend, "_entries")) == 0
