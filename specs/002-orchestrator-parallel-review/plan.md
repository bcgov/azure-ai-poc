# Implementation Plan: Orchestrator Agent with Parallel Processing & Review

**Branch**: `002-orchestrator-parallel-review` | **Date**: 2025-12-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-orchestrator-parallel-review/spec.md`

## Summary

Upgrade the orchestrator agent in `api-ms-agent` to support concurrent task execution using Microsoft Agent Framework SDK's async primitives, with a specialized Review Agent that validates orchestration outputs, redacts sensitive information, and applies ethical AI safeguards. The Review Agent will be reusable across the application for all AI responses.

**Key Design Decisions**:
- Leverage **Microsoft Agent Framework SDK** exclusively for orchestration, task execution, and review agent logic
- Use **asyncio** for parallel task execution (built into Python 3.13)
- Implement Review Agent as a **specialized Tool/Agent** in MS Agent Framework with configurable validation rules
- Reuse Review Agent across the application via dependency injection
- Store review criteria in **Azure Cosmos DB** for runtime configurability without code changes

---

## Technical Context

**Language/Version**: Python 3.13  
**Primary Dependencies**: 
- `agent-framework>=1.0.0b251120` (Microsoft Agent Framework SDK)
- `fastapi>=0.122.0` (API framework)
- `httpx>=0.28.0` (async HTTP client)
- `azure-cosmos>=4.9.0` (review criteria storage + chat history)
- `openai>=2.8.1` (Azure OpenAI integration for review agent inference)
- `structlog>=25.5.0` (structured logging)
- `pydantic-settings>=2.12.0` (configuration management)

**Storage**: Azure Cosmos DB for:
- Review criteria configuration (ReviewCriteria collection)
- Orchestration execution metadata (OrchestrationMetadata collection)
- Review agent decisions and feedback (ReviewDecisions collection)

**Testing**: pytest + pytest-asyncio with:
- Unit tests for orchestrator logic (>=75% coverage for `app/core/orchestrator/`)
- Integration tests for parallel task execution
- Contract tests for orchestration API endpoints
- Review agent validation tests

**Target Platform**: Linux server (FastAPI + Azure Container Apps)  
**Performance Goals**: 
- 3 parallel tasks complete in ≤3s (120% of longest task, ~1s overhead for orchestration)
- p95 review agent inference time: ≤500ms
- Support 10+ concurrent orchestration workflows

**Constraints**:
- p95 orchestration latency: ≤2s (including review)
- Review agent must not add >500ms to total workflow time
- Memory usage ≤100MB per orchestration workflow
- Sensitive data redaction must be 100% comprehensive

**Scale/Scope**: 
- Multi-tenant orchestration workflows
- 2-10 parallel tasks per orchestration request
- 100+ concurrent workflows supported

---

## Constitution Check

✅ **Code Quality**: Will use Microsoft Agent Framework SDK (no custom orchestration logic); all code will pass ruff + mypy strict

✅ **Test-First**: Tests written before implementation; target >=75% coverage for orchestrator core modules

✅ **Type Safety**: All code uses Pydantic models for orchestration requests/responses; full mypy strict mode compliance

✅ **Security & Azure Best Practices**: 
- No hardcoded secrets; all credentials via Azure Key Vault
- Private endpoints for Azure Cosmos DB and Azure OpenAI
- Structured logging with PII/sensitive data redaction via Review Agent
- All infrastructure via Terraform (IaC only)

✅ **Performance & Observability**:
- Structured logging via structlog for all task execution
- Metrics collection for task times, success/failure rates
- OpenTelemetry instrumentation planned (OTLP exporter)
- Critical paths: orchestration execution, review agent validation

---

## Project Structure

### Documentation (this feature)

```text
specs/002-orchestrator-parallel-review/
├── spec.md                          # Feature specification
├── plan.md                          # This file
├── research.md                      # [Phase 0] Technical research & decisions
├── data-model.md                    # [Phase 1] Entity models & relationships
├── quickstart.md                    # [Phase 1] Developer quickstart guide
├── checklists/
│   └── requirements.md              # Quality gate checklist
└── contracts/
    ├── orchestration-request.json   # [Phase 1] OpenAPI schema
    ├── orchestration-response.json  # [Phase 1] OpenAPI schema
    └── review-criteria.json         # [Phase 1] Review criteria schema
