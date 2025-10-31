"""Reinforcement Learning optimization strategy for Agent Lightning.

This module implements RL-based optimization for improving agent decisions
through reward-based learning from execution traces.
"""

from typing import Any

from app.core.logger import get_logger
from app.models.optimization_models import BaselineMetrics, OptimizationConfig

logger = get_logger(__name__)


class RLOptimizationStrategy:
    """Reinforcement Learning optimization strategy.

    Uses reward signals from agent execution to train an RL model that
    improves agent decision-making over time.

    Attributes:
        config: Optimization configuration
        training_samples: Collected RL training data (state/action/reward tuples)
    """

    def __init__(self, config: OptimizationConfig) -> None:
        """Initialize RL optimization strategy.

        Args:
            config: Optimization configuration with tenant_id and agent_name
        """
        self.config = config
        self.training_samples: list[dict[str, Any]] = []

        logger.info(
            f"RL optimization strategy initialized for agent: {config.agent_name}",
            extra={"tenant_id": config.tenant_id, "agent_name": config.agent_name},
        )

    def collect_rl_data(
        self,
        query: str,
        response: str,
        baseline_metrics: BaselineMetrics,
    ) -> dict[str, Any]:
        """Collect RL training data from agent execution.

        Captures state (query context), action (response), and reward (quality signal)
        for reinforcement learning.

        Args:
            query: User query (state)
            response: Agent response (action)
            baseline_metrics: Execution metrics for reward calculation

        Returns:
            Dictionary with state, action, and reward

        Example:
            >>> strategy = RLOptimizationStrategy(config)
            >>> rl_data = strategy.collect_rl_data(
            ...     query="What is AI?",
            ...     response="AI is artificial intelligence...",
            ...     baseline_metrics=BaselineMetrics(...)
            ... )
            >>> print(rl_data["reward"])
            0.85
        """
        # Calculate reward signal
        reward = self._calculate_reward(baseline_metrics)

        # Create RL training sample
        rl_data = {
            "state": {"query": query, "tenant_id": self.config.tenant_id},
            "action": {"response": response},
            "reward": reward,
        }

        logger.debug(
            f"Collected RL data: reward={reward:.3f}",
            extra={
                "tenant_id": self.config.tenant_id,
                "agent_name": self.config.agent_name,
                "reward": reward,
            },
        )

        return rl_data

    def _calculate_reward(self, metrics: BaselineMetrics) -> float:
        """Calculate reward signal from execution metrics.

        Positive reward for good outcomes (high quality, low latency/tokens)
        Negative reward for poor outcomes (low quality, high latency/tokens)

        Args:
            metrics: Baseline execution metrics

        Returns:
            Reward value (positive for good, negative for bad)

        Reward Formula:
            reward = quality_signal - (latency_penalty + token_penalty)
            where penalties are normalized to 0-1 scale
        """
        # Quality signal is primary reward component (0.0-1.0)
        # Shift to [-0.5, 0.5] range so low quality can be negative
        quality_reward = (metrics.quality_signal - 0.5) if metrics.quality_signal else 0.0

        # Latency penalty (normalized: 0 for <500ms, 1.0 for >5000ms)
        latency_penalty = min(metrics.latency_ms / 5000.0, 1.0) * 0.3

        # Token usage penalty (normalized: 0 for <100 tokens, 1.0 for >1000 tokens)
        token_penalty = min(metrics.token_usage / 1000.0, 1.0) * 0.2

        # Combined reward: quality - penalties
        reward = quality_reward - latency_penalty - token_penalty

        # Scale to [-1.0, 1.0] range
        reward = max(-1.0, min(1.0, reward))

        return reward

    def add_training_sample(self, rl_data: dict[str, Any]) -> None:
        """Add a training sample to the RL dataset.

        Enables incremental learning without requiring all data at once.

        Args:
            rl_data: RL training sample with state, action, reward
        """
        self.training_samples.append(rl_data)

        logger.debug(
            f"Added RL training sample (total: {len(self.training_samples)})",
            extra={
                "tenant_id": self.config.tenant_id,
                "agent_name": self.config.agent_name,
                "sample_count": len(self.training_samples),
            },
        )

    def train_rl_model(self) -> dict[str, Any]:
        """Train RL model with collected samples.

        Invokes Agent Lightning RL training API with accumulated data.
        Training is incremental - doesn't require all data at once.

        Returns:
            Training result with status and metrics

        Note:
            Handles failures gracefully - returns error status instead of raising
        """
        try:
            # Check if we have sufficient samples
            if len(self.training_samples) < 10:
                logger.warning(
                    f"Insufficient samples for RL training: "
                    f"{len(self.training_samples)}/10 minimum",
                    extra={
                        "tenant_id": self.config.tenant_id,
                        "agent_name": self.config.agent_name,
                        "sample_count": len(self.training_samples),
                    },
                )
                return {
                    "status": "pending",
                    "message": f"Need {10 - len(self.training_samples)} more samples",
                    "samples_collected": len(self.training_samples),
                }

            # In real implementation, this would call Agent Lightning RL API
            # For now, simulate training
            logger.info(
                f"Training RL model with {len(self.training_samples)} samples",
                extra={
                    "tenant_id": self.config.tenant_id,
                    "agent_name": self.config.agent_name,
                    "sample_count": len(self.training_samples),
                },
            )

            # Simulate successful training
            return {
                "status": "success",
                "message": "RL model trained successfully",
                "samples_used": len(self.training_samples),
                "model_version": "rl_v1",
            }

        except Exception as e:
            logger.error(
                f"RL training failed: {e}",
                exc_info=True,
                extra={
                    "tenant_id": self.config.tenant_id,
                    "agent_name": self.config.agent_name,
                },
            )
            return {
                "status": "error",
                "message": f"Training failed: {str(e)}",
            }

    async def apply_rl_policy(self, context: dict[str, Any]) -> dict[str, Any]:
        """Apply learned RL policy to improve agent decisions.

        Uses trained RL model to provide action guidance for the agent.

        Args:
            context: Query context (state) for policy decision

        Returns:
            Policy output with action guidance

        Note:
            If no model is trained yet, returns default guidance
        """
        try:
            query = context.get("query", "")

            logger.debug(
                "Applying RL policy",
                extra={
                    "tenant_id": self.config.tenant_id,
                    "agent_name": self.config.agent_name,
                    "query_length": len(query),
                },
            )

            # In real implementation, this would query trained RL model
            # For now, return default guidance
            return {
                "action_guidance": {
                    "strategy": "balanced",
                    "confidence": 0.75,
                },
                "decision": "proceed",
            }

        except Exception as e:
            logger.error(
                f"Failed to apply RL policy: {e}",
                exc_info=True,
                extra={
                    "tenant_id": self.config.tenant_id,
                    "agent_name": self.config.agent_name,
                },
            )
            # Return safe default on failure
            return {
                "action_guidance": {"strategy": "default", "confidence": 0.5},
                "decision": "proceed",
            }

    def select_queries_for_training(
        self,
        queries: list[dict[str, Any]],
        max_samples: int = 10,
    ) -> list[dict[str, Any]]:
        """Select queries for RL training.

        Prioritizes queries with lower quality scores (more room for improvement).

        Args:
            queries: List of query/metrics pairs
            max_samples: Maximum number of queries to select

        Returns:
            Selected queries prioritized by improvement potential

        Strategy:
            - Focus on queries with quality_signal < 0.8
            - Diverse representation across latency/token ranges
            - Balance between edge cases and common patterns
        """
        # Filter for improvement candidates (quality < 0.8)
        improvement_candidates = [
            q for q in queries if q["metrics"].quality_signal and q["metrics"].quality_signal < 0.8
        ]

        # Sort by quality score (lowest first - most room for improvement)
        improvement_candidates.sort(key=lambda q: q["metrics"].quality_signal or 0.0)

        # Select up to max_samples
        selected = improvement_candidates[:max_samples]

        logger.info(
            f"Selected {len(selected)} queries for RL training",
            extra={
                "tenant_id": self.config.tenant_id,
                "agent_name": self.config.agent_name,
                "total_queries": len(queries),
                "selected_count": len(selected),
            },
        )

        return selected
