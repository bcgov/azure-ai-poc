# Implementation Tasks: Unified Caching (api-ms-agent)

**Branch**: `001-optimize-agent-performance`  
**Scope**: `api-ms-agent/` only (`api/` is deprecated; do not modify).

This is the Phase 2 task breakdown to implement unified caching while keeping all functionality the same.

## Task 0 — Guardrails

- Confirm no public API changes:
  - Verify routers and response models remain unchanged.
  - Ensure no new required headers/env vars for normal operation.
- Confirm multi-tenant safety requirements:
  - Cache keys MUST include tenant id.
  - User-scoped data MUST include user id.

## Task 1 — Add cache core package

- Create `api-ms-agent/app/core/cache/` package with:
  - `CacheBackend` interface (get/set/delete)
  - In-memory backend (bounded + TTL eviction)
  - `Cache` facade with namespace + policy defaults
  - `get_or_set` with per-key single-flight (stampede control)
- Ensure:
  - Fully typed APIs
  - No secrets logged
  - Bounded memory (max entries and/or max bytes)

## Task 2 — Add cache key building helpers

- Add `api-ms-agent/app/core/cache/keys.py` (or similar) to centralize key building:
  - `tenant_scoped_key(namespace, tenant_id, *parts)`
  - `user_scoped_key(namespace, tenant_id, user_id, *parts)`
  - Canonicalization helpers:
    - Stable JSON serialization (sorted keys)
    - URL + query normalization
    - Body hashing (only for safe idempotent cases)
- Add key versioning support:
  - Prefix keys with `v1` and bump when schema changes.

## Task 3 — Add cache configuration + policies

- Extend `api-ms-agent` settings to include cache config (defaults preserve semantics):
  - Global enable/disable
  - Per-namespace TTL defaults
  - Capacity limits
  - LLM response caching disabled by default (TTL=0)
- Add a policy registry:
  - `db`, `http`, `embed`, `prompt`, `llm`
  - Conservative TTLs (see research.md)

## Task 4 — Instrumentation

- Add structured logging around caching:
  - `namespace`, `key_prefix` (never full user content), `hit|miss|set|evict`, `duration_ms`
- Add opt-in debug logging for full keys only in local/dev (never production).

## Task 5 — Unify / migrate existing ad-hoc caches

- Identify and replace ad-hoc caches with unified cache:
  - JWKS cache (auth)
  - Any chat history/session read caches
  - Workflow research in-memory state caches
  - Orchestrator tool / reference data caches (e.g., parks list)
- Ensure behavior stays identical:
  - Same TTL semantics (or more conservative)
  - Same scoping

## Task 6 — Cosmos DB read caching (first performance win)

- Wrap safe Cosmos read paths with caching:
  - Session list / chat history reads
  - Document metadata list
  - Workflow state reads
- Add targeted invalidation:
  - After writes, delete the specific keys (or tag-based invalidation if implemented)
- Avoid caching:
  - Writes
  - Any query whose result depends on time-sensitive auth rules unless scoped appropriately

## Task 7 — Outbound HTTP caching (GET-only first)

- Add caching to the shared outbound request layer (or in the specific service wrappers if there is no single layer):
  - Cache GET responses only
  - Canonicalize URL/query and include tenant/user scope
  - Do not cache non-2xx by default
  - Keep TTLs conservative and per-service

## Task 8 — Embeddings caching (if repeated embeddings exist)

- Add caching for embedding generation:
  - Key by tenant + embedding deployment + content hash
  - Long TTL (deployment-versioned keys)
- Ensure exact same embeddings are returned as before.

## Task 9 — Prompt assembly caching (optional)

- Only implement if prompt rendering is measured to be non-trivial.
- Cache rendered prompt segments by template id + input hash, short TTL.

## Task 10 — LLM response caching (opt-in, deterministic only)

- Implement behind a strict safety gate:
  - Disabled by default
  - Enabled only when deterministic (e.g., temperature == 0) or explicit internal flag
  - Tenant + user scoped
  - Very short TTL (1–5 min)
- Ensure:
  - No caching of tool-call side effects
  - No caching across different tool definitions / schemas

## Task 11 — Tests

Add unit tests in `api-ms-agent/tests/`:

- Cache core:
  - TTL expiry behavior
  - Capacity eviction behavior (LRU)
  - Single-flight: factory runs once under concurrency
  - Thread/async safety (match how it’s used in code)
- Key safety:
  - Tenant/user included (prevent accidental omission)
- Integration-style tests (where feasible):
  - Cosmos read caching hit/miss (can be mocked)
  - HTTP caching hit/miss (mock httpx)
- Regression safety:
  - Existing tests still pass

## Task 12 — Documentation + rollout notes

- Update feature docs if implementation details diverge:
  - [research.md](research.md) (TTL/policy decisions)
  - [contracts/cache-configuration.md](contracts/cache-configuration.md) (settings)
  - [quickstart.md](quickstart.md) (how to validate)

## Definition of Done

- All caching routes through unified interface.
- No functionality changes (API schemas unchanged).
- Tests added for cache correctness and scoping.
- Logs show cache hit/miss and latency without leaking secrets.
- Bounded memory enforced for in-memory backend.