```

### Source Code Structure (api-ms-agent)

```text
api-ms-agent/
├── app/
│   ├── core/
│   │   ├── __init__.py
│   │   └── orchestrator/                      # NEW MODULE: Phase 1
│   │       ├── __init__.py
│   │       ├── models.py                      # Pydantic models for orchestration
│   │       ├── executor.py                    # Parallel task executor (MS Agent Framework)
│   │       ├── review_agent.py                # Review agent using MS Agent Framework
│   │       └── coordinator.py                 # Orchestration coordinator (main logic)
│   │
│   ├── services/
│   │   ├── orchestration_service.py           # [MODIFY] Public API service
│   │   ├── review_criteria_service.py         # [NEW] Load/cache review criteria from Cosmos DB
│   │   └── sensitive_data_detector.py         # [NEW] PII/sensitive data patterns
│   │
│   ├── routers/
│   │   ├── orchestration.py                   # [NEW] REST endpoints for orchestration
│   │   └── [existing routers unchanged]
│   │
│   ├── models/
│   │   ├── orchestration.py                   # [NEW] Cosmos DB models for orchestration
│   │   └── [existing models unchanged]
│   │
│   └── [other existing modules unchanged]
│
├── tests/
│   ├── unit/
│   │   └── orchestrator/                      # [NEW] Unit tests for orchestrator
│   │       ├── test_executor.py
│   │       ├── test_review_agent.py
│   │       ├── test_coordinator.py
│   │       └── test_models.py
│   │
│   ├── integration/
│   │   └── test_orchestration_flow.py         # [NEW] End-to-end integration tests
│   │
│   ├── contract/
│   │   └── test_orchestration_api.py          # [NEW] API contract tests
│   │
│   └── [existing tests unchanged]
│
├── pyproject.toml                             # [NO CHANGES] Use existing dependencies
├── main.py                                    # [MODIFY] Register orchestration router
└── [other files unchanged]
```

**Structure Decision**: Modular extension to existing `api-ms-agent` codebase. New `app/core/orchestrator/` module encapsulates all parallel execution logic using MS Agent Framework SDK. Review Agent is implemented as a standalone agent that can be injected as a dependency. Separation of concerns: executor (task running), coordinator (workflow management), review_agent (validation + redaction).

---

## Complexity Tracking

No violations of constitution principles. Design is intentionally simple:
- ✅ No custom async orchestration code (use MS Agent Framework)
- ✅ No custom task scheduling (use MS Agent Framework async primitives)
- ✅ No custom agent logic (MS Agent Framework agents for orchestration + review)
- ✅ Configurable review criteria via Cosmos DB (no code changes needed)

---

## Phase 0: Research & Technical Decisions

**Output**: `research.md` with decisions on:
1. Microsoft Agent Framework SDK async patterns for parallel execution
2. Review agent design using MS Agent Framework tools/agents
3. Sensitive data detection patterns for PII redaction
4. Cosmos DB schema for review criteria and orchestration metadata
5. Integration with existing `api-ms-agent` architecture

**Research Tasks**:
- [ ] Document MS Agent Framework SDK async execution patterns and best practices
- [ ] Design review agent as a MS Agent Framework Agent with tools (validation tools, redaction tools)
- [ ] Identify PII/sensitive data patterns (SSN, credit card, health info, personal identifiers)
- [ ] Design Cosmos DB collections for review criteria (configurable without code)
- [ ] Verify compatibility with existing authentication, logging, observability in api-ms-agent

**Gate**: All research questions answered, technical approach aligned with MS Agent Framework patterns

---

## Phase 1: Design & Contracts

### 1.1 Data Model (`data-model.md`)

**Entities**:

```
OrchestrationRequest
├── request_id: UUID
├── tenant_id: str
├── tasks: List[Task]
├── dependencies: Dict[str, List[str]]    # task_id -> [prerequisite_task_ids]
├── review_criteria_id: str                # reference to ReviewCriteria in Cosmos DB
├── timeout_per_task: int                  # seconds
├── created_at: datetime
└── created_by: str

