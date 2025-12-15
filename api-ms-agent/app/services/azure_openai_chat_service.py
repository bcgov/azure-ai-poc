"""Azure OpenAI chat completion helper with opt-in deterministic response caching.

This service wraps `AsyncAzureOpenAI.chat.completions.create(...)` calls and
caches the *assistant message content* in the unified `llm` cache namespace.

Safety / invariants:
- Caching is opt-in via `settings.cache_llm_ttl_seconds > 0`.
- Caching is only attempted for deterministic calls (`temperature == 0`).
- Responses are cached per-user (`user` must be provided) to avoid cross-user leakage.
- Only non-streaming calls are supported (this code assumes `create(...)` returns a response).
"""

from __future__ import annotations

from typing import Any

from openai import AsyncAzureOpenAI

from app.config import settings
from app.core.cache.keys import canonical_json, hash_text
from app.core.cache.provider import get_cache


def _llm_cache_key(payload: dict[str, Any]) -> str:
    return f"llm_resp:{hash_text(canonical_json(payload))}"


def _messages_fingerprint(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fp: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if isinstance(content, str):
            content_hash: str | None = hash_text(content)
        else:
            # For non-string content (tool calls, multimodal), hash its canonical JSON.
            content_hash = hash_text(canonical_json(content)) if content is not None else None

        fp.append({"role": role, "content_hash": content_hash})
    return fp


class AzureOpenAIChatService:
    def __init__(self, client: AsyncAzureOpenAI):
        self._client = client

    async def create_chat_completion_content(
        self,
        *,
        deployment: str,
        messages: list[dict[str, Any]],
        user: str | None,
        temperature: float,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        additional_chat_options: dict[str, Any] | None = None,
    ) -> str:
        """Create a chat completion and return the assistant message content."""

        # Opt-in only
        if settings.cache_llm_ttl_seconds <= 0:
            response = await self._client.chat.completions.create(
                model=deployment,
                messages=messages,
                response_format=response_format,
                temperature=temperature,
                max_tokens=max_tokens,
                additional_chat_options=additional_chat_options,
                user=user,
            )
            return response.choices[0].message.content or ""

        # Deterministic-only (conservative)
        if temperature != 0:
            response = await self._client.chat.completions.create(
                model=deployment,
                messages=messages,
                response_format=response_format,
                temperature=temperature,
                max_tokens=max_tokens,
                additional_chat_options=additional_chat_options,
                user=user,
            )
            return response.choices[0].message.content or ""

        # Per-user only to avoid cross-user leakage
        if not user:
            response = await self._client.chat.completions.create(
                model=deployment,
                messages=messages,
                response_format=response_format,
                temperature=temperature,
                max_tokens=max_tokens,
                additional_chat_options=additional_chat_options,
                user=user,
            )
            return response.choices[0].message.content or ""

        cache = get_cache("llm")

        payload = {
            "v": 1,
            "deployment": deployment,
            "user": user,
            "messages": _messages_fingerprint(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": response_format,
            "additional_chat_options": additional_chat_options,
        }

        cache_key = _llm_cache_key(payload)

        async def _factory() -> bytes:
            response = await self._client.chat.completions.create(
                model=deployment,
                messages=messages,
                response_format=response_format,
                temperature=temperature,
                max_tokens=max_tokens,
                additional_chat_options=additional_chat_options,
                user=user,
            )
            content = response.choices[0].message.content or ""
            return content.encode("utf-8")

        return (await cache.get_or_set(cache_key, _factory)).decode("utf-8")
