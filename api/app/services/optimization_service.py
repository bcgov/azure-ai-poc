"""Optimization service for Agent Lightning data collection and algorithm execution.

This module handles collection of optimization metrics and delegates to
specific optimization algorithms (RL, Prompt Optimization, SFT).
"""

from typing import Any, Literal

import structlog

from app.models.optimization_models import BaselineMetrics, OptimizationConfig
from app.services.prompt_optimization_strategy import PromptOptimizationStrategy
from app.services.rl_optimization_strategy import RLOptimizationStrategy
from app.services.sft_optimization_strategy import SFTOptimizationStrategy

logger = structlog.get_logger(__name__)


class OptimizationDataCollector:
    """Collects execution traces and metrics for agent optimization."""

    def __init__(self, config: OptimizationConfig) -> None:
        """Initialize the optimization data collector.

        Args:
            config: Optimization configuration for this collector
        """
        self._config = config
        self._traces_collected = 0

    def collect_metrics(
        self,
        query: dict[str, Any],
        response: dict[str, Any],
        agent_metadata: dict[str, Any],
        quality_signal: float | None = None,
    ) -> BaselineMetrics:
        """Collect metrics from agent execution.

        Args:
            query: Input query sent to agent
            response: Response from agent
            agent_metadata: Metadata from agent execution (tokens, model, etc.)
            quality_signal: Optional quality score (0.0-1.0)

        Returns:
            BaselineMetrics: Collected metrics

        Example:
            >>> collector = OptimizationDataCollector(config)
            >>> metrics = collector.collect_metrics(
            ...     query={"input": "test"},
            ...     response={"output": "answer"},
            ...     agent_metadata={"tokens": 500, "model": "gpt-4o-mini"},
            ...     quality_signal=0.85
            ... )
        """
        # Extract latency (use current time as placeholder if not in metadata)
        latency_ms = agent_metadata.get("latency_ms", 100.0)

        # Extract token usage
        token_usage = agent_metadata.get("tokens", 0)

        # Calculate cost if model info available
        cost_usd = self._calculate_cost(token_usage, agent_metadata.get("model"))

        self._traces_collected += 1

        logger.debug(
            "optimization_metrics_collected",
            tenant_id=self._config.tenant_id,
            agent_name=self._config.agent_name,
            latency_ms=latency_ms,
            token_usage=token_usage,
            quality_signal=quality_signal,
            traces_count=self._traces_collected,
        )

        return BaselineMetrics(
            latency_ms=latency_ms,
            token_usage=token_usage,
            quality_signal=quality_signal,
            cost_usd=cost_usd,
        )

    def _calculate_cost(self, token_usage: int, model: str | None) -> float | None:
        """Calculate estimated cost based on token usage and model.

        Args:
            token_usage: Number of tokens used
            model: Model name (e.g., "gpt-4o-mini")

        Returns:
            Estimated cost in USD, or None if pricing unknown
        """
        if not model or token_usage == 0:
            return None

        # Simplified pricing (actual pricing may vary)
        # gpt-4o-mini: ~$0.00015 per 1K tokens (input) + $0.0006 per 1K tokens (output)
        # Average: ~$0.0004 per 1K tokens
        if "gpt-4o-mini" in model.lower():
            return (token_usage / 1000) * 0.0004

        # Default estimate
        return (token_usage / 1000) * 0.001


