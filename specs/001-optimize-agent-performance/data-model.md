# Data Model: Unified Caching

This document defines the internal data model used to implement unified caching in `api-ms-agent/`. It does not introduce new externally visible API resources.

## Core Entities

### `CacheKey`
A normalized string key.

**Components (recommended)**
- `namespace` (e.g., `db`, `http`, `embed`, `prompt`, `llm`)
- `tenant_id` (required)
- `user_id` / `session_id` (required when caching user-scoped data)
- `resource-specific parts` (e.g., `session_id`, canonicalized URL/query, model deployment)

**Properties**
- Deterministic: identical inputs yield identical key
- Safe: includes required scope to prevent cross-tenant/user leakage
- Stable: key versioning supported via a `v{N}` prefix segment when schemas change

### `CacheEntry`
A stored value plus metadata.

**Fields**
- `value` (bytes)
- `expires_at_monotonic` (float | None)
- `created_at_monotonic` (float)
- `tags` (set[str]) optional
- `size_bytes` (int) optional (for capacity enforcement)

### `CachePolicy`
Defines how caching behaves per namespace.

**Fields**
- `default_ttl_seconds` (int)
- `max_entries` (int) and/or `max_bytes` (int)
- `eviction` (LRU + TTL)
- `cache_errors` (bool, default false)
- `negative_ttl_seconds` (int, optional)

### `CacheStats` (optional)
Aggregated observability for each namespace.

**Fields**
- `hits`, `misses`, `sets`, `evictions`, `errors`

## Relationships

- A `Cache` instance is scoped to one `namespace` and uses one `CachePolicy`.
- A `Cache` delegates storage to a `CacheBackend`.
- A `TypedCache[T]` is a thin wrapper over `Cache` that encodes/decodes `T` to bytes (JSON/msgpack/etc.).

## Constraints / Invariants

- All cache keys must include `tenant_id`.
- User-scoped data must include `user_id` in the key.
- In-memory cache must be bounded (capacity enforced) and must evict.
- TTLs must be conservative by default to avoid semantic changes.
- Single-flight behavior should be used for `get_or_set` to avoid stampedes under concurrency.
