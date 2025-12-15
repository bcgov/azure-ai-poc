# Quickstart: Validate Caching Changes Locally

This feature is internal-only and should not change API schemas. The steps below focus on running `api-ms-agent/` and validating cache behavior via tests and logs.

## Prerequisites

- Python 3.13+
- `uv` installed
- A configured `.env` for `api-ms-agent/` (Azure OpenAI, Cosmos DB, Search, etc.)

## Install deps

From repo root:

- VS Code task: `uv sync - ms agent`

Or manually:

```bash
cd api-ms-agent
uv sync
```

## Run the service

```bash
cd api-ms-agent
uv run fastapi dev app/main.py --port 4000
```

## Run tests

```bash
cd api-ms-agent
uv run pytest
```

## Validate caching (manual smoke)

- Pick a safe, repeatable endpoint (e.g., document list or a deterministic read).
- Call it twice with the same authenticated user.
- Confirm logs show a cache miss then a cache hit for the same cache namespace/key shape.

Notes:
- Cache hit/miss logging must include namespace and latency, but must not log secrets.
- If you enable any LLM response caching for testing, it must be opt-in and restricted to deterministic settings.
