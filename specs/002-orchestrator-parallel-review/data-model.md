# Data Model: Orchestrator Agent with Parallel Processing & Review

**Feature**: 002-orchestrator-parallel-review  
**Date**: 2025-12-28

## Overview

This document describes the logical entities for orchestration requests/results and the review step.

## Entities

### OrchestrationRequest

Core request object describing tasks, dependencies, timeouts, and review criteria.

Suggested fields:
- request_id: string (uuid)
- tenant_id: string
- tasks: Task[]
- dependencies: object (task_id -> task_id[])
- review_criteria_id: string
- timeout_per_task_seconds: number
- created_at: string (date-time)
- created_by: string

### Task

Suggested fields:
- task_id: string
- agent_name: string
- input_params: object
- timeout_seconds: number
- retry_config: RetryConfig
- expected_output_schema: object

### RetryConfig

Suggested fields:
- max_attempts: number (default 3)
- backoff_base_seconds: number
- backoff_max_seconds: number

### TaskResult

Suggested fields:
- task_id: string
- status: string (PENDING | RUNNING | SUCCESS | FAILED | TIMEOUT)
- output: any
- error: string | null
- started_at: string (date-time) | null
- completed_at: string (date-time) | null
- execution_time_ms: number
- retry_count: number

### ReviewCriteria

Suggested fields:
- id: string
- required_sections: string[]
- quality_thresholds: object
- policy_checks: object
- reject_action: string (retry | escalate | error)
- updated_at: string (date-time)

### ReviewDecision

Suggested fields:
- id: string
- orchestration_id: string
- approved: boolean
- feedback: string[]
- redactions_applied: number
- created_at: string (date-time)

## Storage Notes (Cosmos DB)

- Partitioning: prefer partition keys that align with existing patterns (e.g., user_id or tenant_id) depending on how the application queries orchestration and review records.
- TTL: review criteria should be cached in-process; persistence TTL is optional.