Task
├── task_id: str
├── agent_name: str                       # name of MS Agent Framework agent to execute
├── input_params: Dict[str, Any]
├── timeout: int
├── retry_config: RetryConfig
└── expected_output_schema: Dict          # for validation

TaskResult
├── task_id: str
├── status: "PENDING" | "RUNNING" | "SUCCESS" | "FAILED" | "TIMEOUT"
├── output: Any
├── error: Optional[str]
├── execution_time_ms: int
├── started_at: datetime
├── completed_at: datetime
└── retry_count: int

OrchestrationResult
├── orchestration_id: UUID
├── tenant_id: str
├── request_id: UUID
├── task_results: Dict[str, TaskResult]
├── execution_timeline: ExecutionTimeline
├── review_decision: ReviewDecision
├── total_execution_time_ms: int
└── completed_at: datetime

ReviewCriteria (stored in Cosmos DB)
├── criteria_id: str
├── tenant_id: str
├── required_sections: List[str]
├── quality_thresholds: Dict[str, float]
├── policy_rules: List[PolicyRule]
├── custom_validation_prompts: List[str]
├── enabled: bool
├── created_at: datetime
├── updated_at: datetime
└── version: int

ReviewDecision
├── decision_id: UUID
├── orchestration_id: UUID
├── status: "APPROVED" | "REJECTED"
├── confidence_score: float
├── issues_found: List[ValidationIssue]
├── redacted_result: Dict[str, Any]      # result with PII/sensitive data redacted
├── feedback: str                         # actionable guidance if rejected
├── reviewed_at: datetime
└── review_model: str                     # which model performed the review

ValidationIssue
├── issue_type: str                       # "missing_section" | "inconsistency" | "policy_violation" | "quality_threshold_not_met"
├── severity: "CRITICAL" | "MAJOR" | "MINOR"
├── description: str
├── affected_section: Optional[str]
└── remediation_guidance: str

RetryConfig
├── enabled: bool
├── max_retries: int                     # default 3
├── backoff_strategy: "exponential" | "linear"
├── initial_backoff_ms: int              # default 1000
└── max_backoff_ms: int                  # default 30000

ExecutionTimeline
├── workflow_started_at: datetime
├── workflow_completed_at: datetime
├── task_timings: Dict[str, TaskTiming]
└── total_duration_ms: int

TaskTiming
├── task_id: str
├── queued_at: datetime
├── started_at: datetime
├── completed_at: datetime
└── duration_ms: int
```

### 1.2 API Contracts (`contracts/`)

**Endpoint 1: Submit Orchestration Request**
```
POST /api/v1/orchestration/submit
Content-Type: application/json

Request:
{
  "tenant_id": "string",
  "tasks": [
    {
      "task_id": "string",
      "agent_name": "string",          # MS Agent Framework agent name
      "input_params": {},
      "timeout": 30
    }
  ],
  "dependencies": {
    "task_2": ["task_1"],              # task_2 depends on task_1
    "task_3": ["task_1", "task_2"]
  },
  "review_criteria_id": "string",
  "timeout_per_task": 30
}

Response (202 Accepted):
{
  "orchestration_id": "string (UUID)",
  "status": "SUBMITTED",
  "estimated_completion_ms": 5000
}
```

**Endpoint 2: Get Orchestration Status**
```
GET /api/v1/orchestration/{orchestration_id}

Response:
{
  "orchestration_id": "string",
  "request_id": "string",
  "status": "SUBMITTED" | "EXECUTING" | "COMPLETED" | "FAILED",
  "task_results": {
    "task_1": {
      "status": "SUCCESS",
      "execution_time_ms": 2500,
      "output": {}
    },
    ...
  },
  "review_decision": {
    "status": "APPROVED",
    "confidence_score": 0.97,
    "redacted_result": {}
  },
  "total_execution_time_ms": 3000,
  "completed_at": "ISO8601"
}
```

**Endpoint 3: Configure Review Criteria**
```
POST /api/v1/review-criteria
Content-Type: application/json

