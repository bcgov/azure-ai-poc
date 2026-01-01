# Quickstart: Orchestrator Agent with Parallel Processing & Review

**Feature**: 002-orchestrator-parallel-review  
**Date**: 2025-12-28

## Goal

Add an orchestration API that can execute multiple tasks in parallel (with dependency ordering) and run a review gate before returning the final response.

## Prerequisites

- Python environment for api-ms-agent
- Azure OpenAI configuration (endpoint + key or managed identity)
- (Optional) Cosmos DB configuration for persistence

## Local setup

From repo root:

1) Sync dependencies
- Task: `uv sync - ms agent` (VS Code task)

2) Run the API
- Use the existing start approach for api-ms-agent (Docker or local run)

## Manual test flow

1) Call orchestration submit endpoint (to be implemented)
- POST /api/v1/orchestration/submit

2) Poll orchestration status
- GET /api/v1/orchestration/{orchestration_id}

## Expected behavior

- Independent tasks run concurrently; total time should be close to the longest task.
- Failures/timeouts are isolated to that task.
- A review step validates + redacts output before returning it.

## Troubleshooting

- If review criteria are missing: ensure defaults exist or the criteria service can fall back.
- If Cosmos is not configured: the system should still run, but persistence may be disabled.
