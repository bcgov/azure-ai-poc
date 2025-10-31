"""Agent Lightning metrics and performance tracking endpoints."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth.dependencies import RequireAuth, require_roles
from app.auth.models import KeycloakUser
from app.services.cosmos_db_service import get_cosmos_db_service

router = APIRouter(prefix="/agent-metrics", tags=["Agent Metrics"])


class MetricsStats(BaseModel):
    """Statistics for agent performance metrics."""

    avg_latency_ms: float = Field(..., description="Average response latency in milliseconds")
    min_latency_ms: float = Field(..., description="Minimum latency")
    max_latency_ms: float = Field(..., description="Maximum latency")
    avg_tokens: float = Field(..., description="Average token usage")
    avg_quality: float = Field(..., description="Average quality signal (0.0-1.0)")
    total_requests: int = Field(..., description="Total number of requests")
    total_cost_usd: float = Field(..., description="Total estimated cost in USD")


class MetricsTrend(BaseModel):
    """Metrics trend over time."""

    timestamp: datetime = Field(..., description="Timestamp of the metric")
    latency_ms: float = Field(..., description="Response latency")
    tokens: int = Field(..., description="Token usage")
    quality: float = Field(..., description="Quality signal")
    cost_usd: float | None = Field(None, description="Estimated cost")


class PerformanceComparison(BaseModel):
    """Comparison of performance before and after optimization."""

    baseline: MetricsStats = Field(..., description="Baseline metrics")
    current: MetricsStats = Field(..., description="Current metrics")
    improvement: dict[str, float] = Field(..., description="Percentage improvements")


class AgentMetricsResponse(BaseModel):
    """Agent metrics response."""

    agent_name: str = Field(..., description="Name of the agent")
    tenant_id: str = Field(..., description="Tenant/user ID")
    stats: MetricsStats = Field(..., description="Aggregated statistics")
    recent_trend: list[MetricsTrend] = Field(..., description="Recent metrics trend")


@router.get(
    "/stats",
    summary="Get agent performance statistics",
    description="Retrieve aggregated performance metrics for Agent Lightning wrapped agents",
    response_model=AgentMetricsResponse,
)
async def get_agent_stats(
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Annotated[None, Depends(require_roles("azure-ai-poc-super-admin", "ai-poc-participant"))],
    agent_name: str = Query(
        default="langgraph_document_qa", description="Agent name to get metrics for"
    ),
    days: int = Query(default=7, ge=1, le=90, description="Number of days to analyze"),
) -> AgentMetricsResponse:
    """Get performance statistics for an agent."""
    try:
        cosmos_service = get_cosmos_db_service()
        tenant_id = current_user.sub

        # Calculate date range
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=days)

        # Query metrics from Cosmos DB
        # Note: This assumes metrics are stored with a specific structure
        # Adjust the query based on your actual Cosmos DB schema
        query = """
        SELECT 
            c.agent_metadata.latency_ms as latency,
            c.agent_metadata.tokens as tokens,
            c.quality_signal as quality,
            c.timestamp as timestamp
        FROM c 
        WHERE c.tenant_id = @tenant_id 
            AND c.agent_name = @agent_name
            AND c.timestamp >= @start_date
        ORDER BY c.timestamp DESC
        """

        parameters = [
            {"name": "@tenant_id", "value": tenant_id},
            {"name": "@agent_name", "value": agent_name},
            {"name": "@start_date", "value": start_date.isoformat()},
        ]

        # Execute query
        items = list(
            cosmos_service.container.query_items(
                query=query, parameters=parameters, enable_cross_partition_query=True
            )
        )

        if not items:
            raise HTTPException(
                status_code=404,
                detail=f"No metrics found for agent '{agent_name}' in the last {days} days",
            )

        # Calculate statistics
        latencies = [item["latency"] for item in items if "latency" in item]
        tokens = [item["tokens"] for item in items if "tokens" in item]
        qualities = [item["quality"] for item in items if "quality" in item]

        # Calculate costs (simplified estimation)
        total_tokens = sum(tokens) if tokens else 0
        total_cost = (total_tokens / 1000) * 0.0004  # Simplified: $0.0004 per 1K tokens

        stats = MetricsStats(
            avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0,
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            avg_tokens=sum(tokens) / len(tokens) if tokens else 0,
            avg_quality=sum(qualities) / len(qualities) if qualities else 0,
            total_requests=len(items),
            total_cost_usd=total_cost,
        )

        # Build recent trend (last 20 requests)
        recent_trend = []
        for item in items[:20]:
            recent_trend.append(
                MetricsTrend(
                    timestamp=datetime.fromisoformat(item["timestamp"]),
                    latency_ms=item.get("latency", 0),
                    tokens=item.get("tokens", 0),
                    quality=item.get("quality", 0.0),
                    cost_usd=(item.get("tokens", 0) / 1000) * 0.0004 if "tokens" in item else None,
                )
            )

        return AgentMetricsResponse(
            agent_name=agent_name,
            tenant_id=tenant_id,
            stats=stats,
            recent_trend=recent_trend,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve agent metrics: {str(e)}"
        ) from e


@router.get(
    "/comparison",
    summary="Compare performance before/after optimization",
    description="Compare agent performance between two time periods to measure improvement",
    response_model=PerformanceComparison,
)
async def compare_performance(
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Annotated[None, Depends(require_roles("azure-ai-poc-super-admin", "ai-poc-participant"))],
    agent_name: str = Query(
        default="langgraph_document_qa", description="Agent name to compare metrics for"
    ),
    baseline_days: int = Query(
        default=7, ge=1, le=30, description="Days to use for baseline (older period)"
    ),
    current_days: int = Query(
        default=1, ge=1, le=30, description="Days to use for current period (recent)"
    ),
) -> PerformanceComparison:
    """Compare agent performance between baseline and current periods."""
    try:
        cosmos_service = get_cosmos_db_service()
        tenant_id = current_user.sub

        # Helper function to get stats for a period
        async def get_period_stats(start_date: datetime, end_date: datetime) -> MetricsStats | None:
            query = """
            SELECT 
                c.agent_metadata.latency_ms as latency,
                c.agent_metadata.tokens as tokens,
                c.quality_signal as quality
            FROM c 
            WHERE c.tenant_id = @tenant_id 
                AND c.agent_name = @agent_name
                AND c.timestamp >= @start_date
                AND c.timestamp <= @end_date
            """

            parameters = [
                {"name": "@tenant_id", "value": tenant_id},
                {"name": "@agent_name", "value": agent_name},
                {"name": "@start_date", "value": start_date.isoformat()},
                {"name": "@end_date", "value": end_date.isoformat()},
            ]

            items = list(
                cosmos_service.container.query_items(
                    query=query, parameters=parameters, enable_cross_partition_query=True
                )
            )

            if not items:
                return None

            latencies = [item["latency"] for item in items if "latency" in item]
            tokens = [item["tokens"] for item in items if "tokens" in item]
            qualities = [item["quality"] for item in items if "quality" in item]

            total_tokens = sum(tokens) if tokens else 0
            total_cost = (total_tokens / 1000) * 0.0004

            return MetricsStats(
                avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0,
                min_latency_ms=min(latencies) if latencies else 0,
                max_latency_ms=max(latencies) if latencies else 0,
                avg_tokens=sum(tokens) / len(tokens) if tokens else 0,
                avg_quality=sum(qualities) / len(qualities) if qualities else 0,
                total_requests=len(items),
                total_cost_usd=total_cost,
            )

        # Calculate date ranges
        now = datetime.now(UTC)
        current_start = now - timedelta(days=current_days)
        baseline_end = current_start
        baseline_start = baseline_end - timedelta(days=baseline_days)

        # Get stats for both periods
        baseline_stats = await get_period_stats(baseline_start, baseline_end)
        current_stats = await get_period_stats(current_start, now)

        if not baseline_stats or not current_stats:
            raise HTTPException(
                status_code=404,
                detail="Insufficient data for comparison. Need metrics in both time periods.",
            )

        # Calculate improvements (negative means degradation)
        improvement = {
            "latency_ms": (
                (
                    (baseline_stats.avg_latency_ms - current_stats.avg_latency_ms)
                    / baseline_stats.avg_latency_ms
                    * 100
                )
                if baseline_stats.avg_latency_ms > 0
                else 0
            ),
            "tokens": (
                (
                    (baseline_stats.avg_tokens - current_stats.avg_tokens)
                    / baseline_stats.avg_tokens
                    * 100
                )
                if baseline_stats.avg_tokens > 0
                else 0
            ),
            "quality": (
                (
                    (current_stats.avg_quality - baseline_stats.avg_quality)
                    / baseline_stats.avg_quality
                    * 100
                )
                if baseline_stats.avg_quality > 0
                else 0
            ),
            "cost_reduction": (
                (
                    (baseline_stats.total_cost_usd - current_stats.total_cost_usd)
                    / baseline_stats.total_cost_usd
                    * 100
                )
                if baseline_stats.total_cost_usd > 0
                else 0
            ),
        }

        return PerformanceComparison(
            baseline=baseline_stats, current=current_stats, improvement=improvement
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to compare performance: {str(e)}"
        ) from e
