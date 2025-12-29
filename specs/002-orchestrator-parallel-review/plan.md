# Implementation Plan: Orchestrator Agent with Parallel Processing & Review

**Branch**: `002-orchestrator-parallel-review` | **Date**: 2025-12-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-orchestrator-parallel-review/spec.md`

## Summary

Upgrade the orchestrator agent in `api-ms-agent` to support concurrent task execution using **Microsoft Agent Framework's ConcurrentBuilder** (NO custom asyncio code), with a specialized Review Agent that validates orchestration outputs, redacts sensitive information, and applies ethical AI safeguards. The Review Agent will be reusable across the application for all AI responses.

**Key Design Decisions**:
- Leverage **Microsoft Agent Framework ConcurrentBuilder** exclusively for parallel orchestration (ZERO custom asyncio code)
- Implement Review Agent as a **specialized Agent with Tools** in MS Agent Framework with configurable validation rules
- Reuse Review Agent across the application via dependency injection
- Store review criteria in **Azure Cosmos DB** for runtime configurability without code changes
- Custom aggregator callback for result consolidation (framework handles all parallelism)

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
│   │       ├── workflow_builder.py            # ConcurrentBuilder orchestration (MS Agent Framework)
│   │       ├── review_agent.py                # Review agent using MS Agent Framework
│   │       └── orchestration_handler.py       # Orchestration request handler (main logic)
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

**Structure Decision**: Modular extension to existing `api-ms-agent` codebase. New `app/core/orchestrator/` module encapsulates all parallel execution logic using **MS Agent Framework's `ConcurrentBuilder`** (NO custom asyncio code). Review Agent is implemented as a standalone agent that can be injected as a dependency. Separation of concerns: workflow_builder (orchestration), review_agent (validation + redaction), orchestration_handler (API request processing).

---

## Complexity Tracking

No violations of constitution principles. Design is intentionally simple:
- ✅ No custom async orchestration code (use MS Agent Framework ConcurrentBuilder)
- ✅ No custom task scheduling (MS Agent Framework handles parallel execution natively)
- ✅ No custom agent logic (MS Agent Framework agents + tools for orchestration + review)
- ✅ Configurable review criteria via Cosmos DB (no code changes needed)

---

## Phase 0: Research & Technical Decisions

**Output**: `research.md` with decisions on:
1. MS Agent Framework ConcurrentBuilder patterns and integration with existing agents
2. Custom aggregator callback design for result consolidation
3. Review agent design using MS Agent Framework Agent with tool definitions
4. Sensitive data detection patterns for PII redaction
5. Cosmos DB schema for review criteria and orchestration metadata

**Research Tasks**:
- [ ] Study MS Agent Framework ConcurrentBuilder for parallel agent execution (link: https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/orchestrations/concurrent)
- [ ] Design custom aggregator callbacks for orchestration result consolidation
- [ ] Design review agent as MS Agent Framework Agent with validation/redaction tools
- [ ] Identify PII/sensitive data patterns (SSN, credit card, health info, personal identifiers)
- [ ] Design Cosmos DB collections for review criteria (configurable without code)
- [ ] Verify ConcurrentBuilder timeout handling strategy (task isolation, partial results)
- [ ] Map existing api-ms-agent agents to orchestration participants

**Gate**: All research questions answered, ConcurrentBuilder patterns documented, technical approach validated

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

### Phase 2.2: Core Orchestration Workflow (Blocking for Phase 2.3)
- [ ] Implement OrchestrationWorkflow using MS Agent Framework ConcurrentBuilder
- [ ] Implement custom aggregator callback for result consolidation
- [ ] Implement workflow builder with agent registry integration
- [ ] Add event streaming for progress monitoring
- [ ] Test parallel agent execution via ConcurrentBuilder

### Phase 2.3: Review Agent (Blocking for Phase 2.4)
- [ ] Implement ReviewAgent using MS Agent Framework Agent
- [ ] Implement validation tools (sections, consistency, thresholds)
- [ ] Implement sensitive data detection and redaction tools
- [ ] Implement ethical AI safeguards tools (bias, discrimination, harm checks)
- [ ] Test review agent across sample orchestration results

### Phase 2.4: Integration & API
- [ ] Create orchestration handler (orchestration_handler.py)
- [ ] Create REST endpoints (routers/orchestration.py)
- [ ] Integrate with existing auth and multi-tenancy
- [ ] Integration tests for complete workflows

### Phase 2.5: Observability & Production Hardening
- [ ] Structured logging for all orchestration steps
- [ ] Metrics collection (execution time, success rates, review decisions)
- [ ] Error handling and resilience testing
- [ ] Performance testing with 10+ concurrent workflows

---

## Implementation Approach: Microsoft Agent Framework ConcurrentBuilder

### Why MS Agent Framework ConcurrentBuilder?

The Microsoft Agent Framework provides **`ConcurrentBuilder`** for parallel orchestration:
- ✅ **Native Parallel Execution**: Multiple agents work on tasks simultaneously 
- ✅ **Result Aggregation**: Built-in result collection and aggregation
- ✅ **No Custom Code**: Framework handles all concurrency logic
- ✅ **Event Streaming**: Progress events via `run_stream()` for observability
- ✅ **Custom Aggregator Support**: Process results with custom logic
- ✅ **Dependency Injection**: Agents injected as participants

### Core Components (Zero Custom Parallelism Code)

**1. Orchestration Workflow** (using MS Agent Framework ConcurrentBuilder)
```python
# Pseudo-code: actual implementation in orchestrator/workflow_builder.py

