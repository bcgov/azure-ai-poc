# Contract: Cache Configuration

Caching is enabled by default only for low-risk categories (e.g., short-lived DB read caching). More sensitive caching (LLM responses) is opt-in.

## Configuration Sources

- Environment variables (preferred for deployment)
- Application settings module (defaults)

## Proposed Settings (defaults preserve current behavior)

- `CACHE_ENABLED` (bool, default true)
- `CACHE_BACKEND` (string, default `memory`)

Namespace policies (all optional overrides):
- `CACHE_DB_TTL_SECONDS` (int, default 30)
- `CACHE_HTTP_TTL_SECONDS` (int, default 900)
- `CACHE_LLM_TTL_SECONDS` (int, default 0; 0 means disabled)

Capacity limits:
- `CACHE_MAX_ENTRIES` (int, default 4096)
- `CACHE_MAX_BYTES` (int, optional)

## Safety Requirements

- Defaults must not cause cross-tenant leakage.
- Defaults must not change user-visible results.
- Settings must be safe to tune independently per deployment.