Request:
{
  "tenant_id": "string",
  "required_sections": ["summary", "details", "recommendations"],
  "quality_thresholds": {
    "min_confidence": 0.85,
    "max_hallucination_risk": 0.1
  },
  "policy_rules": [
    {
      "rule_type": "redact_pii",
      "pattern_type": "ssn|credit_card|health_info"
    },
    {
      "rule_type": "ethical_safeguard",
      "check": "no_discriminatory_content"
    }
  ],
  "custom_validation_prompts": [
    "Does the response contain accurate citations?",
    "Are there any contradictions within the response?"
  ]
}

Response:
{
  "criteria_id": "string",
  "status": "CREATED",
  "version": 1
}
```

**Endpoint 4: Get Review Criteria**
```
GET /api/v1/review-criteria/{criteria_id}

Response:
{
  "criteria_id": "string",
  "tenant_id": "string",
  "required_sections": [...],
  "quality_thresholds": {...},
  "policy_rules": [...],
  "enabled": true,
  "version": 1
}
```

### 1.3 Quickstart Guide (`quickstart.md`)

Developers will be able to:
1. Create an orchestration request with multiple tasks
2. Submit via REST API
3. Poll for status with automatic retry
4. Receive approved response with sensitive data redacted
5. Configure review criteria via Cosmos DB without code changes

Example workflow:
```python
# No new code needed! Uses existing HTTP client and models
import httpx

async with httpx.AsyncClient() as client:
    # Submit orchestration request
    response = await client.post(
        "http://api-ms-agent/api/v1/orchestration/submit",
        json={
            "tenant_id": "tenant-123",
            "tasks": [
                {"task_id": "task_1", "agent_name": "document_analyzer", ...},
                {"task_id": "task_2", "agent_name": "sentiment_analyzer", ...}
            ]
        }
    )
    orchestration_id = response.json()["orchestration_id"]
    
    # Poll for completion (automatic review happens during execution)
    result = await client.get(
        f"http://api-ms-agent/api/v1/orchestration/{orchestration_id}"
    )
    # Result already has PII redacted by review agent!
```

### 1.4 Update Agent Context

Run `.specify/scripts/powershell/update-agent-context.ps1 -AgentType copilot` to document:
- New `app/core/orchestrator/` module with MS Agent Framework usage
- Review Agent pattern for sensitive data redaction
- Reusable review agent across application

---

## Phase 2: Implementation Tasks (Phase 0-1 deliverables must be complete)

**Phase 2 will be generated by `/speckit.tasks` command**

### Phase 2.1: Foundation & Setup (Blocking)
- [ ] Create orchestrator module structure
- [ ] Define Pydantic models for orchestration requests/responses
- [ ] Set up Cosmos DB collections for review criteria and metadata
- [ ] Implement review criteria caching service

### Phase 2.2: Core Orchestrator (Blocking for Phase 2.3)
- [ ] Implement TaskExecutor using MS Agent Framework async agents
- [ ] Implement dependency resolution and task ordering
- [ ] Implement parallel task execution with asyncio
- [ ] Implement timeout handling and task isolation

### Phase 2.3: Review Agent (Blocking for Phase 2.4)
- [ ] Implement ReviewAgent using MS Agent Framework agents/tools
- [ ] Implement sensitive data detection and redaction tools
- [ ] Implement validation tools (sections, consistency, thresholds)
- [ ] Implement ethical AI safeguards tools (bias, discrimination, harm checks)
- [ ] Test review agent across sample responses

### Phase 2.4: Integration & API
- [ ] Create orchestration service (orchestration_service.py)
- [ ] Create REST endpoints (routers/orchestration.py)
- [ ] Integrate with existing auth and multi-tenancy
- [ ] Integration tests for complete workflows

### Phase 2.5: Observability & Production Hardening
- [ ] Structured logging for all orchestration steps
- [ ] Metrics collection (execution time, success rates, review decisions)
- [ ] Error handling and resilience testing
- [ ] Performance testing with 10+ concurrent workflows

---

## Implementation Approach: Microsoft Agent Framework SDK Only

### Why MS Agent Framework for Orchestration?

The Microsoft Agent Framework SDK (v1.0.0b251120+) provides:
- ✅ **Async Task Execution**: Native asyncio support for parallel task running
- ✅ **Agent Model**: Agents can represent orchestration tasks, coordinators, and the review agent
- ✅ **Tool System**: Tools for validation, redaction, and policy checks
- ✅ **State Management**: Built-in state for tracking orchestration progress
- ✅ **Event Model**: Event streaming for observability and progress updates
- ✅ **No Custom Code**: All orchestration logic via framework primitives

### Core Components (No Custom Code)

**1. TaskExecutor** (using MS Agent Framework agents)
```python
# Pseudo-code: actual implementation in orchestrator/executor.py

