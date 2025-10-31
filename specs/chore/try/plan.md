# Implementation Plan: Add Microsoft Agent Lightning Integration

**Branch**: `chore/try` | **Date**: 2025-10-30 | **Spec**: `specs/chore/try/spec.md`  
**Input**: Feature specification from `/specs/chore/try/spec.md`

## Summary

Add Microsoft Agent Lightning as an optimization layer on top of existing LangChain/LangGraph agents. Agent Lightning will wrap selected agents (starting with document QA workflow) to improve answer quality and token efficiency through reinforcement learning, prompt optimization, and supervised fine-tuning. This maintains existing orchestration while adding optimization capabilities. Migration will be gradual: Phase 1 (P1) focuses on wrapping the document QA agent to validate Agent Lightning; Phase 2 (P2) adds selective optimization to other agents and enhanced observability.

## Technical Context

**Language/Version**: Python 3.11 (same as current backend)

**Primary Dependencies**:
- New: `agentlightning>=0.1.0` (Agent Lightning SDK - optimization layer)
- Existing (UNCHANGED): FastAPI, LangChain, LangGraph, Azure OpenAI, Azure Search, Cosmos DB, structlog, OpenTelemetry

**Architecture**: Agent Lightning WRAPS existing LangChain/LangGraph agents
- LangGraph: Handles orchestration (unchanged)
- LangChain: Handles agent implementation (unchanged)
- Agent Lightning: Optimizes agent behavior (new, additive layer)

**Storage**: Cosmos DB (existing, no changes)

**Testing**: pytest (existing, will enhance)

**Target Platform**: Linux server (Azure Container Apps)

**Project Type**: Web API (FastAPI backend with agent optimization layer)

**Performance Goals**:
- Simple queries: p95 ≤ 2s (wrapper overhead negligible: ~50ms)
- Multi-agent queries: p95 ≤ 5s (optimization async, non-blocking)
- Concurrent workflows: ≥ 100

**Constraints**:
- Token limits (context window: auto-trim at 95k, no change)
- Agent timeouts (5-30s per agent, 10s workflow-level, no change)
- Cost optimization (Agent Lightning adds monitoring, not overhead)
- Zero-breaking-changes API requirement (wrapper is transparent)
- Multi-tenant isolation must be maintained (scope optimization per tenant)

**Scale/Scope**:
- 50-100 concurrent users
- Document corpus: 10k-50k documents
- Query types: document QA, multi-hop reasoning, synthesis
- Agents: 3 specialized agents (query planner, document analyzer, answer generator)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Principle I: Code Quality** ✅ PASSES
- All Agent Lightning code will pass ruff linting and mypy strict
- Peer review required before merge

**Principle II: Test-First Development** ✅ PASSES
- Tests written BEFORE implementation (TDD cycle)
- Minimum 75% coverage for core agent modules
- Integration + contract tests required

**Principle III: Type Safety** ✅ PASSES
- mypy strict mode on all agent modules
- Pydantic models for all contracts
- Full type annotations required

**Principle IV: User Experience Consistency** ⏭️ N/A
- Backend-only feature (no UI changes)
- API contracts remain unchanged

**Principle V: Performance & Observability** ✅ PASSES
- OpenTelemetry instrumentation on all workflows
- Prometheus metrics for latency, token usage, success rates
- Performance targets: 2s simple / 5s multi-agent

**Verdict**: ✅ **PASSES Constitution Check**

## Project Structure

### Documentation (this feature)

```text
specs/chore/try/
├── spec.md              # ✅ User stories, requirements
├── research.md          # ✅ Phase 0 research: decisions, rationale
├── plan.md              # ← This file (planning)
├── data-model.md        # Phase 1 output (entity definitions)
├── quickstart.md        # Phase 1 output (setup guide)
├── contracts/           # Phase 1 output (API contracts)
└── tasks.md             # Phase 2 output (task breakdown)
```

### Source Code

