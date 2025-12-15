# Phase 0 Research: Agent Performance Optimization (Unified Caching)

**Feature**: [spec.md](spec.md)  
**Plan**: [plan.md](plan.md)  
**Date**: 2025-12-14

This feature keeps user-visible functionality the same and focuses on performance improvements via caching. Scope and findings apply to `api-ms-agent/` only (the `api/` service is deprecated and excluded).

## Decisions

### Decision 1: Introduce a unified cache interface with a pluggable backend

**Decision**: Create a single cache interface used across the service for all caching categories (API calls, DB reads, prompt assembly, LLM responses). Implement an in-memory backend first, designed so a Redis backend can be added later without changing call sites.

**Rationale**:
- The service currently contains multiple ad-hoc in-memory caches with different patterns (dicts + locks + TTL) which makes behavior inconsistent and hard to validate.
- A unified interface enables consistent tenant scoping, TTL policy, eviction policy, and observability (hit/miss logging).

**Alternatives considered**:
- Continue with ad-hoc dict caches per module: rejected due to inconsistency and higher regression risk.
- Use an off-the-shelf caching library directly at call sites: rejected because it couples code to a specific backend and makes a future Redis migration harder.

### Decision 2: Use namespaced caches with conservative TTL defaults

**Decision**: Split caching into explicit namespaces (e.g., `http`, `db`, `prompt`, `llm`) with per-namespace default TTLs and size limits.

**Rationale**:
- Different data has different freshness requirements and invalidation capabilities.
- Namespacing prevents accidental key collisions and allows targeted invalidation.

**Alternatives considered**:
- One global cache: rejected due to higher key collision risk and inability to tune policies.

### Decision 3: Cache keys must always include tenant and (when applicable) user scope

**Decision**: Cache key builders must include a tenant identifier, and include user/session identifiers for user-scoped data.

**Rationale**:
- Prevents cross-tenant and cross-user leakage.
- Makes it safe to enable caching without changing authorization behavior.

**Alternatives considered**:
- Cache by URL/query only: rejected due to security risk.

### Decision 4: LLM response caching is opt-in and only enabled when it cannot change semantics

**Decision**: Only cache LLM responses when the request is effectively deterministic and identical (e.g., temperature is 0 or an explicit “cache-safe” flag is set). Default behavior is conservative (cache disabled for non-deterministic requests).

**Rationale**:
- Caching non-deterministic generations can change user-visible behavior.
- The feature requirement is "keep all functionality same".

**Alternatives considered**:
- Cache all LLM responses with a short TTL: rejected due to semantic drift and unpredictability.

## Caching Candidates (Prioritized)

### 1) Cosmos DB read caching (high impact, low risk)

**Where**:
- User-scoped reads like chat history and session listings.
- Document metadata listing.
- Workflow state reads.

**Key structure**:
- `db:{tenant}:{user_id}:chat_history:{session_id}:{limit}`
- `db:{tenant}:{user_id}:sessions:{page}:{page_size}`
- `db:{tenant}:{user_id}:documents:{limit}`
- `db:{tenant}:{user_id}:workflow_state:{run_id}`

**TTL defaults (conservative)**:
- Chat history / sessions: 10–30 seconds
- Documents list: 30–60 seconds
- Workflow state reads: 5–15 seconds

**Invalidation strategy**:
- Write-through invalidation for same-user keys after writes (save message, create/delete session, save/delete document metadata, save workflow state).

### 2) Outbound HTTP/API call caching (high impact, moderate risk)

**Where**:
- External/public data sources queried via httpx (e.g., Parks/Geocoder/OrgBook tool calls).
- Auth-related JWKs fetch.

**Key structure**:
- `http:{tenant}:{service}:{method}:{url}:{canonical_query}:{body_hash}:{variant}`
  - `canonical_query`: sorted query parameters
  - `body_hash`: only for idempotent requests (default: GET-only)
  - `variant`: optional (e.g., accept-language) when it affects results

**TTL defaults**:
- Public reference data: 15 minutes to 24 hours depending on volatility
- JWKs: 10 minutes (aligned with existing behavior)

**Invalidation strategy**:
- Primarily TTL-based for external data.
- Do not cache error responses by default (optional short negative caching only if needed).

### 3) Embeddings caching (high cost, usually safe)

**Where**:
- Repeated embeddings for identical text/chunks.

**Key structure**:
- `embed:{tenant}:{deployment}:{sha256(normalized_text)}`

**TTL defaults**:
- Long-lived (days) or effectively unbounded when keys are versioned by model deployment.

**Invalidation strategy**:
- Implicit via deployment/model changes (key changes), or explicit re-index operations.

### 4) Prompt assembly caching (low impact)

**Decision**: Treat as optional. Prompt assembly is typically much cheaper than DB/HTTP/LLM calls.

**If enabled**:
- Key: `prompt:{tenant}:{template_id}:{sha256(inputs)}`
- TTL: 5–15 minutes

### 5) LLM response caching (highest cost, highest risk)

**Key structure**:
- `llm:{tenant}:{user_id}:{deployment}:{temperature}:{max_tokens}:{response_format}:{sha256(messages+tools+settings)}`

**TTL defaults**:
- 1–5 minutes (short-lived), only when deterministic/explicitly cache-safe.

**Invalidation strategy**:
- Implicit via key versioning on prompt template/tool schema changes.

## Unified Cache Interface (Design Requirements)

**Required operations**:
- `get(key) -> Optional[bytes]`
- `set(key, value: bytes, ttl_seconds: int, tags: Optional[list[str]] = None)`
- `delete(key)`
- `get_or_set(key, ttl_seconds, factory)` with stampede protection (single-flight per key)

**Design notes**:
- Interface is byte-based so Redis support is a backend swap (encode/decode handled by typed wrappers).
- Namespaces provide default TTLs and capacity limits.
- Tenant/user scoping happens at key-building time (not optional).
- In-memory backend must be bounded (LRU + TTL eviction) to avoid unbounded memory growth.

## Existing Ad-hoc Caches to Consolidate

- JWKS cache in auth flow.
- Chat history short TTL cache.
- Research workflow in-memory state cache and per-run web search cache.
- External reference data caches (e.g., park lists).
- Note: OpenAI client factories already cache client objects (connection reuse) and are not response caches.
