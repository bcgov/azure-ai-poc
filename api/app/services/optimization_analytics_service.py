"""Optimization Analytics Service for Agent Lightning.

This service provides analytics and reporting capabilities for Agent Lightning
optimization workflows, including improvement reports, cost impact analysis,
and ROI dashboard data aggregation.
"""

from datetime import UTC, datetime
from typing import Any

from app.core.optimization_roi_calculator import ROICalculator
from app.models.optimization_models import BaselineMetrics


class OptimizationAnalyticsService:
    """Service for generating analytics and reports from optimization data.

    This service aggregates optimization metrics and generates actionable
    insights for stakeholders, including improvement percentages, cost savings,
    and ROI projections.
    """

    def __init__(
        self,
        tenant_id: str,
        token_cost_per_1k: float = 0.002,
    ) -> None:
        """Initialize the analytics service.

        Args:
            tenant_id: Tenant identifier for multi-tenant isolation
            token_cost_per_1k: Cost per 1000 tokens in USD (default: $0.002)
        """
        self.tenant_id = tenant_id
        self.roi_calculator = ROICalculator(token_cost_per_1k=token_cost_per_1k)

    def generate_improvement_report(
        self,
        agent_name: str,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
    ) -> dict[str, Any]:
        """Generate comprehensive improvement report.

        Compares baseline and optimized metrics to generate a detailed report
        showing improvements in quality, latency, and token efficiency.

        Args:
            agent_name: Name of the agent being analyzed
            baseline_metrics: Metrics before optimization
            optimized_metrics: Metrics after optimization

        Returns:
            Dictionary containing:
                - agent_name: Name of the agent
                - tenant_id: Tenant identifier
                - baseline_summary: Average baseline metrics
                - optimized_summary: Average optimized metrics
                - improvements: Improvement percentages
                - timestamp: ISO format timestamp of report generation

        Example:
            >>> service = OptimizationAnalyticsService(tenant_id="tenant-123")
            >>> report = service.generate_improvement_report(
            ...     agent_name="query_planner",
            ...     baseline_metrics=baseline,
            ...     optimized_metrics=optimized
            ... )
            >>> print(report["improvements"]["quality_improvement"])  # 15.5
        """
        # Calculate improvement percentages
        improvements = self.roi_calculator.calculate_improvement_percent(
            baseline_metrics, optimized_metrics
        )

        # Calculate baseline summary
        baseline_summary: dict[str, float | None] = {}
        if baseline_metrics:
            baseline_summary = {
                "avg_quality_signal": (
                    sum(m.quality_signal for m in baseline_metrics if m.quality_signal is not None)
                    / len([m for m in baseline_metrics if m.quality_signal is not None])
                    if any(m.quality_signal is not None for m in baseline_metrics)
                    else None
                ),
                "avg_latency_ms": sum(m.latency_ms for m in baseline_metrics)
                / len(baseline_metrics),
                "avg_token_usage": sum(m.token_usage for m in baseline_metrics)
                / len(baseline_metrics),
                "sample_count": float(len(baseline_metrics)),
            }

        # Calculate optimized summary
        optimized_summary: dict[str, float | None] = {}
        if optimized_metrics:
            optimized_summary = {
                "avg_quality_signal": (
                    sum(m.quality_signal for m in optimized_metrics if m.quality_signal is not None)
                    / len([m for m in optimized_metrics if m.quality_signal is not None])
                    if any(m.quality_signal is not None for m in optimized_metrics)
                    else None
                ),
                "avg_latency_ms": sum(m.latency_ms for m in optimized_metrics)
                / len(optimized_metrics),
                "avg_token_usage": sum(m.token_usage for m in optimized_metrics)
                / len(optimized_metrics),
                "sample_count": float(len(optimized_metrics)),
            }

        return {
            "agent_name": agent_name,
            "tenant_id": self.tenant_id,
            "baseline_summary": baseline_summary,
            "optimized_summary": optimized_summary,
            "improvements": improvements,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def calculate_cost_impact(
        self,
        agent_name: str,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
        projected_queries: int = 10000,
        optimization_cost_usd: float = 10.0,
    ) -> dict[str, Any]:
        """Calculate cost impact and ROI from optimization.

        Calculates token savings, cost savings, and ROI based on projected
        query volume. Useful for demonstrating business value of optimization.

        Args:
            agent_name: Name of the agent being analyzed
            baseline_metrics: Metrics before optimization
            optimized_metrics: Metrics after optimization
            projected_queries: Number of queries to project savings for
            optimization_cost_usd: Cost of running optimization (training, etc.)

        Returns:
            Dictionary containing:
                - agent_name: Name of the agent
                - tenant_id: Tenant identifier
                - token_savings: Token savings breakdown
                - cost_roi: Cost ROI breakdown
                - projected_queries: Number of queries projected
                - breakeven_queries: Queries needed to break even
                - timestamp: ISO format timestamp of calculation

        Example:
            >>> service = OptimizationAnalyticsService(tenant_id="tenant-123")
            >>> impact = service.calculate_cost_impact(
            ...     agent_name="query_planner",
            ...     baseline_metrics=baseline,
            ...     optimized_metrics=optimized,
            ...     projected_queries=100000
            ... )
            >>> print(impact["cost_roi"]["net_roi_usd"])  # 50.00
        """
        # Calculate token savings
        token_savings = self.roi_calculator.calculate_token_savings(
            baseline_metrics, optimized_metrics, projected_queries
        )

        # Calculate cost ROI
        cost_roi = self.roi_calculator.calculate_cost_roi(
            baseline_metrics, optimized_metrics, projected_queries, optimization_cost_usd
        )

        # Calculate breakeven point (queries needed to recover optimization cost)
        breakeven_queries: int | None = None
        if token_savings["tokens_saved_per_query"] > 0:
            cost_saved_per_query = (
                token_savings["tokens_saved_per_query"]
                / 1000
                * self.roi_calculator.token_cost_per_1k
            )
            if cost_saved_per_query > 0:
                breakeven_queries = int(optimization_cost_usd / cost_saved_per_query)

        return {
            "agent_name": agent_name,
            "tenant_id": self.tenant_id,
            "token_savings": token_savings,
            "cost_roi": cost_roi,
            "projected_queries": projected_queries,
            "breakeven_queries": breakeven_queries,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def generate_roi_dashboard_data(
        self,
        agent_name: str,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
        projected_queries: int = 10000,
        optimization_cost_usd: float = 10.0,
    ) -> dict[str, Any]:
        """Generate aggregated data for ROI dashboard.

        Combines improvement report and cost impact into a single dashboard
        payload with all key metrics for stakeholder presentation.

        Args:
            agent_name: Name of the agent being analyzed
            baseline_metrics: Metrics before optimization
            optimized_metrics: Metrics after optimization
            projected_queries: Number of queries to project savings for
            optimization_cost_usd: Cost of running optimization

        Returns:
            Dictionary containing:
                - agent_name: Name of the agent
                - tenant_id: Tenant identifier
                - summary: High-level summary metrics
                - improvements: Detailed improvement percentages
                - cost_impact: Cost savings and ROI
                - recommendations: Actionable recommendations
                - timestamp: ISO format timestamp of generation

        Example:
            >>> service = OptimizationAnalyticsService(tenant_id="tenant-123")
            >>> dashboard = service.generate_roi_dashboard_data(
            ...     agent_name="query_planner",
            ...     baseline_metrics=baseline,
            ...     optimized_metrics=optimized,
            ...     projected_queries=100000
            ... )
            >>> print(dashboard["summary"]["overall_improvement"])
        """
        # Generate improvement report
        improvement_report = self.generate_improvement_report(
            agent_name, baseline_metrics, optimized_metrics
        )

        # Calculate cost impact
        cost_impact = self.calculate_cost_impact(
            agent_name,
            baseline_metrics,
            optimized_metrics,
            projected_queries,
            optimization_cost_usd,
        )

        # Calculate overall improvement (weighted average)
        improvements = improvement_report["improvements"]
        overall_improvement = (
            improvements["quality_improvement"] * 0.5
            + improvements["token_improvement"] * 0.3
            + improvements["latency_improvement"] * 0.2
        )

        # Generate recommendations based on metrics
        recommendations: list[str] = []
        if cost_impact["cost_roi"]["roi_percent"] < 0:
            if cost_impact["breakeven_queries"]:
                breakeven = cost_impact["breakeven_queries"]
                recommendations.append(f"Optimization will break even after {breakeven:,} queries")
            else:
                recommendations.append("Consider lower-cost optimization strategies")
        else:
            roi_pct = cost_impact["cost_roi"]["roi_percent"]
            recommendations.append(f"Positive ROI of {roi_pct:.1f}% - continue optimization")

        if improvements["quality_improvement"] < 0:
            recommendations.append("Quality degradation detected - review optimization algorithm")
        elif improvements["quality_improvement"] >= 20:
            recommendations.append("Significant quality improvement - consider wider rollout")

        if improvements["token_improvement"] > 30:
            recommendations.append(
                "Excellent token efficiency gains - update token allocation budgets"
            )

        # Build summary
        summary = {
            "overall_improvement": round(overall_improvement, 2),
            "quality_improvement": improvements["quality_improvement"],
            "token_improvement": improvements["token_improvement"],
            "latency_improvement": improvements["latency_improvement"],
            "net_roi_usd": cost_impact["cost_roi"]["net_roi_usd"],
            "roi_percent": cost_impact["cost_roi"]["roi_percent"],
            "tokens_saved": cost_impact["token_savings"]["total_tokens_saved"],
            "cost_saved_usd": cost_impact["cost_roi"]["cost_saved_usd"],
        }

        return {
            "agent_name": agent_name,
            "tenant_id": self.tenant_id,
            "summary": summary,
            "improvements": {
                "quality": improvements["quality_improvement"],
                "token_efficiency": improvements["token_improvement"],
                "latency": improvements["latency_improvement"],
            },
            "cost_impact": {
                "tokens_saved": cost_impact["token_savings"]["total_tokens_saved"],
                "cost_saved_usd": cost_impact["cost_roi"]["cost_saved_usd"],
                "optimization_cost_usd": cost_impact["cost_roi"]["optimization_cost_usd"],
                "net_roi_usd": cost_impact["cost_roi"]["net_roi_usd"],
                "roi_percent": cost_impact["cost_roi"]["roi_percent"],
                "breakeven_queries": cost_impact["breakeven_queries"],
            },
            "recommendations": recommendations,
            "projected_queries": projected_queries,
            "timestamp": datetime.now(UTC).isoformat(),
        }
