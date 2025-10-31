"""Optimization ROI (Return on Investment) calculator.

This module calculates improvement metrics, token savings, and cost ROI
from Agent Lightning optimization.
"""

from typing import Any

from app.models.optimization_models import BaselineMetrics


class ROICalculator:
    """Calculator for optimization ROI metrics.

    Compares baseline metrics with optimized metrics to calculate
    improvement percentages, token savings, and estimated cost reduction.
    """

    def __init__(self, token_cost_per_1k: float = 0.002) -> None:
        """Initialize ROI calculator.

        Args:
            token_cost_per_1k: Cost per 1000 tokens in USD (default: $0.002)
        """
        self.token_cost_per_1k = token_cost_per_1k

    def calculate_improvement_percent(
        self,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
    ) -> dict[str, float]:
        """Calculate improvement percentages for key metrics.

        Args:
            baseline_metrics: Metrics before optimization
            optimized_metrics: Metrics after optimization

        Returns:
            Dictionary with improvement percentages:
                - quality_improvement: Quality signal improvement %
                - latency_improvement: Latency reduction %
                - token_improvement: Token usage reduction %

        Example:
            >>> calculator = ROICalculator()
            >>> improvement = calculator.calculate_improvement_percent(
            ...     baseline, optimized
            ... )
            >>> print(improvement["quality_improvement"])  # 15.5
        """
        if not baseline_metrics or not optimized_metrics:
            return {
                "quality_improvement": 0.0,
                "latency_improvement": 0.0,
                "token_improvement": 0.0,
            }

        # Calculate baseline averages
        avg_baseline_quality = sum(m.quality_signal for m in baseline_metrics) / len(
            baseline_metrics
        )
        avg_baseline_latency = sum(m.latency_ms for m in baseline_metrics) / len(baseline_metrics)
        avg_baseline_tokens = sum(m.token_usage for m in baseline_metrics) / len(baseline_metrics)

        # Calculate optimized averages
        avg_optimized_quality = sum(m.quality_signal for m in optimized_metrics) / len(
            optimized_metrics
        )
        avg_optimized_latency = sum(m.latency_ms for m in optimized_metrics) / len(
            optimized_metrics
        )
        avg_optimized_tokens = sum(m.token_usage for m in optimized_metrics) / len(
            optimized_metrics
        )

        # Calculate improvement percentages
        quality_improvement = (
            (avg_optimized_quality - avg_baseline_quality) / avg_baseline_quality
        ) * 100

        latency_improvement = (
            (avg_baseline_latency - avg_optimized_latency) / avg_baseline_latency
        ) * 100

        token_improvement = (
            (avg_baseline_tokens - avg_optimized_tokens) / avg_baseline_tokens
        ) * 100

        return {
            "quality_improvement": round(quality_improvement, 2),
            "latency_improvement": round(latency_improvement, 2),
            "token_improvement": round(token_improvement, 2),
        }

    def calculate_token_savings(
        self,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
        projected_queries: int = 1000,
    ) -> dict[str, Any]:
        """Calculate token savings from optimization.

        Args:
            baseline_metrics: Metrics before optimization
            optimized_metrics: Metrics after optimization
            projected_queries: Number of queries to project savings for

        Returns:
            Dictionary with token savings:
                - baseline_tokens_per_query: Average tokens before
                - optimized_tokens_per_query: Average tokens after
                - tokens_saved_per_query: Tokens saved per query
                - total_tokens_saved: Total tokens saved (projected)
                - projected_queries: Number of queries projected

        Example:
            >>> savings = calculator.calculate_token_savings(
            ...     baseline, optimized, projected_queries=10000
            ... )
            >>> print(savings["total_tokens_saved"])  # 50000
        """
        if not baseline_metrics or not optimized_metrics:
            return {
                "baseline_tokens_per_query": 0,
                "optimized_tokens_per_query": 0,
                "tokens_saved_per_query": 0,
                "total_tokens_saved": 0,
                "projected_queries": projected_queries,
            }

        # Calculate average tokens per query
        avg_baseline_tokens = sum(m.token_usage for m in baseline_metrics) / len(baseline_metrics)
        avg_optimized_tokens = sum(m.token_usage for m in optimized_metrics) / len(
            optimized_metrics
        )

        # Calculate savings
        tokens_saved_per_query = avg_baseline_tokens - avg_optimized_tokens
        total_tokens_saved = int(tokens_saved_per_query * projected_queries)

        return {
            "baseline_tokens_per_query": round(avg_baseline_tokens, 2),
            "optimized_tokens_per_query": round(avg_optimized_tokens, 2),
            "tokens_saved_per_query": round(tokens_saved_per_query, 2),
            "total_tokens_saved": total_tokens_saved,
            "projected_queries": projected_queries,
        }

    def calculate_cost_roi(
        self,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
        projected_queries: int = 1000,
        optimization_cost_usd: float = 10.0,
    ) -> dict[str, Any]:
        """Calculate cost ROI from optimization.

        Args:
            baseline_metrics: Metrics before optimization
            optimized_metrics: Metrics after optimization
            projected_queries: Number of queries to project ROI for
            optimization_cost_usd: Cost of running optimization (training, etc.)

        Returns:
            Dictionary with cost ROI:
                - baseline_cost_usd: Total cost before optimization
                - optimized_cost_usd: Total cost after optimization
                - cost_saved_usd: Total cost saved
                - optimization_cost_usd: Cost of optimization
                - net_roi_usd: Net ROI (savings - optimization cost)
                - roi_percent: ROI as percentage
                - projected_queries: Number of queries projected

        Example:
            >>> roi = calculator.calculate_cost_roi(
            ...     baseline, optimized, projected_queries=10000
            ... )
            >>> print(roi["net_roi_usd"])  # 50.00
        """
        if not baseline_metrics or not optimized_metrics:
            return {
                "baseline_cost_usd": 0.0,
                "optimized_cost_usd": 0.0,
                "cost_saved_usd": 0.0,
                "optimization_cost_usd": optimization_cost_usd,
                "net_roi_usd": -optimization_cost_usd,
                "roi_percent": -100.0,
                "projected_queries": projected_queries,
            }

        # Calculate token savings
        token_savings = self.calculate_token_savings(
            baseline_metrics, optimized_metrics, projected_queries
        )

        # Calculate costs
        baseline_cost_usd = (
            token_savings["baseline_tokens_per_query"]
            * projected_queries
            / 1000
            * self.token_cost_per_1k
        )

        optimized_cost_usd = (
            token_savings["optimized_tokens_per_query"]
            * projected_queries
            / 1000
            * self.token_cost_per_1k
        )

        cost_saved_usd = baseline_cost_usd - optimized_cost_usd
        net_roi_usd = cost_saved_usd - optimization_cost_usd

        # Calculate ROI percentage
        if optimization_cost_usd > 0:
            roi_percent = (net_roi_usd / optimization_cost_usd) * 100
        else:
            roi_percent = 0.0 if net_roi_usd == 0 else float("inf")

        return {
            "baseline_cost_usd": round(baseline_cost_usd, 2),
            "optimized_cost_usd": round(optimized_cost_usd, 2),
            "cost_saved_usd": round(cost_saved_usd, 2),
            "optimization_cost_usd": round(optimization_cost_usd, 2),
            "net_roi_usd": round(net_roi_usd, 2),
            "roi_percent": round(roi_percent, 2),
            "projected_queries": projected_queries,
        }
