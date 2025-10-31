"""Unit tests for optimization service strategy selection and execution.

T025: Tests for optimization service updates.
"""

import pytest

from app.models.optimization_models import BaselineMetrics, OptimizationConfig
from app.services.optimization_service import (
    execute_optimization_cycle,
    select_optimization_strategy,
)


class TestOptimizationServiceStrategy:
    """Unit tests for optimization service strategy methods."""

    def test_select_optimization_strategy_for_quality(self) -> None:
        """Test strategy selection prioritizes prompt opt for quality."""
        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_rl=True,
            enable_prompt_opt=True,
            enable_sft=True,
            metric_target="answer_quality",
        )

        baseline = [
            BaselineMetrics(latency_ms=100.0, token_usage=200, quality_signal=0.7)
            for _ in range(10)
        ]

        strategy = select_optimization_strategy(config, baseline)

        # Should prioritize prompt optimization for quality
        assert strategy == "prompt_opt"

    def test_select_optimization_strategy_for_token_efficiency(self) -> None:
        """Test strategy selection prioritizes RL for token efficiency."""
        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_rl=True,
            enable_prompt_opt=True,
            enable_sft=True,
            metric_target="token_efficiency",
        )

        baseline = [
            BaselineMetrics(latency_ms=100.0, token_usage=500, quality_signal=0.7)
            for _ in range(10)
        ]

        strategy = select_optimization_strategy(config, baseline)

        # Should prioritize RL for token efficiency
        assert strategy == "rl"

    def test_select_optimization_strategy_for_latency(self) -> None:
        """Test strategy selection prioritizes RL for latency."""
        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_rl=True,
            enable_prompt_opt=True,
            metric_target="latency",
        )

        baseline = [
            BaselineMetrics(latency_ms=200.0, token_usage=300, quality_signal=0.7)
            for _ in range(10)
        ]

        strategy = select_optimization_strategy(config, baseline)

        # Should prioritize RL for latency
        assert strategy == "rl"

    def test_select_optimization_strategy_fallback(self) -> None:
        """Test strategy selection falls back when preferred not enabled."""
        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_rl=False,
            enable_prompt_opt=False,
            enable_sft=True,
            metric_target="answer_quality",
        )

        baseline = [
            BaselineMetrics(latency_ms=100.0, token_usage=200, quality_signal=0.7)
            for _ in range(10)
        ]

        strategy = select_optimization_strategy(config, baseline)

        # Should fall back to SFT when prompt opt not enabled
        assert strategy == "sft"

    @pytest.mark.asyncio
    async def test_execute_optimization_cycle_requires_minimum_metrics(
        self,
    ) -> None:
        """Test optimization cycle requires at least 50 baseline metrics."""
        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_rl=True,
        )

        # Insufficient baseline metrics (< 50)
        baseline = [
            BaselineMetrics(latency_ms=100.0, token_usage=200, quality_signal=0.7)
            for _ in range(20)
        ]

        queries = [("query1", "response1"), ("query2", "response2")]

        result = await execute_optimization_cycle(config, baseline, queries)

        # Should return insufficient_data status
        assert result["status"] == "insufficient_data"
        assert result["metrics_available"] == 20
        assert result["metrics_required"] == 50

    @pytest.mark.asyncio
    async def test_execute_optimization_cycle_with_rl_strategy(self) -> None:
        """Test optimization cycle executes RL strategy."""
        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_rl=True,
            enable_prompt_opt=False,
            metric_target="token_efficiency",
        )

        # Sufficient baseline metrics
        baseline = [
            BaselineMetrics(latency_ms=100.0, token_usage=300, quality_signal=0.7)
            for _ in range(60)
        ]

        # Training queries
        queries = [(f"query{i}", f"response{i}") for i in range(15)]

        result = await execute_optimization_cycle(config, baseline, queries)

        # Should execute successfully
        assert result["status"] == "success"
        assert result["strategy"] == "rl"
        assert result["training_samples"] == 15

    @pytest.mark.asyncio
    async def test_execute_optimization_cycle_with_prompt_strategy(self) -> None:
        """Test optimization cycle executes prompt optimization strategy."""
        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_rl=False,
            enable_prompt_opt=True,
            metric_target="answer_quality",
        )

        # Sufficient baseline metrics
        baseline = [
            BaselineMetrics(latency_ms=100.0, token_usage=200, quality_signal=0.75)
            for _ in range(55)
        ]

        # Training queries
        queries = [(f"What is {i}?", f"Answer {i}") for i in range(10)]

        result = await execute_optimization_cycle(config, baseline, queries)

        # Should execute successfully
        assert result["status"] == "success"
        assert result["strategy"] == "prompt_opt"
        assert result["variants_tested"] == 3

    @pytest.mark.asyncio
    async def test_execute_optimization_cycle_with_sft_strategy(self) -> None:
        """Test optimization cycle executes SFT strategy."""
        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_rl=False,
            enable_prompt_opt=False,
            enable_sft=True,
        )

        # Sufficient baseline metrics
        baseline = [
            BaselineMetrics(latency_ms=100.0, token_usage=200, quality_signal=0.85)
            for _ in range(50)
        ]

        # Training queries (high quality for SFT)
        queries = [(f"Question {i}?", f"Detailed answer {i}") for i in range(25)]

        result = await execute_optimization_cycle(config, baseline, queries)

        # Should execute successfully
        assert result["status"] == "success"
        assert result["strategy"] == "sft"
        assert result["training_samples"] == 25
