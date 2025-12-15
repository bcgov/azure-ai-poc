# Contract: Unified Cache Interface (`api-ms-agent/app/core/cache/*`)

This contract describes the unified caching interface used by all caching call sites.

## Backend Interface

A backend must implement the following operations (names are illustrative; exact names are implementation details):

- `get(key: str) -> bytes | None`
- `set(key: str, value: bytes, ttl_seconds: int, tags: list[str] | None = None) -> None`
- `delete(key: str) -> None`
- `clear_namespace(namespace: str) -> None` (optional)

## High-level Cache API

A higher-level cache wrapper provides:

- Namespacing (policy defaults)
- Typed encode/decode wrappers (`TypedCache[T]`)
- `get_or_set(key, ttl_seconds, factory)` with stampede protection

## Behavioral Guarantees

- **Scope safety**: key-building helpers must require `tenant_id` and should require `user_id` for user-scoped data.
- **No semantic changes by default**: LLM response caching is disabled unless explicitly enabled for deterministic requests.
- **Bounded memory**: in-memory backend enforces capacity via eviction.
- **TTL correctness**: expired entries are not returned.
- **Stampede protection**: concurrent `get_or_set` calls for the same key result in a single factory execution.

## Non-goals

- No persistent cache guarantees.
- No cross-process sharing in the in-memory backend.
