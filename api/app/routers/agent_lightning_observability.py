"""
Agent Lightning observability router.

Provides endpoints for monitoring Agent Lightning optimization metrics,
health status, and performance improvements.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.dependencies import RequireAuth, require_roles
from app.auth.models import KeycloakUser
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["agent-lightning"])


# Response models


class MetricsResponse(BaseModel):
    """Agent Lightning optimization metrics response."""

    agent_name: str = Field(..., description="Name of the agent")
    tenant_id: str = Field(..., description="Tenant identifier")
    baseline_latency_ms: float | None = Field(
        None, description="Baseline latency before optimization"
    )
    current_latency_ms: float | None = Field(None, description="Current latency after optimization")
    baseline_token_usage: int | None = Field(
        None, description="Baseline token usage before optimization"
    )
    current_token_usage: int | None = Field(
        None, description="Current token usage after optimization"
    )
    latency_improvement_percent: float | None = Field(
        None, description="Latency improvement percentage"
    )
    token_savings_percent: float | None = Field(None, description="Token savings percentage")
    quality_signal: float | None = Field(None, description="Current quality signal (0.0-1.0)")


class StatusResponse(BaseModel):
    """Agent Lightning health and status response."""

    status: str = Field(..., description="Overall status (healthy, degraded, unhealthy)")
    agent_lightning_available: bool = Field(
        ..., description="Whether Agent Lightning SDK is available"
    )
    optimization_algorithms: list[str] = Field(
        ..., description="List of enabled optimization algorithms"
    )
    agents_wrapped: int = Field(..., description="Number of agents wrapped with Agent Lightning")
    metrics_collected: int = Field(..., description="Total number of metrics collected")
    message: str | None = Field(None, description="Additional status information")


# Endpoints


@router.get(
    "/metrics",
    summary="Get Agent Lightning optimization metrics",
    description="Returns current optimization metrics for the tenant's agents, "
    "including baseline vs optimized performance",
    response_model=MetricsResponse,
)
async def get_metrics(
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Annotated[
        None,
        Depends(require_roles("azure-ai-poc-super-admin", "ai-poc-participant")),
    ],
    agent_name: str = "langgraph_document_qa",
) -> MetricsResponse:
    """Get optimization metrics for the tenant's agent."""
    try:
        from app.core.agent_lightning_config import is_agent_lightning_available

        if not is_agent_lightning_available():
            raise HTTPException(
                status_code=503,
                detail="Agent Lightning is not available or disabled",
            )

        # Use user_id as tenant_id (multi-tenant pattern)
        tenant_id = current_user.sub

        # TODO: Implement actual metrics retrieval from storage
        # For now, return placeholder metrics
        logger.info(f"Metrics requested for agent: {agent_name}, tenant: {tenant_id}")

        return MetricsResponse(
            agent_name=agent_name,
            tenant_id=tenant_id,
            baseline_latency_ms=None,
            current_latency_ms=None,
            baseline_token_usage=None,
            current_token_usage=None,
            latency_improvement_percent=None,
            token_savings_percent=None,
            quality_signal=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving Agent Lightning metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve metrics: {str(e)}",
        ) from e


@router.get(
    "/status",
    summary="Get Agent Lightning health status",
    description="Returns health status of Agent Lightning optimization layer, "
    "including enabled algorithms and agent count",
    response_model=StatusResponse,
)
async def get_status(
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Annotated[
        None,
        Depends(require_roles("azure-ai-poc-super-admin", "ai-poc-participant")),
    ],
) -> StatusResponse:
    """Get Agent Lightning health and status."""
    try:
        from app.core.agent_lightning_config import (
            get_agent_lightning_settings,
            is_agent_lightning_available,
        )

        available = is_agent_lightning_available()

        if not available:
            return StatusResponse(
                status="unavailable",
                agent_lightning_available=False,
                optimization_algorithms=[],
                agents_wrapped=0,
                metrics_collected=0,
                message="Agent Lightning SDK not installed or disabled",
            )

        # Get settings
        settings = get_agent_lightning_settings()

        # Determine enabled algorithms
        algorithms = []
        if settings.enable_rl:
            algorithms.append("reinforcement_learning")
        if settings.enable_prompt_opt:
            algorithms.append("prompt_optimization")
        if settings.enable_sft:
            algorithms.append("supervised_fine_tuning")

        # TODO: Get actual counts from metrics storage
        agents_wrapped = 1  # langgraph_document_qa
        metrics_collected = 0

        status = "healthy" if algorithms else "degraded"

        logger.info(
            f"Status check: available={available}, algorithms={algorithms}, agents={agents_wrapped}"
        )

        return StatusResponse(
            status=status,
            agent_lightning_available=True,
            optimization_algorithms=algorithms,
            agents_wrapped=agents_wrapped,
            metrics_collected=metrics_collected,
            message=f"Agent Lightning operational with {len(algorithms)} algorithms",
        )

    except Exception as e:
        logger.error(f"Error checking Agent Lightning status: {e}")
        return StatusResponse(
            status="unhealthy",
            agent_lightning_available=False,
            optimization_algorithms=[],
            agents_wrapped=0,
            metrics_collected=0,
            message=f"Error: {str(e)}",
        )