def apply_optimization_algorithm(
    config: OptimizationConfig,
    baseline: BaselineMetrics,
    training_data: list[dict[str, str]],
) -> dict[str, Any] | None:
    """Apply optimization algorithm(s) based on configuration.

    This function delegates to specific optimization algorithms based on
    which are enabled in the configuration.

    Args:
        config: Optimization configuration
        baseline: Baseline metrics before optimization
        training_data: Training data for optimization algorithms

    Returns:
        Optimization result status or None

    Example:
        >>> result = apply_optimization_algorithm(
        ...     config=OptimizationConfig(tenant_id="t1", enable_rl=True),
        ...     baseline=BaselineMetrics(latency_ms=1200, token_usage=500),
        ...     training_data=[{"query": "test", "response": "answer"}]
        ... )
    """
    if not training_data:
        logger.warning(
            "optimization_skipped_no_training_data",
            tenant_id=config.tenant_id,
            agent_name=config.agent_name,
        )
        return None

    results: dict[str, Any] = {"algorithms_applied": []}

    try:
        # Apply Reinforcement Learning if enabled
        if config.enable_rl:
            logger.info(
                "optimization_applying_rl",
                tenant_id=config.tenant_id,
                agent_name=config.agent_name,
                metric_target=config.metric_target,
            )
            rl_result = _apply_rl_optimization(config, baseline, training_data)
            results["algorithms_applied"].append("rl")
            results["rl"] = rl_result

        # Apply Prompt Optimization if enabled
        if config.enable_prompt_opt:
            logger.info(
                "optimization_applying_prompt_opt",
                tenant_id=config.tenant_id,
                agent_name=config.agent_name,
                metric_target=config.metric_target,
            )
            prompt_result = _apply_prompt_optimization(config, baseline, training_data)
            results["algorithms_applied"].append("prompt_opt")
            results["prompt_opt"] = prompt_result

        # Apply SFT if enabled
        if config.enable_sft:
            logger.info(
                "optimization_applying_sft",
                tenant_id=config.tenant_id,
                agent_name=config.agent_name,
                metric_target=config.metric_target,
            )
            sft_result = _apply_sft_optimization(config, baseline, training_data)
            results["algorithms_applied"].append("sft")
            results["sft"] = sft_result

        logger.info(
            "optimization_completed",
            tenant_id=config.tenant_id,
            agent_name=config.agent_name,
            algorithms=results["algorithms_applied"],
        )

        return results

    except Exception as e:
        logger.error(
            "optimization_failed",
            error=str(e),
            tenant_id=config.tenant_id,
            agent_name=config.agent_name,
        )
        return {"status": "failed", "error": str(e)}


def _apply_rl_optimization(
    config: OptimizationConfig,
    baseline: BaselineMetrics,
    training_data: list[dict[str, str]],
) -> dict[str, Any]:
    """Apply Reinforcement Learning optimization.

    Args:
        config: Optimization configuration
        baseline: Baseline metrics
        training_data: Training data

    Returns:
        RL optimization result
    """
    # Placeholder implementation
    # In production, this would call Agent Lightning's RL optimization
    logger.debug(
        "rl_optimization_stub",
        tenant_id=config.tenant_id,
        training_samples=len(training_data),
    )

    return {
        "status": "RL optimization applied",
        "training_samples": len(training_data),
        "baseline_latency": baseline.latency_ms,
        "baseline_tokens": baseline.token_usage,
    }


def _apply_prompt_optimization(
    config: OptimizationConfig,
    baseline: BaselineMetrics,
    training_data: list[dict[str, str]],
) -> dict[str, Any]:
    """Apply Automatic Prompt Optimization.

    Args:
        config: Optimization configuration
        baseline: Baseline metrics
        training_data: Training data

    Returns:
        Prompt optimization result
    """
    # Placeholder implementation
    # In production, this would call Agent Lightning's Prompt Optimization
    logger.debug(
        "prompt_optimization_stub",
        tenant_id=config.tenant_id,
        training_samples=len(training_data),
    )

    return {
        "status": "Prompt optimization applied",
        "training_samples": len(training_data),
        "baseline_latency": baseline.latency_ms,
        "baseline_tokens": baseline.token_usage,
    }


def _apply_sft_optimization(
    config: OptimizationConfig,
    baseline: BaselineMetrics,
    training_data: list[dict[str, str]],
) -> dict[str, Any]:
    """Apply Supervised Fine-Tuning optimization.

    Args:
        config: Optimization configuration
        baseline: Baseline metrics
        training_data: Training data

    Returns:
        SFT optimization result
    """
    # Placeholder implementation
    # In production, this would call Agent Lightning's SFT
    logger.debug(
        "sft_optimization_stub",
        tenant_id=config.tenant_id,
        training_samples=len(training_data),
    )

    return {
        "status": "SFT optimization applied",
        "training_samples": len(training_data),
        "baseline_latency": baseline.latency_ms,
        "baseline_tokens": baseline.token_usage,
    }


def select_optimization_strategy(
    config: OptimizationConfig,
    baseline_metrics: list[BaselineMetrics],
) -> str:
    """Select best optimization strategy based on config and metrics.

    Args:
        config: Optimization configuration
        baseline_metrics: Baseline performance metrics

    Returns:
        Name of selected strategy: "rl" | "prompt_opt" | "sft"

    Example:
        >>> config = OptimizationConfig(
        ...     tenant_id="t1",
        ...     agent_name="agent1",
        ...     enable_rl=True,
        ...     enable_prompt_opt=True,
        ...     metric_target="answer_quality"
        ... )
        >>> strategy = select_optimization_strategy(config, baseline_metrics)
        >>> print(strategy)  # "prompt_opt"
    """
    # Priority order based on metric target
    if config.metric_target == "answer_quality":
        # Prompt optimization typically best for quality
        if config.enable_prompt_opt:
            return "prompt_opt"
        elif config.enable_sft:
            return "sft"
        elif config.enable_rl:
            return "rl"

    elif config.metric_target == "token_efficiency":
        # RL typically best for token efficiency
        if config.enable_rl:
            return "rl"
        elif config.enable_prompt_opt:
            return "prompt_opt"
        elif config.enable_sft:
            return "sft"

    elif config.metric_target == "latency":
        # RL can optimize for latency
        if config.enable_rl:
            return "rl"
        elif config.enable_prompt_opt:
            return "prompt_opt"
        elif config.enable_sft:
            return "sft"

    elif config.metric_target == "cost":
        # RL best for cost optimization (token reduction)
        if config.enable_rl:
            return "rl"
        elif config.enable_prompt_opt:
            return "prompt_opt"
        elif config.enable_sft:
            return "sft"

    # Default fallback
    if config.enable_rl:
        return "rl"
    elif config.enable_prompt_opt:
        return "prompt_opt"
    elif config.enable_sft:
        return "sft"

    return "rl"  # Default


