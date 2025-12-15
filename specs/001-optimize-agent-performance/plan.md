# Implementation Plan: Agent Performance Optimization (Unified Caching)

**Branch**: `001-optimize-agent-performance` | **Date**: 2025-12-14 | **Spec**: [specs/001-optimize-agent-performance/spec.md](specs/001-optimize-agent-performance/spec.md)
**Input**: Feature specification from `/specs/001-optimize-agent-performance/spec.md` + note: keep functionality the same; focus purely on performance via caching.

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Improve end-to-end agent response time and stability by introducing a single, unified caching interface with an in-memory backend, and applying it consistently to:

- Outbound API calls (read-only / safe-to-cache responses)
- Database reads (safe read paths with short TTLs)
- Prompt rendering (template expansion / prompt assembly)
- LLM response caching (only when safe to avoid changing semantics)

All caching logic is abstracted behind a unified interface so Redis can be introduced later by adding a new backend implementation without changing call sites.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.13 (api-ms-agent) + TypeScript (frontend)  
**Primary Dependencies**: FastAPI, httpx, openai (Azure), azure-cosmos, agent-framework, structlog  
**Storage**: Azure Cosmos DB (chat history, metadata, workflow persistence); Azure Search / Document Intelligence as dependencies  
**Testing**: pytest, pytest-asyncio, pytest-cov (backend); vitest/playwright (frontend)  
**Target Platform**: Linux containers (local Docker + Azure hosting)  
**Project Type**: Web application (backend service `api-ms-agent/` + `frontend/`)  
**Performance Goals**: Reduce median agent response time by ≥30%; keep tail latencies predictable; reduce redundant outbound calls  
**Constraints**: Keep user-visible behavior the same; multi-tenant safety (no cross-tenant cache leakage); bounded memory; cache keys must include relevant request context; in-memory now but Redis-ready later  
**Scale/Scope**: Multi-user chat sessions; mixed workloads (chat, retrieval, workflow research); performance improvements targeted at repeated work (API/DB/LLM/prompt)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Gates derived from `.specify/memory/constitution.md`:

- Code Quality: ruff linting must pass; imports sorted; keep style consistent.
- Testing: add/adjust tests for caching behavior (hit/miss, TTL, tenant isolation) and ensure existing tests continue to pass.
- Type Safety: keep types strict; cache interface and key builders must be fully typed.
- Performance & Observability: performance improvements must be measurable; emit structured logs for cache hit/miss and latency; do not introduce uncontrolled memory growth.

Notes on performance targets:

- Constitution’s "≤500ms p95 for standard queries" is treated as applying to non-LLM endpoints.
- Agent chat flows that include LLM calls use the feature spec’s end-to-end targets (e.g., p95 ≤ 5s) while still optimizing internal overhead via caching.

## Project Structure

### Documentation (this feature)

```text
specs/001-optimize-agent-performance/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
api-ms-agent/
├── app/
│   ├── auth/
│   ├── core/                 # (planned) shared caching interface + in-memory backend
│   ├── middleware/
│   ├── routers/
│   └── services/
└── tests/

frontend/
└── src/

infra/

api/                          # DEPRECATED: do not use for this feature
```

**Structure Decision**: Web application. This feature applies to `api-ms-agent/` only. The `api/` service is deprecated and is excluded from analysis and changes.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |

## Phase 0: Outline & Research (Output: research.md)

Research questions to resolve before design:

1. What is safe-to-cache (and for how long) for each category (API, DB, prompt, LLM) without changing user-visible behavior?
2. What keying strategy prevents cross-tenant/user cache leakage?
3. How to prevent cache stampedes under concurrency (especially for LLM calls)?
4. Where are the highest-cost repeated calls in `api-ms-agent/` (hotspots) and where should caching be applied first?

## Phase 1: Design & Contracts (Outputs: data-model.md, contracts/, quickstart.md)

Design deliverables:

- A unified cache interface (typed) that supports TTL, namespacing, and atomic "get-or-set" patterns.
- An in-memory backend that is bounded (max entries and/or max bytes) with TTL eviction.
- A key builder strategy per cache type:
  - API cache keys: URL + method + normalized query + relevant headers + tenant context.
  - DB cache keys: query identifier + parameters + tenant/user context.
  - Prompt cache keys: prompt template identifier + rendered inputs + model id.
  - LLM response cache keys: model deployment + messages + tool definitions + deterministic parameters + tenant/user context.
- A contract delta: "no external API changes" (OpenAPI with empty/unchanged paths) since functionality remains the same.

## Phase 2: Planning (Stop after this phase)

High-level implementation sequence (detailed tasks will be generated by `/speckit.tasks`):

1. Introduce `app/core/cache` module in `api-ms-agent/` with the unified interface and in-memory backend.
2. Add cache key builders and a small policy layer (default TTLs, allow/deny list, tenant scoping).
3. Apply caching to:
   - Outbound API calls in the orchestrator tools
   - Cosmos DB read paths where safe
   - Prompt assembly
   - LLM responses only when deterministic/safe
4. Add tests for cache correctness (TTL, isolation, stampede control) and smoke tests for unaffected behavior.
5. Add structured logs/metrics-like events for hit/miss and latency per cache namespace.