from agent_framework import ConcurrentBuilder, ChatMessage, WorkflowOutputEvent
from agent_framework.azure import AzureChatClient

class OrchestrationWorkflow:
    """Builds concurrent workflows using MS Agent Framework ConcurrentBuilder"""
    
    def __init__(self, chat_client: AzureChatClient, agent_registry: AgentRegistry):
        self.chat_client = chat_client
        self.agent_registry = agent_registry
    
    async def build_and_run(
        self,
        request: OrchestrationRequest,
        aggregator_callback: Callable = None
    ) -> WorkflowOutputEvent:
        """
        Build concurrent workflow from request and execute
        MS Agent Framework handles all parallelism - NO custom asyncio code
        """
        
        # Get agents for each task from registry
        agents = []
        for task in request.tasks:
            agent = await self.agent_registry.get_agent(task.agent_name)
            agents.append(agent)
        
        # Build workflow using ConcurrentBuilder (handles all parallelism)
        workflow_builder = ConcurrentBuilder().participants(agents)
        
        # Add custom aggregator if provided (e.g., for result synthesis)
        if aggregator_callback:
            workflow_builder = workflow_builder.with_aggregator(aggregator_callback)
        
        workflow = workflow_builder.build()
        
        # Run workflow with streaming (agents run in parallel automatically)
        # ConcurrentBuilder manages all concurrent execution
        output_evt: WorkflowOutputEvent | None = None
        async for event in workflow.run_stream(self._format_prompt(request)):
            if isinstance(event, WorkflowOutputEvent):
                output_evt = event
                # Event streaming enables progress monitoring
        
        return output_evt
    
    def _format_prompt(self, request: OrchestrationRequest) -> str:
        """Format orchestration request as prompt for agents"""
        return f"""
        Process this request with your expertise:
        
        {json.dumps(request.to_dict())}
        
        Provide your analysis and recommendations.
        """
```

**2. ReviewAgent** (using MS Agent Framework Agent with Tools)
```python
# Pseudo-code: actual implementation in orchestrator/review_agent.py

from agent_framework import ChatAgent
from agent_framework.azure import AzureChatClient

