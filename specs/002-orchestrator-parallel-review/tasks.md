---
description: "Actionable task list for 002-orchestrator-parallel-review"
---

# Tasks: Orchestrator Agent with Parallel Processing & Review

**Input**: Design documents from `/specs/002-orchestrator-parallel-review/` (plan.md, spec.md)

**Notes**:
- No new top-level folder structure is introduced; changes are within existing `api-ms-agent/app/...`.
- Tests are included because the specification has mandatory user scenarios/testing and the plan calls for test-first implementation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US#]**: Which user story this task belongs to
- Every task includes an exact file path

---

## Phase 1: Setup (Shared Documentation & Contracts)

- [x] T001 [P] Create research notes scaffold in specs/002-orchestrator-parallel-review/research.md
- [x] T002 [P] Create data model doc scaffold in specs/002-orchestrator-parallel-review/data-model.md
- [x] T003 [P] Create developer quickstart with local run + test steps in specs/002-orchestrator-parallel-review/quickstart.md
- [x] T004 [P] Add request schema contract in specs/002-orchestrator-parallel-review/contracts/orchestration-request.json
- [x] T005 [P] Add response schema contract in specs/002-orchestrator-parallel-review/contracts/orchestration-response.json
- [x] T006 [P] Add review criteria schema contract in specs/002-orchestrator-parallel-review/contracts/review-criteria.json
- [x] T007 Update plan references in specs/002-orchestrator-parallel-review/plan.md if any remaining wording implies a new module tree

---

## Phase 2: Foundational (Blocking Prerequisites)

- [ ] T008 Add orchestration-related settings (timeouts, retries, limits, reject action) in api-ms-agent/app/config.py
- [ ] T009 Define Pydantic models for orchestration + review types in api-ms-agent/app/models/orchestration.py
- [ ] T010 [P] Export/attach orchestration models from api-ms-agent/app/models/__init__.py (or document intentional non-export pattern)
- [ ] T011 Extend Cosmos container provisioning for review/orchestration persistence in api-ms-agent/app/services/cosmos_db_service.py
- [ ] T012 Add Cosmos persistence helpers for review criteria and review decisions in api-ms-agent/app/services/cosmos_db_service.py
- [ ] T013 Implement criteria load/cache service in api-ms-agent/app/services/review_criteria_service.py
- [ ] T014 Implement sensitive data detection + redaction primitives in api-ms-agent/app/services/sensitive_data_detector.py
- [ ] T015 Implement Review Agent service wrapper (MAF ChatAgent + tools) in api-ms-agent/app/services/review_agent.py
- [ ] T016 Add orchestration router skeleton and request/response models in api-ms-agent/app/routers/orchestration.py
- [ ] T017 Wire orchestration router into api-ms-agent/app/routers/__init__.py

**Checkpoint**: Foundation ready (models + persistence + review service skeleton + router skeleton).

---

## Phase 3: User Story 1 - Execute Multiple Tasks in Parallel (Priority: P1) 🎯 MVP

**Goal**: Execute multiple orchestration tasks concurrently (vs sequential), respecting dependencies and isolating failures/timeouts.

**Independent Test**: Submit an orchestration request with 3 independent tasks and verify total time is close to the longest task, and that per-task status/results are returned.

### Tests for User Story 1 (test-first)

- [ ] T018 [P] [US1] Add unit test for dependency ordering (DAG) in api-ms-agent/tests/test_orchestration_dependencies.py
- [ ] T019 [P] [US1] Add unit test for concurrency timing (3 tasks, longest dominates) in api-ms-agent/tests/test_orchestration_parallel_timing.py
- [ ] T020 [P] [US1] Add unit test for failure isolation (one fails, others succeed) in api-ms-agent/tests/test_orchestration_failure_isolation.py
- [ ] T021 [P] [US1] Add unit test for retry + exponential backoff behavior in api-ms-agent/tests/test_orchestration_retries.py

### Implementation for User Story 1

