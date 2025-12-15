"""Prompt assembly helpers with unified caching.

This module centralizes "prompt assembly" work (e.g., formatting history transcripts,
combining system instructions with document context) and caches results in the
`prompt` cache namespace.

Caching is best-effort and conservative:
- History/query prompts are cached only when `user_id` is present to prevent
  cross-user leakage.
- Document-context prompts are cached per-user when `user_id` is present.
"""

from __future__ import annotations

from collections.abc import Callable

from app.core.cache.keys import canonical_json, hash_text
from app.core.cache.provider import get_cache
from app.utils import trim_text


def _prompt_cache_key(prefix: str, payload: dict) -> str:
    return f"{prefix}:{hash_text(canonical_json(payload))}"


def _history_fingerprint(history: list[dict[str, str]] | None, *, max_messages: int) -> list[dict]:
    if not history:
        return []
    trimmed = history[-max_messages:]
    return [
        {
            "role": (msg.get("role") or ""),
            "content_hash": hash_text(msg.get("content") or ""),
        }
        for msg in trimmed
    ]


async def build_history_augmented_query(
    *,
    query: str,
    history: list[dict[str, str]] | None,
    user_id: str | None,
    max_history_chars: int,
    max_history_messages: int = 5,
) -> str:
    """Build an LLM query with a short transcript of prior messages."""

    if not history:
        return query

    if not user_id:
        history_text = "\n".join(
            f"{msg.get('role', '').upper()}: {msg.get('content', '')}" for msg in history[-5:]
        )
        history_text = trim_text(history_text, max_history_chars)
        return f"Previous conversation:\n{history_text}\n\nCurrent question: {query}"

    cache = get_cache("prompt")

    payload = {
        "v": 1,
        "type": "history_augmented_query",
        "user_id": user_id,
        "query_hash": hash_text(query),
        "history": _history_fingerprint(history, max_messages=max_history_messages),
        "max_history_chars": max_history_chars,
        "max_history_messages": max_history_messages,
    }
    cache_key = _prompt_cache_key("prompt_query", payload)

    async def _factory() -> bytes:
        history_text = "\n".join(
            f"{msg.get('role', '').upper()}: {msg.get('content', '')}"
            for msg in history[-max_history_messages:]
        )
        history_text2 = trim_text(history_text, max_history_chars)
        out = f"Previous conversation:\n{history_text2}\n\nCurrent question: {query}"
        return out.encode("utf-8")

    return (await cache.get_or_set(cache_key, _factory)).decode("utf-8")


async def build_system_instructions_with_document_context(
    *,
    base_instructions: str,
    document_context: str,
    user_id: str | None,
    max_doc_context_chars: int,
    header: str,
) -> str:
    """Append document context to base instructions, optionally cached."""

    if not user_id:
        trimmed_context = trim_text(document_context, max_doc_context_chars)
        return base_instructions + f"\n\n{header}\n{trimmed_context}"

    cache = get_cache("prompt")

    payload = {
        "v": 1,
        "type": "system_instructions_with_doc",
        "user_id": user_id,
        "base_hash": hash_text(base_instructions),
        "doc_hash": hash_text(document_context),
        "max_doc_context_chars": max_doc_context_chars,
        "header_hash": hash_text(header),
    }
    cache_key = _prompt_cache_key("prompt_instructions", payload)

    async def _factory() -> bytes:
        trimmed_context = trim_text(document_context, max_doc_context_chars)
        out = base_instructions + f"\n\n{header}\n{trimmed_context}"
        return out.encode("utf-8")

    return (await cache.get_or_set(cache_key, _factory)).decode("utf-8")


async def build_cached(
    *,
    cache_key_prefix: str,
    payload: dict,
    factory: Callable[[], str],
    allow_anonymous: bool = True,
) -> str:
    """Generic prompt cache helper.

    Prefer the more specific helpers above; this is mainly for complex prompt assembly
    where callers already have a stable payload structure.
    """

    if not allow_anonymous and not payload.get("user_id"):
        return factory()

    cache = get_cache("prompt")
    cache_key = _prompt_cache_key(cache_key_prefix, payload)

    async def _factory_bytes() -> bytes:
        return factory().encode("utf-8")

    return (await cache.get_or_set(cache_key, _factory_bytes)).decode("utf-8")