class ReviewAgent:
    """Review agent with validation and redaction tools"""
    
    def __init__(self, chat_client: AzureChatClient, criteria_service):
        self.chat_client = chat_client
        self.criteria_service = criteria_service
        
        # Create review agent with specialized instructions
        self.agent = chat_client.create_agent(
            name="review_agent",
            instructions="""
            You are a quality assurance and compliance reviewer for AI-generated responses.
            
            Your responsibilities:
            1. Validate that response contains all required sections
            2. Check for internal consistency and contradictions
            3. Verify response meets quality thresholds
            4. Identify and redact sensitive personal information (PII, health data, etc.)
            5. Apply ethical safeguards (no bias, discrimination, harmful content)
            
            Use the provided tools to perform your review systematically.
            Provide clear, actionable feedback for any issues found.
            """
        )
        
        # Register tools (called by agent as needed)
        self.tools = {
            "validate_sections": self.validate_sections,
            "check_consistency": self.check_consistency,
            "validate_quality": self.validate_quality,
            "redact_pii": self.redact_pii,
            "check_ethical": self.check_ethical,
        }
    
    async def review(
        self,
        orchestration_result: Dict[str, Any],
        criteria_id: str
    ) -> ReviewDecision:
        """
        Run review agent on orchestration result
        MS Agent Framework agent invokes tools as needed
        """
        
        criteria = await self.criteria_service.get_criteria(criteria_id)
        
        # Prepare context for review agent
        review_context = f"""
        Orchestration Result to Review:
        {json.dumps(orchestration_result, indent=2)}
        
        Validation Criteria:
        - Required Sections: {criteria.required_sections}
        - Quality Thresholds: {criteria.quality_thresholds}
        - Policy Rules: {criteria.policy_rules}
        
        Please review systematically using available tools.
        """
        
        # Agent calls tools as needed - framework handles orchestration
        from agent_framework import ChatMessage, Role
        response = await self.agent.run([
            ChatMessage(Role.USER, text=review_context)
        ])
        
        # Parse agent response and create ReviewDecision
        return self._parse_review_response(response, criteria)
    
    async def validate_sections(self, result: Dict, required: List[str]) -> Dict:
        """Tool: Validate required sections are present"""
        missing = [s for s in required if s not in result]
        return {"valid": len(missing) == 0, "missing": missing}
    
    async def check_consistency(self, result: Dict) -> Dict:
        """Tool: Check for contradictions"""
        # LLM-based consistency checking via tool call
        return {"consistent": True, "issues": []}
    
    async def validate_quality(self, result: Dict, thresholds: Dict) -> Dict:
        """Tool: Validate quality metrics against thresholds"""
        return {"meets_threshold": True, "score": 0.95}
    
    async def redact_pii(self, result: Dict) -> Dict:
        """Tool: Redact personally identifiable information"""
        # PII patterns: SSN, credit card, health info, personal identifiers
        return {"redacted": result, "redactions_applied": 5}
    
    async def check_ethical(self, result: Dict) -> Dict:
        """Tool: Check for ethical AI violations"""
        return {"ethical": True, "issues": []}
    
    def _parse_review_response(self, response, criteria) -> ReviewDecision:
        """Parse agent response into ReviewDecision object"""
        # Extract decision, issues, feedback from agent messages
        return ReviewDecision(...)
```

**3. Orchestration Handler** (uses workflow + review agent)
```python
# Pseudo-code: actual implementation in orchestrator/orchestration_handler.py

class OrchestrationHandler:
    """Handles orchestration requests end-to-end"""
    
    def __init__(
        self,
        workflow_builder: OrchestrationWorkflow,
        review_agent: ReviewAgent
    ):
        self.workflow_builder = workflow_builder
        self.review_agent = review_agent
    
    async def handle_orchestration(
        self,
        request: OrchestrationRequest
    ) -> OrchestrationResult:
        """
        Orchestrate parallel execution with review
        
        Execution flow:
        1. ConcurrentBuilder runs all tasks in parallel (MS Agent Framework)
        2. Results are aggregated by framework
        3. Review agent validates and redacts combined result
        """
        
        # Step 1: Run parallel tasks via ConcurrentBuilder
        # All agents execute concurrently - NO custom parallelism code
        orchestration_output = await self.workflow_builder.build_and_run(
            request,
            aggregator_callback=self._aggregate_results  # Custom aggregator
        )
        
        combined_result = self._extract_result(orchestration_output)
        
        # Step 2: Review the combined result
        review_decision = await self.review_agent.review(
            combined_result,
            request.review_criteria_id
        )
        
        # Step 3: Prepare final result
        return OrchestrationResult(
            orchestration_id=str(uuid4()),
            task_results=self._extract_task_results(orchestration_output),
            review_decision=review_decision,
            total_execution_time_ms=self._calculate_execution_time()
        )
    
    async def _aggregate_results(self, results: List[Any]) -> Dict:
        """Custom aggregator callback for ConcurrentBuilder"""
        # MS Agent Framework calls this to aggregate results
        aggregated = {}
        for result in results:
            executor_id = getattr(result, "executor_id", "unknown")
            aggregated[executor_id] = self._extract_content(result)
        return aggregated
```

---

### Key Difference: Zero Custom Parallelism Code

**Before (❌ Custom asyncio code)**:
```python
# OLD: Custom code for parallelism
async def execute_parallel(tasks, dependencies):
    results = {}
    pending = set(...)
    while pending:
        ready = [t for t in tasks if dependencies_met(t)]
        futures = [execute_task(t) for t in ready]  # ← Custom asyncio logic
        for task, future in zip(ready, asyncio.as_completed(futures)):  # ← Manual concurrency
            results[task.task_id] = await future
            pending.discard(task.task_id)
    return results
```

**After (✅ MS Agent Framework ConcurrentBuilder)**:
```python
# NEW: MS Agent Framework handles ALL parallelism
workflow = ConcurrentBuilder().participants(agents).build()
async for event in workflow.run_stream(prompt):  # ← Framework runs agents in parallel
    if isinstance(event, WorkflowOutputEvent):
        results = event.data  # ← Framework aggregates results automatically
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