- [ ] T022 [US1] Add orchestration request parsing + validation in api-ms-agent/app/routers/orchestration.py
- [ ] T023 [US1] Add orchestration entrypoint method (e.g., process_orchestration) in api-ms-agent/app/services/orchestrator_agent.py
- [ ] T024 [US1] Implement dependency resolution (topological / wave execution) in api-ms-agent/app/services/orchestrator_agent.py
- [ ] T025 [US1] Implement parallel wave execution using agent_framework ConcurrentBuilder (no asyncio.gather) in api-ms-agent/app/services/orchestrator_agent.py
- [ ] T026 [US1] Implement per-task timeout handling (task isolation) using supported Agent Framework APIs in api-ms-agent/app/services/orchestrator_agent.py
- [ ] T027 [US1] Implement retry policy (defaults: 3 retries, exponential backoff) in api-ms-agent/app/services/orchestrator_agent.py
- [ ] T028 [US1] Persist orchestration metadata + per-task results (including failures) in api-ms-agent/app/services/cosmos_db_service.py
- [ ] T029 [US1] Emit structured logs per task (id, start/end, status, duration, attempt) in api-ms-agent/app/services/orchestrator_agent.py

**Checkpoint**: US1 complete — parallel execution works, dependency ordering works, failures/timeouts are isolated, and per-task results are returned.

---

## Phase 4: User Story 2 - Review Agent Validates Orchestration Responses (Priority: P1)

**Goal**: Run a dedicated review step on the aggregated orchestration output before returning to the user; reject with actionable feedback when invalid.

**Independent Test**: Provide a response missing required sections and verify review rejects with specific feedback; provide a valid response and verify approval.

### Tests for User Story 2 (test-first)

- [ ] T030 [P] [US2] Add unit test for “approve” path (valid response) in api-ms-agent/tests/test_review_agent_approve.py
- [ ] T031 [P] [US2] Add unit test for “reject” path with actionable feedback in api-ms-agent/tests/test_review_agent_reject.py
- [ ] T032 [P] [US2] Add unit test for PII redaction behavior in api-ms-agent/tests/test_review_agent_redaction.py
- [ ] T033 [P] [US2] Add unit test for reject action handling (retry/escalate/error) in api-ms-agent/tests/test_review_reject_actions.py

### Implementation for User Story 2

- [ ] T034 [US2] Define ReviewCriteria + ReviewDecision models used by the review flow in api-ms-agent/app/models/orchestration.py
- [ ] T035 [US2] Implement ReviewAgent.review(...) orchestration (criteria load, validate, redact) in api-ms-agent/app/services/review_agent.py
- [ ] T036 [US2] Integrate review step into orchestration response flow in api-ms-agent/app/services/orchestrator_agent.py
- [ ] T037 [US2] Implement configurable reject actions (retry / escalate / error) in api-ms-agent/app/services/orchestrator_agent.py
- [ ] T038 [US2] Persist review decisions + feedback in api-ms-agent/app/services/cosmos_db_service.py
- [ ] T039 [US2] Ensure response always includes source/trace info for review (criteria id, decision id) in api-ms-agent/app/routers/orchestration.py

**Checkpoint**: US2 complete — review gate runs on every orchestration response and blocks/approves correctly with actionable feedback.

---

## Phase 5: User Story 3 - Monitor Parallel Execution Progress (Priority: P2)

**Goal**: Expose task-level status and timing so operators/users can observe progress.

**Independent Test**: Submit a long-running orchestration and verify status endpoint/logs show per-task status transitions and timestamps.

### Tests for User Story 3

- [ ] T040 [P] [US3] Add unit test for status model + transitions in api-ms-agent/tests/test_orchestration_status_transitions.py
- [ ] T041 [P] [US3] Add API-level test for status endpoint shape in api-ms-agent/tests/test_orchestration_status_api.py

### Implementation for User Story 3

- [ ] T042 [US3] Add task status fields (pending/running/success/failed/timeout) and timestamps to models in api-ms-agent/app/models/orchestration.py
- [ ] T043 [US3] Persist and update task status during execution in api-ms-agent/app/services/cosmos_db_service.py
- [ ] T044 [US3] Implement GET status endpoint (by orchestration_id) in api-ms-agent/app/routers/orchestration.py
- [ ] T045 [US3] Add structured logging fields for orchestration_id + task_id in api-ms-agent/app/services/orchestrator_agent.py
- [ ] T046 [US3] Add basic orchestration metrics helpers (timings, counts) in api-ms-agent/app/observability/orchestration_metrics.py

