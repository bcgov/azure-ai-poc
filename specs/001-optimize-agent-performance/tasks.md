# Tasks: Agent Performance Optimization (Unified Caching)

**Input**: Design documents from `specs/001-optimize-agent-performance/`  
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`  
**Scope**: `api-ms-agent/` only (`api/` is deprecated; do not modify).

## Format

`- [ ] T### [P?] [US#?] Description with file path`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the repository structure for unified caching (no behavioral changes yet).

- [x] T001 Create cache package structure in api-ms-agent/app/core/__init__.py and api-ms-agent/app/core/cache/__init__.py
- [x] T002 [P] Add typed cache interfaces skeleton in api-ms-agent/app/core/cache/types.py
- [x] T003 [P] Add cache key canonicalization helpers skeleton in api-ms-agent/app/core/cache/keys.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core cache implementation required before any user story work.

- [ ] T004 Implement in-memory TTL + bounded LRU backend in api-ms-agent/app/core/cache/memory_backend.py
- [ ] T005 Implement Cache facade + namespace policies in api-ms-agent/app/core/cache/cache.py
- [ ] T006 Implement single-flight (stampede protection) for get_or_set in api-ms-agent/app/core/cache/singleflight.py
- [ ] T007 Wire cache configuration defaults into api-ms-agent/app/config.py (safe defaults; LLM response caching disabled)
- [ ] T008 [P] Add structured cache logging helpers in api-ms-agent/app/core/cache/logging.py
- [ ] T009 Add a cache provider/factory in api-ms-agent/app/core/cache/provider.py (future Redis backend swap point)

**Checkpoint**: Foundation ready; user stories can begin.

---

## Phase 3: User Story 1 — Faster Agent Responses (Priority: P1) 🎯 MVP

**Goal**: Reduce redundant work safely via unified caching.

**Independent Test**: Run a representative interaction set twice and confirm the second run reduces redundant DB/HTTP calls (and improves latency) without changing responses.

### Implementation (US1)

- [ ] T010 [US1] Add safe Cosmos read caching wrappers in api-ms-agent/app/services/cosmos_db_service.py
- [ ] T011 [US1] Add targeted cache invalidation on Cosmos writes in api-ms-agent/app/services/cosmos_db_service.py
- [ ] T012 [US1] Add GET-only outbound HTTP caching in api-ms-agent/app/http_client.py
- [ ] T013 [US1] Apply caching to orchestrator tool calls in api-ms-agent/app/services/orchestrator_agent.py
- [ ] T014 [US1] Apply caching to workflow state reads in api-ms-agent/app/services/workflow_state_service.py
- [ ] T015 [US1] Add embedding caching in api-ms-agent/app/services/azure_openai_embedding_service.py
- [ ] T016 [US1] (Optional) Add prompt assembly caching in api-ms-agent/app/services/prompt_builder.py
- [ ] T017 [US1] (Opt-in) Add deterministic-only LLM response caching in api-ms-agent/app/services/azure_openai_chat_service.py

### Tests (required by FR-003)

- [ ] T018 [P] [US1] Unit tests for cache TTL + eviction in api-ms-agent/tests/test_cache_backend.py
- [ ] T019 [P] [US1] Unit tests for key scoping (tenant/user) in api-ms-agent/tests/test_cache_keys.py
- [ ] T020 [P] [US1] Unit tests for single-flight behavior in api-ms-agent/tests/test_cache_singleflight.py
- [ ] T021 [US1] Integration-style test for Cosmos read caching (mocked) in api-ms-agent/tests/test_cosmos_db_cache.py
- [ ] T022 [US1] Integration-style test for HTTP GET caching (mocked) in api-ms-agent/tests/test_http_cache.py

**Checkpoint**: US1 complete; caching yields measurable latency improvements on repeat calls.

---

## Phase 4: User Story 2 — Performance Visibility (Priority: P2)

**Goal**: Make performance improvements measurable and regressions detectable.

**Independent Test**: Run a known workload and confirm logs/metrics include latency distribution markers and cache hit/miss summaries.

### Implementation (US2)

- [ ] T023 [US2] Add request timing middleware instrumentation in api-ms-agent/app/middleware/performance_middleware.py
- [ ] T024 [US2] Emit structured perf logs (request id, path, outcome, duration) in api-ms-agent/app/logger.py
- [ ] T025 [P] [US2] Add cache hit/miss counters per namespace in api-ms-agent/app/core/cache/stats.py
- [ ] T026 [US2] Add a repeatable workload runner script in api-ms-agent/scripts/run_workload.py
- [ ] T027 [US2] Add baseline comparison report in api-ms-agent/scripts/compare_baseline.py

### Tests (required by FR-003/FR-004)

- [ ] T028 [P] [US2] Unit test perf middleware adds timing context in api-ms-agent/tests/test_performance_middleware.py
- [ ] T029 [US2] Snapshot-style test for baseline report format in api-ms-agent/tests/test_compare_baseline.py

**Checkpoint**: US2 complete; operators can validate improvements and detect regressions.

---

## Phase 5: User Story 3 — Predictable Performance Under Load (Priority: P3)

**Goal**: Maintain predictable behavior under concurrency and avoid stampedes/memory blowups.

**Independent Test**: Simulate concurrent identical requests and confirm single-flight limits redundant work and memory stays bounded.

### Implementation (US3)

- [ ] T030 [US3] Add per-namespace capacity tuning knobs in api-ms-agent/app/config.py
- [ ] T031 [US3] Add defensive timeouts around cached downstream calls in api-ms-agent/app/http_client.py
- [ ] T032 [US3] Add cache eviction observability (evict events) in api-ms-agent/app/core/cache/memory_backend.py
- [ ] T033 [US3] Add optional short negative caching for safe HTTP errors in api-ms-agent/app/http_client.py

### Tests (US3)

- [ ] T034 [P] [US3] Concurrency test for single-flight under load in api-ms-agent/tests/test_cache_concurrency.py
- [ ] T035 [US3] Load-style test harness (local) in api-ms-agent/tests/test_workload_smoke.py

**Checkpoint**: US3 complete; system remains stable and predictable under load.

---

## Phase 6: Polish & Cross-Cutting

- [ ] T036 [P] Update docs for cache settings in specs/001-optimize-agent-performance/contracts/cache-configuration.md
- [ ] T037 [P] Update quickstart validation steps in specs/001-optimize-agent-performance/quickstart.md
- [ ] T038 Run full test suite and fix regressions introduced by caching in api-ms-agent/tests/

---

## Dependencies & Execution Order

- Phase 1 (Setup) → Phase 2 (Foundational) → Phases 3–5 (User stories) → Phase 6 (Polish)
- US1 is the MVP and should land first.
- US2 can proceed after Phase 2 and independently of US1 (but benefits from cache stats).
- US3 depends on Phase 2 and is largely independent of US1/US2.

## Parallel Opportunities

- Phase 1: T002 and T003 can be done in parallel.
- Phase 2: T008 can be done in parallel with T004–T007.
- US1 tests T018–T020 can be done in parallel.
- US2: T025 can be done in parallel with T023–T024.
- US3: T034 can be done in parallel after T006 exists.

## Parallel Example: US1

- Implement DB caching in api-ms-agent/app/services/cosmos_db_service.py (T010, T011)
- Implement HTTP caching in api-ms-agent/app/http_client.py (T012)
- Implement cache backend tests in api-ms-agent/tests/test_cache_backend.py (T018)
