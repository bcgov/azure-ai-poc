"""Pydantic models for Agent Lightning optimization tracking.

This module defines data models for configuring, tracking, and analyzing
agent optimization metrics when using Agent Lightning.
"""

from typing import Literal

from pydantic import BaseModel, Field


class OptimizationConfig(BaseModel):
    """Configuration for Agent Lightning optimization algorithms.

    Attributes:
        tenant_id: Unique identifier for multi-tenant isolation
        agent_name: Name of the agent being optimized
        enable_rl: Enable Reinforcement Learning optimization
        enable_prompt_opt: Enable Automatic Prompt Optimization
        enable_sft: Enable Supervised Fine-Tuning
        metric_target: Target metric for optimization
    """

    tenant_id: str = Field(
        ...,
        description="Unique tenant identifier for multi-tenant isolation",
        min_length=1,
    )
    agent_name: str = Field(
        default="default",
        description="Name of the agent being optimized",
        min_length=1,
    )
    enable_rl: bool = Field(
        default=True,
        description="Enable Reinforcement Learning optimization",
    )
    enable_prompt_opt: bool = Field(
        default=True,
        description="Enable Automatic Prompt Optimization",
    )
    enable_sft: bool = Field(
        default=False,
        description="Enable Supervised Fine-Tuning (requires training data)",
    )
    metric_target: Literal["answer_quality", "token_efficiency", "latency", "cost"] = Field(
        default="answer_quality",
        description="Primary optimization target metric",
    )

    model_config = {"frozen": False, "extra": "forbid"}


class BaselineMetrics(BaseModel):
    """Baseline performance metrics before Agent Lightning optimization.

    Attributes:
        latency_ms: Response latency in milliseconds
        token_usage: Total tokens used (prompt + completion)
        quality_signal: Quality score (0.0-1.0, from user feedback or eval)
        cost_usd: Estimated cost in USD
    """

    latency_ms: float = Field(
        ...,
        description="Response latency in milliseconds",
        ge=0.0,
    )
    token_usage: int = Field(
        ...,
        description="Total tokens used (prompt + completion)",
        ge=0,
    )
    quality_signal: float | None = Field(
        default=None,
        description="Quality score (0.0-1.0, from user feedback or evaluation)",
        ge=0.0,
        le=1.0,
    )
    cost_usd: float | None = Field(
        default=None,
        description="Estimated cost in USD",
        ge=0.0,
    )

    model_config = {"frozen": True, "extra": "forbid"}


class OptimizationMetrics(BaseModel):
    """Optimization metrics after Agent Lightning optimization.

    Attributes:
        latency_ms: Response latency in milliseconds (post-optimization)
        token_usage: Total tokens used (post-optimization)
        quality_signal: Quality score (post-optimization)
        cost_usd: Estimated cost in USD (post-optimization)
        improvement_percent: Overall improvement percentage
        token_savings: Number of tokens saved
        latency_change_ms: Change in latency (negative = improvement)
        roi_percent: Return on investment percentage
    """

    latency_ms: float = Field(
        ...,
        description="Response latency in milliseconds (post-optimization)",
        ge=0.0,
    )
    token_usage: int = Field(
        ...,
        description="Total tokens used (post-optimization)",
        ge=0,
    )
    quality_signal: float | None = Field(
        default=None,
        description="Quality score (0.0-1.0, post-optimization)",
        ge=0.0,
        le=1.0,
    )
    cost_usd: float | None = Field(
        default=None,
        description="Estimated cost in USD (post-optimization)",
        ge=0.0,
    )

    # Derived metrics (calculated from baseline comparison)
    improvement_percent: float | None = Field(
        default=None,
        description="Overall improvement percentage (positive = better)",
    )
    token_savings: int | None = Field(
        default=None,
        description="Number of tokens saved (positive = savings)",
    )
    latency_change_ms: float | None = Field(
        default=None,
        description="Change in latency in milliseconds (negative = faster)",
    )
    roi_percent: float | None = Field(
        default=None,
        description="Return on investment percentage (cost savings)",
    )

    model_config = {"frozen": True, "extra": "forbid"}

    @classmethod
    def from_baseline_comparison(
        cls,
        baseline: BaselineMetrics,
        optimized_latency_ms: float,
        optimized_token_usage: int,
        optimized_quality_signal: float | None = None,
        optimized_cost_usd: float | None = None,
    ) -> "OptimizationMetrics":
        """Create OptimizationMetrics by comparing with baseline.

        This factory method calculates derived metrics (improvement_percent,
        token_savings, latency_change_ms, roi_percent) from baseline comparison.

        Args:
            baseline: Baseline metrics before optimization
            optimized_latency_ms: Latency after optimization (ms)
            optimized_token_usage: Token usage after optimization
            optimized_quality_signal: Quality score after optimization (optional)
            optimized_cost_usd: Cost after optimization (optional)

        Returns:
            OptimizationMetrics: Metrics instance with derived calculations

        Example:
            >>> baseline = BaselineMetrics(
            ...     latency_ms=1200.0,
            ...     token_usage=500,
            ...     quality_signal=0.75,
            ...     cost_usd=0.015
            ... )
            >>> optimized = OptimizationMetrics.from_baseline_comparison(
            ...     baseline=baseline,
            ...     optimized_latency_ms=1100.0,
            ...     optimized_token_usage=400,
            ...     optimized_quality_signal=0.80,
            ...     optimized_cost_usd=0.012
            ... )
            >>> print(f"Token savings: {optimized.token_savings}")
            Token savings: 100
            >>> print(f"ROI: {optimized.roi_percent:.2f}%")
            ROI: 20.00%
        """
        # Calculate token savings
        token_savings = baseline.token_usage - optimized_token_usage

        # Calculate latency change (negative = improvement)
        latency_change_ms = optimized_latency_ms - baseline.latency_ms

        # Calculate improvement percentage (weighted average)
        # If quality signal available, weight quality more heavily
        if baseline.quality_signal is not None and optimized_quality_signal is not None:
            quality_improvement = (
                (optimized_quality_signal - baseline.quality_signal) / baseline.quality_signal
            ) * 100
            token_efficiency_improvement = (token_savings / baseline.token_usage) * 100
            latency_improvement = (-latency_change_ms / baseline.latency_ms) * 100

            # Weighted average: 50% quality, 30% token efficiency, 20% latency
            improvement_percent = (
                0.5 * quality_improvement
                + 0.3 * token_efficiency_improvement
                + 0.2 * latency_improvement
            )
        else:
            # Without quality signal, use token efficiency and latency only
            token_efficiency_improvement = (token_savings / baseline.token_usage) * 100
            latency_improvement = (-latency_change_ms / baseline.latency_ms) * 100
            improvement_percent = 0.6 * token_efficiency_improvement + 0.4 * latency_improvement

        # Calculate ROI (cost savings percentage)
        roi_percent = None
        if baseline.cost_usd is not None and optimized_cost_usd is not None:
            cost_savings = baseline.cost_usd - optimized_cost_usd
            roi_percent = (cost_savings / baseline.cost_usd) * 100

        return cls(
            latency_ms=optimized_latency_ms,
            token_usage=optimized_token_usage,
            quality_signal=optimized_quality_signal,
            cost_usd=optimized_cost_usd,
            improvement_percent=improvement_percent,
            token_savings=token_savings,
            latency_change_ms=latency_change_ms,
            roi_percent=roi_percent,
        )
