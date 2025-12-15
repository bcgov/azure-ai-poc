from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.config import settings
from app.core.cache import provider as cache_provider
from app.services.azure_openai_chat_service import AzureOpenAIChatService


@dataclass
class _FakeMessage:
    content: str | None


@dataclass
class _FakeChoice:
    message: _FakeMessage


@dataclass
class _FakeResponse:
    choices: list[_FakeChoice]


class _FakeCompletions:
    def __init__(self):
        self.calls = 0

    async def create(self, **kwargs):
        self.calls += 1
        # Make response dependent on call count to verify caching.
        return _FakeResponse(
            choices=[_FakeChoice(message=_FakeMessage(content=f"resp-{self.calls}"))]
        )


class _FakeChat:
    def __init__(self, completions: _FakeCompletions):
        self.completions = completions


class _FakeClient:
    def __init__(self):
        self._completions = _FakeCompletions()
        self.chat = _FakeChat(self._completions)


@pytest.fixture(autouse=True)
def _isolate_cache(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cache_enabled", True, raising=False)
    cache_provider._caches.clear()  # type: ignore[attr-defined]
    yield
    cache_provider._caches.clear()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_llm_response_cached_when_opted_in_and_deterministic(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cache_llm_ttl_seconds", 60, raising=False)

    client = _FakeClient()
    svc = AzureOpenAIChatService(client)  # type: ignore[arg-type]

    messages = [
        {"role": "system", "content": "You are a test"},
        {"role": "user", "content": "Hello"},
    ]

    out1 = await svc.create_chat_completion_content(
        deployment="dep",
        messages=messages,
        user="u1",
        temperature=0,
        max_tokens=10,
        response_format={"type": "json_object"},
    )
    out2 = await svc.create_chat_completion_content(
        deployment="dep",
        messages=messages,
        user="u1",
        temperature=0,
        max_tokens=10,
        response_format={"type": "json_object"},
    )

    assert out1 == out2
    assert client._completions.calls == 1


@pytest.mark.asyncio
async def test_llm_response_not_cached_when_temperature_nonzero(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cache_llm_ttl_seconds", 60, raising=False)

    client = _FakeClient()
    svc = AzureOpenAIChatService(client)  # type: ignore[arg-type]

    messages = [{"role": "user", "content": "Hello"}]

    out1 = await svc.create_chat_completion_content(
        deployment="dep",
        messages=messages,
        user="u1",
        temperature=0.1,
    )
    out2 = await svc.create_chat_completion_content(
        deployment="dep",
        messages=messages,
        user="u1",
        temperature=0.1,
    )

    assert out1 != out2
    assert client._completions.calls == 2


@pytest.mark.asyncio
async def test_llm_response_not_cached_when_user_missing(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cache_llm_ttl_seconds", 60, raising=False)

    client = _FakeClient()
    svc = AzureOpenAIChatService(client)  # type: ignore[arg-type]

    messages = [{"role": "user", "content": "Hello"}]

    out1 = await svc.create_chat_completion_content(
        deployment="dep",
        messages=messages,
        user=None,
        temperature=0,
    )
    out2 = await svc.create_chat_completion_content(
        deployment="dep",
        messages=messages,
        user=None,
        temperature=0,
    )

    assert out1 != out2
    assert client._completions.calls == 2