class TaskExecutor:
    """Executes tasks using MS Agent Framework agents"""
    
    async def execute_task(self, task: Task) -> TaskResult:
        # Load MS Agent Framework agent by name
        agent = await self.agent_registry.get_agent(task.agent_name)
        
        # Execute agent with timeout
        try:
            result = await asyncio.wait_for(
                agent.run(task.input_params),
                timeout=task.timeout
            )
            return TaskResult(status="SUCCESS", output=result)
        except asyncio.TimeoutError:
            return TaskResult(status="TIMEOUT", error="Task exceeded timeout")
        except Exception as e:
            return TaskResult(status="FAILED", error=str(e))
    
    async def execute_parallel(
        self, 
        tasks: List[Task],
        dependencies: Dict[str, List[str]]
    ) -> Dict[str, TaskResult]:
        """Execute tasks respecting dependency graph"""
        results = {}
        pending = set(t.task_id for t in tasks)
        
        while pending:
            # Find tasks with no unmet dependencies
            ready = [
                t for t in tasks 
                if t.task_id in pending 
                and all(dep in results for dep in dependencies.get(t.task_id, []))
            ]
            
            # Execute ready tasks in parallel
            task_futures = [
                self.execute_task(t) 
                for t in ready
            ]
            
            # Collect results as they complete
            for task, future in zip(ready, asyncio.as_completed(task_futures)):
                results[task.task_id] = await future
                pending.discard(task.task_id)
        
        return results
```

**2. ReviewAgent** (using MS Agent Framework with tools)
```python
# Pseudo-code: actual implementation in orchestrator/review_agent.py

class ReviewAgent:
    """Validates and redacts orchestration results"""
    
    def __init__(self, criteria_service, model_client):
        self.criteria_service = criteria_service
        self.model_client = model_client
        
        # Define tools for validation and redaction
        self.tools = [
            self._make_tool("validate_required_sections", self.validate_required_sections),
            self._make_tool("check_consistency", self.check_consistency),
            self._make_tool("validate_quality", self.validate_quality),
            self._make_tool("redact_sensitive_data", self.redact_sensitive_data),
            self._make_tool("check_ethical_safeguards", self.check_ethical_safeguards),
        ]
    
    async def review(
        self,
        result: Dict[str, Any],
        criteria_id: str
    ) -> ReviewDecision:
        """Run review agent on orchestration result"""
        
        criteria = await self.criteria_service.get_criteria(criteria_id)
        
        # Create MS Agent Framework agent with tools
        review_agent = Agent(
            name="review_agent",
            tools=self.tools,
            model=self.model_client
        )
        
        # Prompt agent to review result using tools
        prompt = f"""
        Review this orchestration result against criteria.
        
        Result: {json.dumps(result)}
        
        Required sections: {criteria.required_sections}
        Quality thresholds: {criteria.quality_thresholds}
        Policy rules: {criteria.policy_rules}
        
        Use the following tools in this order:
        1. validate_required_sections
        2. check_consistency
        3. validate_quality
        4. check_ethical_safeguards
        5. redact_sensitive_data
        
        Provide your final decision: APPROVED or REJECTED
        """
        
        response = await review_agent.run(prompt)
        
        # Parse response and create ReviewDecision
        return ReviewDecision(
            status=response.decision,  # APPROVED or REJECTED
            issues_found=response.issues,
            redacted_result=response.redacted_data,
            feedback=response.feedback
        )
```

**3. Orchestrator Coordinator** (uses MS Agent Framework agents + executor)
```python
# Pseudo-code: actual implementation in orchestrator/coordinator.py