# T028: ROI Dashboard Endpoints


class ROIReportResponse(BaseModel):
    """ROI report response model."""

    tenant_id: str = Field(..., description="Tenant identifier")
    baseline_metrics: dict = Field(..., description="Average baseline metrics before optimization")
    current_metrics: dict = Field(..., description="Average current metrics after optimization")
    improvement: dict = Field(..., description="Improvement percentages by metric")
    token_savings: dict = Field(..., description="Token savings calculations")
    cost_roi: dict = Field(..., description="Cost ROI calculations")


class StartOptimizationRequest(BaseModel):
    """Request body for starting optimization."""

    agent_name: str = Field(..., description="Name of the agent to optimize")
    metric_target: str = Field(
        default="answer_quality",
        description="Target metric for optimization "
        "(answer_quality, token_efficiency, latency, cost)",
    )


class StartOptimizationResponse(BaseModel):
    """Response for start optimization request."""

    status: str = Field(..., description="Optimization status (started, queued, running)")
    agent_name: str = Field(..., description="Name of the agent being optimized")
    metric_target: str = Field(..., description="Target metric for optimization")
    estimated_duration_minutes: int | None = Field(
        None, description="Estimated duration in minutes"
    )
    message: str | None = Field(None, description="Additional information")


@router.get(
    "/roi-report",
    summary="Get optimization ROI report",
    description="Returns ROI analysis including improvement percentages, "
    "token savings, and cost reduction estimates",
    response_model=ROIReportResponse,
)
async def get_roi_report(
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Annotated[
        None,
        Depends(require_roles("azure-ai-poc-super-admin", "ai-poc-participant")),
    ],
) -> ROIReportResponse:
    """Get optimization ROI report for the tenant."""
    try:
        from app.core.agent_lightning_config import is_agent_lightning_available

        if not is_agent_lightning_available():
            raise HTTPException(
                status_code=503,
                detail="Agent Lightning is not available or disabled",
            )

        # Use user_id as tenant_id
        tenant_id = current_user.sub

        logger.info(f"ROI report requested for tenant: {tenant_id}")

        # TODO: Implement actual ROI calculation from stored metrics
        # For now, return placeholder data
        return ROIReportResponse(
            tenant_id=tenant_id,
            baseline_metrics={
                "latency_ms": 150.0,
                "token_usage": 300,
                "quality_signal": 0.70,
            },
            current_metrics={
                "latency_ms": 120.0,
                "token_usage": 240,
                "quality_signal": 0.85,
            },
            improvement={
                "quality_improvement": 21.43,
                "latency_improvement": 20.0,
                "token_improvement": 20.0,
            },
            token_savings={
                "tokens_saved_per_query": 60.0,
                "total_tokens_saved": 60000,
                "projected_queries": 1000,
            },
            cost_roi={
                "baseline_cost_usd": 6.0,
                "optimized_cost_usd": 4.8,
                "cost_saved_usd": 1.2,
                "optimization_cost_usd": 5.0,
                "net_roi_usd": -3.8,
                "roi_percent": -76.0,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating ROI report: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate ROI report: {str(e)}",
        ) from e


@router.post(
    "/start-optimization",
    summary="Start optimization cycle",
    description="Triggers an optimization cycle for the specified agent "
    "using collected baseline metrics",
    response_model=StartOptimizationResponse,
)
async def start_optimization(
    request: StartOptimizationRequest,
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Annotated[
        None,
        Depends(require_roles("azure-ai-poc-super-admin", "ai-poc-participant")),
    ],
) -> StartOptimizationResponse:
    """Start optimization cycle for the tenant's agent."""
    try:
        from app.core.agent_lightning_config import is_agent_lightning_available

        if not is_agent_lightning_available():
            raise HTTPException(
                status_code=503,
                detail="Agent Lightning is not available or disabled",
            )

        # Use user_id as tenant_id
        tenant_id = current_user.sub

        logger.info(
            f"Optimization requested for agent: {request.agent_name}, "
            f"tenant: {tenant_id}, target: {request.metric_target}"
        )

        # TODO: Implement actual optimization cycle triggering
        # - Check if sufficient baseline metrics collected (50+)
        # - Select optimization strategy based on metric_target
        # - Execute optimization cycle asynchronously
        # - Return optimization job status

        return StartOptimizationResponse(
            status="started",
            agent_name=request.agent_name,
            metric_target=request.metric_target,
            estimated_duration_minutes=15,
            message="Optimization cycle started successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting optimization: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start optimization: {str(e)}",
        ) from e
