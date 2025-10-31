"""Agent Lightning Analytics Router.

Provides endpoints for analytics and reporting on Agent Lightning
optimization results, including improvement reports, cost impact analysis,
and ROI dashboard data.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth.dependencies import RequireAuth, require_roles
from app.auth.models import KeycloakUser
from app.core.logger import get_logger
from app.models.optimization_models import BaselineMetrics
from app.services.optimization_analytics_service import OptimizationAnalyticsService

logger = get_logger(__name__)

router = APIRouter(tags=["agent-lightning-analytics"])


# Request models


class ImprovementReportRequest(BaseModel):
    """Request model for improvement report generation."""

    agent_name: str = Field(..., description="Name of the agent to analyze")
    baseline_metrics: list[BaselineMetrics] = Field(
        ..., description="Baseline metrics before optimization"
    )
    optimized_metrics: list[BaselineMetrics] = Field(
        ..., description="Optimized metrics after optimization"
    )


class CostImpactRequest(BaseModel):
    """Request model for cost impact calculation."""

    agent_name: str = Field(..., description="Name of the agent to analyze")
    baseline_metrics: list[BaselineMetrics] = Field(
        ..., description="Baseline metrics before optimization"
    )
    optimized_metrics: list[BaselineMetrics] = Field(
        ..., description="Optimized metrics after optimization"
    )
    projected_queries: int = Field(
        default=10000, description="Number of queries to project ROI for", ge=1
    )
    optimization_cost_usd: float = Field(
        default=10.0, description="Cost of running optimization in USD", ge=0.0
    )


# Response models


class ImprovementReportResponse(BaseModel):
    """Response model for improvement report."""

    agent_name: str = Field(..., description="Name of the agent analyzed")
    tenant_id: str = Field(..., description="Tenant identifier")
    baseline_summary: dict[str, float | None] = Field(
        ..., description="Summary of baseline metrics"
    )
    optimized_summary: dict[str, float | None] = Field(
        ..., description="Summary of optimized metrics"
    )
    improvements: dict[str, float] = Field(..., description="Improvement percentages")
    timestamp: str = Field(..., description="ISO timestamp of report generation")


class CostImpactResponse(BaseModel):
    """Response model for cost impact calculation."""

    agent_name: str = Field(..., description="Name of the agent analyzed")
    tenant_id: str = Field(..., description="Tenant identifier")
    token_savings: dict[str, float | int] = Field(..., description="Token savings breakdown")
    cost_roi: dict[str, float] = Field(..., description="Cost ROI breakdown")
    projected_queries: int = Field(..., description="Number of queries projected")
    breakeven_queries: int | None = Field(None, description="Queries needed to break even")
    timestamp: str = Field(..., description="ISO timestamp of calculation")


class ROIDashboardResponse(BaseModel):
    """Response model for ROI dashboard data."""

    agent_name: str = Field(..., description="Name of the agent analyzed")
    tenant_id: str = Field(..., description="Tenant identifier")
    summary: dict[str, float | int] = Field(..., description="High-level summary metrics")
    improvements: dict[str, float] = Field(..., description="Detailed improvement percentages")
    cost_impact: dict[str, float | int | None] = Field(..., description="Cost savings and ROI")
    recommendations: list[str] = Field(..., description="Actionable recommendations")
    projected_queries: int = Field(..., description="Number of queries projected")
    timestamp: str = Field(..., description="ISO timestamp of generation")


# Endpoints


@router.post(
    "/improvement-report",
    summary="Generate Agent Lightning improvement report",
    description=(
        "Generates a comprehensive improvement report comparing baseline "
        "and optimized metrics. Shows improvements in quality, latency, and token efficiency."
    ),
    response_model=ImprovementReportResponse,
)
async def generate_improvement_report(
    request: ImprovementReportRequest,
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Annotated[
        None,
        Depends(require_roles("azure-ai-poc-super-admin", "ai-poc-participant")),
    ],
    token_cost_per_1k: float = Query(
        default=0.002,
        description="Cost per 1000 tokens in USD",
        ge=0.0,
    ),
) -> ImprovementReportResponse:
    """Generate improvement report for optimized agent.

    Compares baseline and optimized metrics to calculate improvement percentages
    for quality, latency, and token efficiency.

    Args:
        request: Improvement report request with metrics
        current_user: Authenticated user (from JWT)
        token_cost_per_1k: Cost per 1000 tokens in USD

    Returns:
        ImprovementReportResponse with detailed improvement analysis

    Raises:
        HTTPException: If metrics are invalid or analysis fails
    """
    try:
        # Use user_id as tenant_id (multi-tenant isolation)
        tenant_id = current_user.sub

        logger.info(
            f"Generating improvement report for agent: {request.agent_name}, tenant: {tenant_id}"
        )

        # Create analytics service
        analytics_service = OptimizationAnalyticsService(
            tenant_id=tenant_id,
            token_cost_per_1k=token_cost_per_1k,
        )

        # Generate improvement report
        report = analytics_service.generate_improvement_report(
            agent_name=request.agent_name,
            baseline_metrics=request.baseline_metrics,
            optimized_metrics=request.optimized_metrics,
        )

        logger.info(
            f"Generated improvement report for {request.agent_name}: "
            f"quality={report['improvements']['quality_improvement']:.1f}%, "
            f"latency={report['improvements']['latency_improvement']:.1f}%, "
            f"tokens={report['improvements']['token_improvement']:.1f}%"
        )

        return ImprovementReportResponse(**report)

    except Exception as e:
        logger.error(f"Failed to generate improvement report: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate improvement report: {str(e)}",
        ) from e


@router.post(
    "/cost-impact",
    summary="Calculate Agent Lightning cost impact and ROI",
    description=(
        "Calculates cost impact and ROI from Agent Lightning optimization. "
        "Shows token savings, cost savings, and breakeven analysis based on "
        "projected query volume."
    ),
    response_model=CostImpactResponse,
)
async def calculate_cost_impact(
    request: CostImpactRequest,
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Annotated[
        None,
        Depends(require_roles("azure-ai-poc-super-admin", "ai-poc-participant")),
    ],
    token_cost_per_1k: float = Query(
        default=0.002,
        description="Cost per 1000 tokens in USD",
        ge=0.0,
    ),
) -> CostImpactResponse:
    """Calculate cost impact and ROI from optimization.

    Calculates token savings, cost savings, and ROI based on projected query volume.
    Includes breakeven analysis to show when optimization investment will be recovered.

    Args:
        request: Cost impact request with metrics and projections
        current_user: Authenticated user (from JWT)
        token_cost_per_1k: Cost per 1000 tokens in USD

    Returns:
        CostImpactResponse with detailed cost analysis and ROI

    Raises:
        HTTPException: If metrics are invalid or calculation fails
    """
    try:
        # Use user_id as tenant_id (multi-tenant isolation)
        tenant_id = current_user.sub

        logger.info(
            f"Calculating cost impact for agent: {request.agent_name}, "
            f"tenant: {tenant_id}, projected_queries: {request.projected_queries}"
        )

        # Create analytics service
        analytics_service = OptimizationAnalyticsService(
            tenant_id=tenant_id,
            token_cost_per_1k=token_cost_per_1k,
        )

        # Calculate cost impact
        impact = analytics_service.calculate_cost_impact(
            agent_name=request.agent_name,
            baseline_metrics=request.baseline_metrics,
            optimized_metrics=request.optimized_metrics,
            projected_queries=request.projected_queries,
            optimization_cost_usd=request.optimization_cost_usd,
        )

        logger.info(
            f"Calculated cost impact for {request.agent_name}: "
            f"net_roi=${impact['cost_roi']['net_roi_usd']:.2f}, "
            f"roi_percent={impact['cost_roi']['roi_percent']:.1f}%, "
            f"tokens_saved={impact['token_savings']['total_tokens_saved']:,}"
        )

        return CostImpactResponse(**impact)

    except Exception as e:
        logger.error(f"Failed to calculate cost impact: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate cost impact: {str(e)}",
        ) from e


@router.post(
    "/roi-dashboard",
    summary="Generate Agent Lightning ROI dashboard data",
    description=(
        "Generates comprehensive ROI dashboard data combining improvement "
        "reports and cost impact analysis. Includes high-level summary metrics, "
        "detailed improvements, cost analysis, and actionable recommendations."
    ),
    response_model=ROIDashboardResponse,
)
async def generate_roi_dashboard(
    request: CostImpactRequest,  # Same request model as cost-impact
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Annotated[
        None,
        Depends(require_roles("azure-ai-poc-super-admin", "ai-poc-participant")),
    ],
    token_cost_per_1k: float = Query(
        default=0.002,
        description="Cost per 1000 tokens in USD",
        ge=0.0,
    ),
) -> ROIDashboardResponse:
    """Generate ROI dashboard data.

    Combines improvement reports and cost impact analysis into a single dashboard
    payload with high-level summary, detailed metrics, and actionable recommendations.

    Args:
        request: Dashboard request with metrics and projections
        current_user: Authenticated user (from JWT)
        token_cost_per_1k: Cost per 1000 tokens in USD

    Returns:
        ROIDashboardResponse with complete dashboard data

    Raises:
        HTTPException: If metrics are invalid or generation fails
    """
    try:
        # Use user_id as tenant_id (multi-tenant isolation)
        tenant_id = current_user.sub

        logger.info(
            f"Generating ROI dashboard for agent: {request.agent_name}, tenant: {tenant_id}"
        )

        # Create analytics service
        analytics_service = OptimizationAnalyticsService(
            tenant_id=tenant_id,
            token_cost_per_1k=token_cost_per_1k,
        )

        # Generate dashboard data
        dashboard = analytics_service.generate_roi_dashboard_data(
            agent_name=request.agent_name,
            baseline_metrics=request.baseline_metrics,
            optimized_metrics=request.optimized_metrics,
            projected_queries=request.projected_queries,
            optimization_cost_usd=request.optimization_cost_usd,
        )

        logger.info(
            f"Generated ROI dashboard for {request.agent_name}: "
            f"overall_improvement={dashboard['summary']['overall_improvement']:.1f}%, "
            f"net_roi=${dashboard['summary']['net_roi_usd']:.2f}, "
            f"recommendations={len(dashboard['recommendations'])}"
        )

        return ROIDashboardResponse(**dashboard)

    except Exception as e:
        logger.error(f"Failed to generate ROI dashboard: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate ROI dashboard: {str(e)}",
        ) from e
