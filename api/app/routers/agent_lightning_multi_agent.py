"""Multi-agent optimization API endpoints.

T035: API endpoints for selective agent optimization control and monitoring.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.dependencies import RequireAuth, require_roles
from app.auth.models import KeycloakUser
from app.services.multi_agent_optimization_coordinator import (
    MultiAgentOptimizationCoordinator,
)

# Create router
router = APIRouter(
    prefix="/api/v1/agent-lightning",
    tags=["agent-lightning-multi-agent"],
)


# Response models
class AgentStatus(BaseModel):
    """Status of an optimizable agent."""

    agent_name: str = Field(..., description="Name of the agent")
    optimization_algorithm: str = Field(
        ..., description="Optimization algorithm assigned to this agent"
    )
    improvement_percent: float = Field(..., description="Current improvement percentage")
    roi_dollars: float = Field(..., description="ROI in dollars")


class AgentListResponse(BaseModel):
    """Response for listing all optimizable agents."""

    tenant_id: str = Field(..., description="Tenant identifier")
    agents: list[AgentStatus] = Field(..., description="List of optimizable agents")


class OptimizeAgentRequest(BaseModel):
    """Request to optimize a specific agent."""

    force: bool = Field(default=False, description="Force optimization even if recently optimized")


class OptimizeAgentResponse(BaseModel):
    """Response for agent optimization trigger."""

    status: str = Field(..., description="Optimization status")
    agent_name: str = Field(..., description="Name of the agent")
    algorithm: str = Field(..., description="Algorithm used for optimization")
    tenant_id: str = Field(..., description="Tenant identifier")
    message: str = Field(..., description="Status message")


class AgentMetricsResponse(BaseModel):
    """Response for per-agent metrics."""

    agent_name: str = Field(..., description="Name of the agent")
    tenant_id: str = Field(..., description="Tenant identifier")
    baseline_metrics: dict[str, float] = Field(..., description="Baseline metrics")
    current_metrics: dict[str, float] = Field(..., description="Current metrics")
    improvement: dict[str, float] = Field(..., description="Improvement percentages")


@router.get(
    "/agents",
    response_model=AgentListResponse,
    summary="List all optimizable agents",
    description="Returns list of all agents that can be optimized with their current status",
)
async def list_agents(
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Any = Depends(require_roles(["user", "admin"])),
) -> AgentListResponse:
    """List all optimizable agents with their status.

    Returns:
        AgentListResponse with list of agents and their optimization status
    """
    tenant_id = current_user.sub

    # Create coordinator for this tenant
    coordinator = MultiAgentOptimizationCoordinator(tenant_id=tenant_id)

    # Get status for all agents
    agents_status = []
    for agent_name in coordinator.agent_names:
        # Get optimization config for this agent
        result = coordinator.trigger_selective_optimization(agent_name)

        # Create agent status (placeholder values for now)
        agent_status = AgentStatus(
            agent_name=agent_name,
            optimization_algorithm=result["algorithm"],
            improvement_percent=0.0,  # TODO: Calculate from actual metrics
            roi_dollars=0.0,  # TODO: Calculate from actual metrics
        )
        agents_status.append(agent_status)

    return AgentListResponse(tenant_id=tenant_id, agents=agents_status)


@router.post(
    "/agents/{agent_name}/optimize",
    response_model=OptimizeAgentResponse,
    summary="Trigger optimization for specific agent",
    description="Starts optimization process for the specified agent",
)
async def optimize_agent(
    agent_name: str,
    request: OptimizeAgentRequest,
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Any = Depends(require_roles(["user", "admin"])),
) -> OptimizeAgentResponse:
    """Trigger optimization for a specific agent.

    Args:
        agent_name: Name of the agent to optimize
        request: Optimization request parameters
        current_user: Authenticated user
        _: Role verification

    Returns:
        OptimizeAgentResponse with optimization status

    Raises:
        HTTPException: If agent name is invalid
    """
    tenant_id = current_user.sub

    # Create coordinator for this tenant
    coordinator = MultiAgentOptimizationCoordinator(tenant_id=tenant_id)

    # Validate agent name
    if agent_name not in coordinator.agent_names:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_name}' not found. "
            f"Valid agents: {', '.join(coordinator.agent_names)}",
        )

    # Trigger optimization
    result = coordinator.trigger_selective_optimization(agent_name)

    return OptimizeAgentResponse(
        status=result["status"],
        agent_name=result["agent_name"],
        algorithm=result["algorithm"],
        tenant_id=result["tenant_id"],
        message=f"Optimization triggered for {agent_name} using {result['algorithm']}",
    )


@router.get(
    "/agents/{agent_name}/metrics",
    response_model=AgentMetricsResponse,
    summary="Get per-agent metrics",
    description="Returns baseline, current, and improvement metrics for a specific agent",
)
async def get_agent_metrics(
    agent_name: str,
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Any = Depends(require_roles(["user", "admin"])),
) -> AgentMetricsResponse:
    """Get metrics for a specific agent.

    Args:
        agent_name: Name of the agent
        current_user: Authenticated user
        _: Role verification

    Returns:
        AgentMetricsResponse with agent metrics

    Raises:
        HTTPException: If agent name is invalid
    """
    tenant_id = current_user.sub

    # Create coordinator for this tenant
    coordinator = MultiAgentOptimizationCoordinator(tenant_id=tenant_id)

    # Validate agent name
    if agent_name not in coordinator.agent_names:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_name}' not found. "
            f"Valid agents: {', '.join(coordinator.agent_names)}",
        )

    # Get metrics for this agent (placeholder values for now)
    # TODO: Fetch actual metrics from database
    baseline_metrics = {
        "avg_latency_ms": 100.0,
        "avg_token_usage": 50.0,
        "avg_quality_signal": 0.75,
    }

    current_metrics = {
        "avg_latency_ms": 90.0,
        "avg_token_usage": 45.0,
        "avg_quality_signal": 0.80,
    }

    improvement = {
        "latency_improvement_percent": 10.0,
        "token_improvement_percent": 10.0,
        "quality_improvement_percent": 6.67,
    }

    return AgentMetricsResponse(
        agent_name=agent_name,
        tenant_id=tenant_id,
        baseline_metrics=baseline_metrics,
        current_metrics=current_metrics,
        improvement=improvement,
    )
