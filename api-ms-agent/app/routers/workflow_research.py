"""
Router for Workflow-based Deep Research Agent.

Provides REST API endpoints for the explicit WorkflowBuilder-based
research agent that runs automatically without human approval
(unless explicitly requested).

Endpoints:
    POST /start - Start a new research workflow
    POST /run/{run_id} - Execute the workflow
    GET /run/{run_id}/status - Get workflow status
    POST /run/{run_id}/approve - Send approval (if required)
    GET /health - Health check
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user_from_request
from app.auth.models import KeycloakUser
from app.logger import get_logger
from app.services.workflow_research_agent import (
    WorkflowResearchAgentService,
    get_workflow_research_service,
)

logger = get_logger(__name__)

router = APIRouter()


# ==================== Request/Response Models ====================


class StartResearchRequest(BaseModel):
    """Request to start a new research workflow."""

    topic: str = Field(
        ...,
        min_length=5,
        description="The topic to research. Include 'approval' or 'review' in the message to require human approval before finalizing.",
    )
    require_approval: bool | None = Field(
        default=None,
        description="Explicitly require approval. If None, auto-detected from topic.",
    )
    user_id: str | None = Field(default=None, description="Optional user ID for tracking")
    model: str | None = Field(
        default=None,
        description="Model to use: 'gpt-4o-mini' (default) or 'gpt-41-nano'",
    )


class StartResearchResponse(BaseModel):
    """Response after starting a research workflow."""

    run_id: str
    topic: str
    status: str
    current_phase: str
    require_approval: bool


class WorkflowResultResponse(BaseModel):
    """Response with workflow execution results."""

    run_id: str
    status: str
    current_phase: str
    topic: str | None = None
    plan: dict | None = None
    findings: list[dict] | None = None
    final_report: str | None = None
    report_preview: str | None = None
    message: str | None = None
    error: str | None = None


class RunStatusResponse(BaseModel):
    """Response with workflow run status."""

    run_id: str
    current_phase: str
    topic: str
    require_approval: bool
    has_plan: bool
    findings_count: int
    has_report: bool
    error: str | None = None


class ApprovalRequest(BaseModel):
    """Request to approve or reject the research report."""

    approved: bool = Field(..., description="Whether to approve the report")
    feedback: str | None = Field(default=None, description="Optional feedback")


class ApprovalResponse(BaseModel):
    """Response after sending approval."""

    run_id: str
    status: str
    approved: bool
    current_phase: str
    final_report: str | None = None
    plan: dict | None = None
    findings: list[dict] | None = None
    feedback: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    features: list[str]


# ==================== Dependency ====================


def get_research_service() -> WorkflowResearchAgentService:
    """Dependency to get the workflow research service."""
    return get_workflow_research_service()


# ==================== Endpoints ====================


@router.post("/start", response_model=StartResearchResponse, status_code=201)
async def start_research(
    request: StartResearchRequest,
    service: Annotated[WorkflowResearchAgentService, Depends(get_research_service)],
    current_user: Annotated[KeycloakUser, Depends(get_current_user_from_request)],
) -> StartResearchResponse:
    """
    Start a new research workflow.

    The workflow will execute automatically through all phases:
    Planning -> Research -> Synthesis -> Complete

    Human approval is only required if:
    - require_approval is explicitly set to True, OR
    - The topic contains keywords like "approval", "review", "confirm", etc.

    Example topics:
    - "Impact of AI on healthcare" (no approval)
    - "Research climate change with approval before finalizing" (requires approval)
    """
    user_id = current_user.sub if current_user else request.user_id
    logger.info(
        "workflow_research_start_requested",
        topic=request.topic,
        user_id=user_id,
        require_approval=request.require_approval,
    )

    try:
        result = await service.start_research(
            topic=request.topic,
            require_approval=request.require_approval,
            user_id=user_id,
            model=request.model,
        )
        logger.info(
            "workflow_research_started",
            run_id=result.get("run_id"),
            user_id=user_id,
            topic=request.topic,
        )
        return StartResearchResponse(**result)
    except Exception as e:
        logger.error(
            "workflow_research_start_failed",
            error=str(e),
            user_id=user_id,
            topic=request.topic,
        )
        raise HTTPException(status_code=500, detail=f"Failed to start research: {e}")


@router.post("/run/{run_id}", response_model=WorkflowResultResponse)
async def run_workflow(
    run_id: str,
    service: Annotated[WorkflowResearchAgentService, Depends(get_research_service)],
    current_user: Annotated[KeycloakUser, Depends(get_current_user_from_request)],
) -> WorkflowResultResponse:
    """
    Execute the research workflow.

    Runs all workflow phases (Planning -> Research -> Synthesis).
    If approval was requested, pauses at AWAITING_APPROVAL phase.
    Otherwise, completes fully and returns the final report.
    """
    user_id = current_user.sub if current_user else None
    logger.info(
        "workflow_run_requested",
        run_id=run_id,
        user_id=user_id,
    )

    try:
        result = await service.run_workflow(run_id)
        logger.info(
            "workflow_run_completed",
            run_id=run_id,
            user_id=user_id,
            status=result.get("status"),
            phase=result.get("current_phase"),
        )
        return WorkflowResultResponse(**result)
    except ValueError as e:
        logger.warning("workflow_run_not_found", run_id=run_id, user_id=user_id, error=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("workflow_run_failed", run_id=run_id, user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to run workflow: {e}")


@router.get("/run/{run_id}/status", response_model=RunStatusResponse)
async def get_run_status(
    run_id: str,
    service: Annotated[WorkflowResearchAgentService, Depends(get_research_service)],
    current_user: Annotated[KeycloakUser, Depends(get_current_user_from_request)],
) -> RunStatusResponse:
    """Get the current status of a workflow run."""
    user_id = current_user.sub if current_user else None
    logger.debug("workflow_status_requested", run_id=run_id, user_id=user_id)

    try:
        result = service.get_run_status(run_id)
        return RunStatusResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/run/{run_id}/approve", response_model=ApprovalResponse)
async def send_approval(
    run_id: str,
    request: ApprovalRequest,
    service: Annotated[WorkflowResearchAgentService, Depends(get_research_service)],
    current_user: Annotated[KeycloakUser, Depends(get_current_user_from_request)],
) -> ApprovalResponse:
    """
    Send approval for a research report awaiting approval.

    Only valid when the workflow is in AWAITING_APPROVAL phase.
    - approved=True: Marks workflow as complete
    - approved=False: Marks workflow as failed/rejected
    """
    user_id = current_user.sub if current_user else None
    logger.info(
        "workflow_approval_requested",
        run_id=run_id,
        user_id=user_id,
        approved=request.approved,
    )

    try:
        result = await service.send_approval(
            run_id=run_id,
            approved=request.approved,
            feedback=request.feedback,
        )
        logger.info(
            "workflow_approval_processed",
            run_id=run_id,
            user_id=user_id,
            approved=request.approved,
            status=result.get("status"),
        )
        return ApprovalResponse(**result)
    except ValueError as e:
        logger.warning(
            "workflow_approval_invalid",
            run_id=run_id,
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "workflow_approval_failed",
            run_id=run_id,
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to send approval: {e}")


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint for the workflow research service."""
    return HealthResponse(
        status="healthy",
        service="workflow-research-agent",
        features=[
            "explicit-workflow-builder",
            "auto-execution",
            "optional-approval",
            "planning-executor",
            "research-executor",
            "synthesis-executor",
        ],
    )
