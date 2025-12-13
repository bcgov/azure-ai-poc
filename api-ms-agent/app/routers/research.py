"""
Research Router - API endpoints for deep research agent using Agent Framework SDK.

Provides endpoints for:
- Starting new research workflows
- Running workflows with streaming support
- Handling human approval checkpoints
- Getting workflow status and results
- Document-based deep research
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user_from_request
from app.auth.models import AuthenticatedUser
from app.logger import get_logger
from app.services.research_agent import (
    DeepResearchAgentService,
    get_deep_research_service,
)

logger = get_logger(__name__)

router = APIRouter()


# ==================== Request/Response Models ====================


class StartResearchRequest(BaseModel):
    """Request to start a new research workflow."""

    topic: str = Field(..., min_length=3, max_length=500, description="The topic to research")
    user_id: str | None = Field(None, description="Optional user ID for tracking")
    document_id: str | None = Field(
        None, description="Optional document ID for document-based research"
    )
    model: str | None = Field(
        default=None,
        description="Model to use: 'gpt-4o-mini' (default) or 'gpt-41-nano'",
    )


class ApprovalRequest(BaseModel):
    """Request to send an approval for a pending checkpoint."""

    request_id: str = Field(..., description="The ID of the approval request")
    approved: bool = Field(..., description="Whether to approve the request")
    feedback: str | None = Field(None, description="Optional feedback with the approval")


class WorkflowStartResponse(BaseModel):
    """Response when starting a new workflow."""

    run_id: str
    topic: str
    status: str
    current_phase: str


class WorkflowStatusResponse(BaseModel):
    """Response for workflow status."""

    run_id: str
    current_phase: str
    topic: str
    has_plan: bool
    findings_count: int
    has_report: bool
    pending_approvals: int


class SourceInfo(BaseModel):
    """Source citation information - MANDATORY for traceability."""

    source_type: str = Field(
        ..., description="Type of source: 'llm_knowledge', 'document', 'web', 'api'"
    )
    description: str = Field(..., description="Description of the source")
    confidence: str = Field(
        default="medium", description="Confidence level: 'high', 'medium', 'low'"
    )
    url: str | None = Field(default=None, description="URL of the source if available")


class WorkflowResultResponse(BaseModel):
    """Response with full workflow results - includes mandatory source citations."""

    run_id: str
    status: str
    current_phase: str | None = None
    plan: dict | None = None
    findings: list[dict] = []
    final_report: str = ""
    sources: list[SourceInfo] = Field(
        default_factory=list,
        description="Sources used in the research (REQUIRED for traceability)",
    )
    has_sufficient_info: bool = Field(
        default=True, description="Whether sufficient information was available"
    )
    message: str | None = None
    workflow_state: str | None = None
    error: str | None = None


class ApprovalResponse(BaseModel):
    """Response after sending an approval."""

    run_id: str
    request_id: str
    status: str
    approved: bool


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str


# ==================== Dependency ====================


def get_research_service() -> DeepResearchAgentService:
    """Dependency to get the research service."""
    return get_deep_research_service()


ResearchServiceDep = Annotated[DeepResearchAgentService, Depends(get_research_service)]


# ==================== Endpoints ====================


@router.post(
    "/start",
    response_model=WorkflowStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new research workflow",
    description="""
    Start a new deep research workflow using the Agent Framework SDK.
    This creates a new workflow run and returns the run_id.
    Use the /run/{run_id} endpoint to execute the workflow.
    If document_id is provided, the research will thoroughly scan the document.
    """,
)
async def start_research(
    request: StartResearchRequest,
    service: ResearchServiceDep,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user_from_request)],
) -> WorkflowStartResponse:
    """Start a new research workflow."""
    user_id = current_user.sub if current_user else request.user_id

    try:
        result = await service.start_research(
            topic=request.topic,
            user_id=user_id,
            document_id=request.document_id,
            model=request.model,
        )
        return WorkflowStartResponse(**result)
    except Exception as e:
        logger.error("start_research_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start research: {str(e)}",
        ) from e


@router.post(
    "/run/{run_id}",
    response_model=WorkflowResultResponse,
    summary="Execute the research workflow",
    description="""
    Execute the research workflow.

    The workflow will run through all phases:
    1. Planning - Creates research plan with approval checkpoint
    2. Researching - Gathers findings with approval checkpoint
    3. Synthesizing - Creates final report with approval checkpoint

    Each phase uses ai_function(approval_mode="always_require") for human-in-the-loop.
    """,
)
async def run_workflow(
    run_id: str,
    service: ResearchServiceDep,
) -> WorkflowResultResponse:
    """Execute the research workflow."""
    logger.info("executing_workflow", run_id=run_id)

    try:
        result = await service.run_workflow(run_id)
        return WorkflowResultResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error("run_workflow_failed", run_id=run_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run workflow: {str(e)}",
        ) from e


@router.get(
    "/run/{run_id}/stream",
    summary="Execute workflow with streaming events",
    description="""
    Execute the research workflow and stream events as they occur.

    Returns Server-Sent Events (SSE) with workflow progress,
    including approval requests that pause the workflow.
    """,
)
async def run_workflow_streaming(
    run_id: str,
    service: ResearchServiceDep,
):
    """Execute the workflow with streaming events."""
    import json

    async def event_generator():
        try:
            async for event in service.run_workflow_streaming(run_id):
                yield f"data: {json.dumps(event)}\n\n"
        except ValueError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        except Exception as e:
            logger.error("streaming_error", run_id=run_id, error=str(e))
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get(
    "/run/{run_id}/status",
    response_model=WorkflowStatusResponse,
    summary="Get workflow run status",
    description="Get the current status of a workflow run.",
)
async def get_run_status(
    run_id: str,
    service: ResearchServiceDep,
) -> WorkflowStatusResponse:
    """Get the status of a workflow run."""
    try:
        result = service.get_run_status(run_id)
        return WorkflowStatusResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post(
    "/run/{run_id}/approve",
    response_model=ApprovalResponse,
    summary="Send approval for a pending checkpoint",
    description="""
    Send an approval response for a pending human-in-the-loop checkpoint.

    When the workflow pauses at an approval checkpoint, use this endpoint
    to approve or reject and resume the workflow.
    """,
)
async def send_approval(
    run_id: str,
    request: ApprovalRequest,
    service: ResearchServiceDep,
) -> ApprovalResponse:
    """Send an approval for a pending checkpoint."""
    logger.info(
        "sending_approval",
        run_id=run_id,
        request_id=request.request_id,
        approved=request.approved,
    )

    try:
        result = await service.send_approval(
            run_id=run_id,
            request_id=request.request_id,
            approved=request.approved,
            feedback=request.feedback,
        )
        return ApprovalResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error("send_approval_failed", run_id=run_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send approval: {str(e)}",
        ) from e


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check if the research service is healthy.",
)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy", service="deep-research-agent-framework")