async def execute_optimization_cycle(
    config: OptimizationConfig,
    baseline_metrics: list[BaselineMetrics],
    queries: list[tuple[str, str]],  # List of (query, response) tuples
) -> dict[str, Any]:
    """Execute complete optimization cycle with selected strategy.

    Args:
        config: Optimization configuration
        baseline_metrics: Baseline performance metrics
        queries: List of (query, response) tuples for training

    Returns:
        Optimization result with status, metrics, and selected strategy

    Example:
        >>> result = await execute_optimization_cycle(
        ...     config,
        ...     baseline_metrics,
        ...     [("query1", "response1"), ("query2", "response2")]
        ... )
        >>> print(result["status"])  # "success"
    """
    if len(baseline_metrics) < 50:
        logger.warning(
            "Insufficient baseline metrics for optimization",
            extra={
                "tenant_id": config.tenant_id,
                "agent_name": config.agent_name,
                "metrics_count": len(baseline_metrics),
                "required": 50,
            },
        )
        return {
            "status": "insufficient_data",
            "metrics_available": len(baseline_metrics),
            "metrics_required": 50,
        }

    # Select optimization strategy
    strategy_name = select_optimization_strategy(config, baseline_metrics)

    logger.info(
        f"Selected optimization strategy: {strategy_name}",
        extra={
            "tenant_id": config.tenant_id,
            "agent_name": config.agent_name,
            "strategy": strategy_name,
            "metric_target": config.metric_target,
        },
    )

    try:
        if strategy_name == "rl":
            strategy = RLOptimizationStrategy(config)
            # Collect training data
            for query, response in queries:
                # Use first baseline metric as representative
                metrics = (
                    baseline_metrics[0]
                    if baseline_metrics
                    else BaselineMetrics(latency_ms=100.0, token_usage=200, quality_signal=0.7)
                )
                rl_data = strategy.collect_rl_data(query, response, metrics)
                strategy.add_training_sample(rl_data)

            # Train model
            result = strategy.train_rl_model()

            return {
                "status": "success",
                "strategy": strategy_name,
                "training_samples": len(queries),
                "result": result,
            }

        elif strategy_name == "prompt_opt":
            strategy = PromptOptimizationStrategy(config)
            # Generate and evaluate variants
            test_queries = [q[0] for q in queries[:5]]  # First 5 queries for testing
            variants = strategy.generate_prompt_variants(
                "Answer the user's question", num_variants=3
            )
            evaluation = strategy.evaluate_variants(variants, test_queries)
            best_prompt = strategy.select_best_prompt(evaluation)

            return {
                "status": "success",
                "strategy": strategy_name,
                "variants_tested": len(variants),
                "best_prompt": best_prompt,
            }

        elif strategy_name == "sft":
            strategy = SFTOptimizationStrategy(config)
            # Collect high-quality training data
            for query, response in queries:
                metrics = (
                    baseline_metrics[0]
                    if baseline_metrics
                    else BaselineMetrics(latency_ms=100.0, token_usage=200, quality_signal=0.85)
                )
                strategy.collect_training_data(query, response, metrics)

            # Fine-tune model
            result = await strategy.fine_tune_model()

            return {
                "status": "success",
                "strategy": strategy_name,
                "training_samples": len(queries),
                "result": result,
            }

        else:
            return {
                "status": "error",
                "error": f"Unknown strategy: {strategy_name}",
            }

    except Exception as e:
        logger.error(
            f"Optimization cycle failed: {e}",
            extra={
                "tenant_id": config.tenant_id,
                "agent_name": config.agent_name,
                "strategy": strategy_name,
                "error": str(e),
            },
        )

        return {
            "status": "error",
            "strategy": strategy_name,
            "error": str(e),
        }