**Checkpoint**: US3 complete — status visibility exists via endpoint and logs/metrics.

---

## Phase 6: User Story 4 - Configure Review Agent Criteria (Priority: P2)

**Goal**: Allow criteria to be configured without code changes (stored in Cosmos, cached, effective within ~1 minute).

**Independent Test**: Update criteria, run an orchestration that violates the new rule, verify review rejects using the updated config.

### Tests for User Story 4

- [ ] T047 [P] [US4] Add unit test for criteria caching + TTL behavior in api-ms-agent/tests/test_review_criteria_cache.py
- [ ] T048 [P] [US4] Add integration test ensuring criteria updates take effect quickly in api-ms-agent/tests/test_review_criteria_update_effect.py

### Implementation for User Story 4

- [ ] T049 [US4] Define ReviewCriteria storage shape + partition key strategy in api-ms-agent/app/services/review_criteria_service.py
- [ ] T050 [US4] Implement get/update criteria methods (Cosmos-backed + cache) in api-ms-agent/app/services/review_criteria_service.py
- [ ] T051 [US4] Add minimal admin API endpoints to read/update criteria in api-ms-agent/app/routers/orchestration.py
- [ ] T052 [US4] Ensure ReviewAgent loads criteria by id and falls back to defaults when missing in api-ms-agent/app/services/review_agent.py

**Checkpoint**: US4 complete — criteria can be changed without redeploy and is enforced by review.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T053 [P] Document orchestration + review flows and sample requests in specs/002-orchestrator-parallel-review/quickstart.md
- [ ] T054 [P] Add contract examples aligned to implemented API in specs/002-orchestrator-parallel-review/contracts/orchestration-request.json
- [ ] T055 [P] Add contract examples aligned to implemented API in specs/002-orchestrator-parallel-review/contracts/orchestration-response.json
- [ ] T056 [P] Add contract examples aligned to implemented API in specs/002-orchestrator-parallel-review/contracts/review-criteria.json
- [ ] T057 Add router registration notes (paths, tags) in api-ms-agent/app/routers/__init__.py
- [ ] T058 Add hardening: size limits and truncation for large task outputs in api-ms-agent/app/services/orchestrator_agent.py
- [ ] T059 Add hardening: review agent failure handling (fallback + error) in api-ms-agent/app/services/orchestrator_agent.py
- [ ] T060 Run and document local verification steps in specs/002-orchestrator-parallel-review/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup completion — blocks all user stories
- **US1 + US2 (Phase 3–4)**: Depend on Foundational — can proceed in parallel after Phase 2
- **US3 + US4 (Phase 5–6)**: Depend on US1/US2 core flow being available
- **Polish (Phase 7)**: Depends on desired user stories being complete

### User Story Dependencies

- **[US1] Parallel execution (P1)** → foundational for everything else
- **[US2] Review gate (P1)** → required before returning orchestrated results
- **[US3] Progress monitoring (P2)** → builds on orchestration persistence/logging
- **[US4] Criteria configuration (P2)** → builds on Cosmos persistence + review agent integration

---

## Parallel Execution Examples

### User Story 1 (parallelizable tasks)

- T018 + T019 + T020 + T021 (tests) can be developed in parallel
- After models/config are ready: T022 (router parsing) and T023–T027 (service implementation) can be split among contributors

### User Story 2 (parallelizable tasks)

- T030–T033 (tests) can be developed in parallel
- T035 (review agent) and T037 (reject actions) can be developed in parallel once models exist

### User Story 3 (parallelizable tasks)

- T040 (status transitions) and T041 (status API test) can be developed in parallel

### User Story 4 (parallelizable tasks)

- T047 and T048 can be developed in parallel
- T050 and T051 can be developed in parallel once the service shape is established

---

## Implementation Strategy (MVP)

- MVP scope is **US1 + US2** first: parallel execution + review gate.
- Then deliver **US3 + US4** for production readiness (observability + configurability).
