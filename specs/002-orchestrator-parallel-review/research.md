# Research: Orchestrator Agent with Parallel Processing & Review

**Feature**: 002-orchestrator-parallel-review  
**Date**: 2025-12-28

## Goals

- Confirm the Microsoft Agent Framework (MAF) primitives to use for concurrency (ConcurrentBuilder), including how to:
  - Run participants concurrently
  - Stream progress events
  - Aggregate results
  - Handle failures/timeouts without custom asyncio coordination

## Key Decisions (to be filled)

### 1) ConcurrentBuilder integration approach
- Decision:
- Rationale:
- Notes / links:

### 2) Aggregation strategy
- Decision:
- Rationale:
- Notes:

### 3) Dependency ordering strategy
- Decision:
- Rationale:
- Notes:

### 4) Review Agent design
- Decision:
- Rationale:
- Notes:

### 5) Timeout + retry strategy
- Decision:
- Rationale:
- Notes:

### 6) Cosmos persistence strategy
- Decision:
- Rationale:
- Notes:

## Open Questions

- How should timeouts be enforced per task using framework-supported APIs?
- What event types are available from workflow streaming, and which ones should be persisted?
- What is the most compatible way to represent task dependencies without introducing a new folder structure?

## References

- MAF Concurrent Orchestrations: https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/orchestrations/concurrent