class OrchestrationCoordinator:
    """Orchestrates parallel task execution with review"""
    
    def __init__(self, executor: TaskExecutor, review_agent: ReviewAgent):
        self.executor = executor
        self.review_agent = review_agent
    
    async def orchestrate(
        self,
        request: OrchestrationRequest
    ) -> OrchestrationResult:
        """Execute orchestration with parallel tasks and review"""
        
        # Phase 1: Execute tasks in parallel
        task_results = await self.executor.execute_parallel(
            request.tasks,
            request.dependencies
        )
        
        # Phase 2: Combine results
        combined = self._combine_results(task_results)
        
        # Phase 3: Run review agent
        review_decision = await self.review_agent.review(
            combined,
            request.review_criteria_id
        )
        
        return OrchestrationResult(
            task_results=task_results,
            review_decision=review_decision,
            total_execution_time_ms=...
        )
```

---

## Testing Strategy

**Unit Tests** (75%+ coverage for orchestrator):
- TaskExecutor: test concurrent execution, timeout handling, error propagation
- ReviewAgent: test each validation tool, redaction accuracy, tool calling
- Coordinator: test dependency resolution, result combination

**Integration Tests**:
- End-to-end orchestration with real MS Agent Framework agents
- Review agent validation against real orchestration results
- Timeout and failure scenarios
- Cosmos DB criteria loading and caching

**Contract Tests**:
- API request/response validation
- Pydantic model validation
- Review criteria schema validation

---

## Observability & Monitoring

**Structured Logging** (via structlog):
```python
# Example: structured log for task execution
logger.info(
    "task_execution",
    task_id="task_1",
    status="SUCCESS",
    execution_time_ms=2500,
    agent_name="document_analyzer",
    tenant_id="tenant-123"
)

# Example: structured log for review decision
logger.info(
    "review_decision",
    orchestration_id="orch-456",
    status="APPROVED",
    confidence_score=0.97,
    redactions_applied=5,
    pii_patterns_found=["ssn", "credit_card"]
)
```

**Metrics**:
- `orchestration_execution_time_ms` (histogram)
- `task_execution_time_ms` (histogram by task_id)
- `review_agent_confidence_score` (histogram)
- `review_approval_rate` (counter)
- `task_failure_rate` (counter by task_id)
- `redaction_events` (counter by pattern_type)

**Alerts**:
- Orchestration p95 latency >2s
- Review agent confidence <0.85
- Task failure rate >5%
- Redaction failures (PII not properly masked)

---

## Security & Compliance

✅ **No Secrets in Code**: All credentials via Azure Key Vault  
✅ **PII Redaction**: Review agent redacts SSN, credit card, health info, personal identifiers  
✅ **Ethical AI**: Review agent checks for bias, discrimination, harmful content  
✅ **Multi-tenant**: Request/response isolation via tenant_id  
✅ **Audit Trail**: All review decisions logged to Cosmos DB  
✅ **Type Safety**: Full mypy strict mode compliance  

---

## Success Metrics & Gates

**Phase 1 Gate** (before Phase 2 starts):
- ✅ All research questions answered in research.md
- ✅ Data model and API contracts defined
- ✅ MS Agent Framework usage patterns documented
- ✅ Quickstart guide created

**Phase 2 Gate** (before merging to main):
- ✅ 75%+ coverage for orchestrator module
- ✅ All functional requirements tested
- ✅ Success criteria validated (40%+ latency reduction, 95%+ review accuracy)
- ✅ Security review approved (PII redaction verified)
- ✅ Performance benchmarks met (p95 <2s for 3-task orchestration)

---

## Next Steps

1. **Phase 0**: Run research tasks and create `research.md`
2. **Phase 1**: Create data model, API contracts, and quickstart guide
3. **Phase 1.1**: Run `update-agent-context.ps1` to document in copilot instructions
4. **Phase 2**: Generate implementation tasks via `/speckit.tasks`
5. **Phase 2+**: Implement phases 2.1-2.5 in order (blocking dependencies enforced)

**Estimated Timeline**:
- Phase 0: 2 days (research)
- Phase 1: 2 days (design & contracts)
- Phase 2: 8-10 days (implementation across 5 phases)
- **Total: 2-3 weeks** for complete feature

**Parallel Review Agent Reuse**: Once Phase 2.3 completes, the Review Agent can be injected into other features (document analysis, chat responses, etc.) for application-wide PII redaction and ethical AI safeguards.