```text
api/
├── app/
│   ├── core/
│   │   ├── agent_lightning_config.py    # NEW: Agent Lightning init + wrapper factory
│   │   └── [existing]
│   ├── models/
│   │   ├── optimization_models.py       # NEW: Optimization metrics + config models
│   │   └── [existing]
│   ├── services/
│   │   ├── agent_wrapper_service.py         # NEW: Base wrapper for any agent
│   │   ├── optimization_service.py          # NEW: Optimization data collection
│   │   ├── document_qa_service.py           # MODIFIED: Wrap document QA agent
│   │   └── [existing, mostly unchanged]
│   └── routers/
│       ├── document_qa.py                   # UNCHANGED: API contracts identical
│       └── [existing]

tests/
├── contract/
│   ├── test_document_qa_api_contract.py     # NEW: Verify response schema identical
│   └── [existing]
├── integration/
│   ├── test_agent_wrapper_integration.py    # NEW: Wrapper works with LangGraph
│   ├── test_optimization_data_collection.py # NEW: Metrics collected correctly
│   └── [existing]
└── unit/
    ├── test_agent_wrapper.py                # NEW: Wrapper logic (75%+ coverage)
    ├── test_optimization_config.py          # NEW: Config schema validation
    ├── [existing]
```

## Phase Structure

### Phase 0: Research (✅ COMPLETE - research.md)
- [x] Resolve all NEEDS CLARIFICATION items
- [x] Finalize technology choices
- [x] Design orchestrator pattern
- [x] Plan migration strategy

### Phase 1: Design & Contracts (⏳ NEXT)
- [ ] Extract wrapper and optimization data models → data-model.md
- [ ] Generate API contracts (verify unchanged) → contracts/ directory
- [ ] Define wrapper interface specs and optimization config schema
- [ ] Create quickstart.md setup guide for Agent Lightning integration

**Output**: data-model.md, contracts/*, quickstart.md

### Phase 2: Tasks Breakdown (⏳ AFTER PHASE 1)
- [ ] Break down into implementation tasks
- [ ] Assign phases: Setup (deps) → Foundational (wrapper, metrics) → User Stories (wrap document QA, selective optimization)
- [ ] Create tasks.md with test-first ordering (tests FIRST per Constitution)

**Output**: tasks.md

### Phase 3+: Implementation
- Follows tasks.md phase-by-phase

## Key Technical Decisions

**Wrapper Pattern**: Agent Lightning wraps existing agents without code changes
- Existing agents continue working (zero modifications)
- Wrapper intercepts execution, collects metrics, applies optimizations
- Transparent to API clients (no response changes)
- Can disable optimization per-agent (configurable)

**Selective Optimization**: Start with one agent (document QA), expand incrementally
- Reduces risk (focused validation)
- Clear ROI measurement per agent
- Per-agent algorithm selection (RL for reasoning, Prompt Opt for search, SFT for generation)

**Testing Strategy**: Test-First (per Constitution II)
- Unit tests: Wrapper logic (75%+ coverage)
- Integration tests: Wrapper + LangGraph compatibility
- Contract tests: API backward compatibility (100%)
- Optimization tests: Metrics collection, ROI calculation

## Success Criteria

1. ✅ Agent Lightning successfully wraps and optimizes existing LangGraph agents
2. ✅ All API contracts remain unchanged (backward compatible, zero breaking changes)
3. ✅ Wrapper overhead is negligible (< 50ms latency increase)
4. ✅ Performance meets targets (p95: 2s simple, 5s multi-agent, unchanged)
5. ✅ Optimization metrics are collected and observable (traces, logs, metrics)
6. ✅ Selective optimization per agent works correctly
7. ✅ Error handling is robust (wrapper failures don't break underlying agent)
8. ✅ Code coverage ≥ 75% for wrapper/optimization modules
9. ✅ Zero breaking changes to existing API
10. ✅ All code passes ruff + mypy strict
11. ✅ Tests pass before implementation (TDD)
12. ✅ Multi-tenant isolation preserved in optimization

## Next Steps

1. ✅ Phase 0 research complete (research.md)
2. ⏳ Phase 1: Create data models and API contracts
3. ⏳ Phase 2: Create tasks breakdown (tasks.md)
4. ⏳ Phase 3+: Implementation per tasks.md

**Status**: ✅ Phase 0 Complete - Ready for Phase 1

**Branch**: chore/try  
**IMPL_PLAN**: specs/chore/try/plan.md  
**SPECS_DIR**: specs/chore/try/

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
