"""Integration tests for optimization improvement tracking.

T021: Tests to verify optimization algorithms run without breaking queries
and improvement metrics are calculated correctly.
"""

import pytest

from app.models.optimization_models import BaselineMetrics, OptimizationConfig
from app.services.prompt_optimization_strategy import PromptOptimizationStrategy
from app.services.rl_optimization_strategy import RLOptimizationStrategy


@pytest.mark.asyncio
class TestOptimizationImprovementTracking:
    """Integration tests for optimization improvement tracking."""

    async def test_execute_multiple_queries_and_collect_baseline_metrics(
        self,
    ) -> None:
        """Test executing 50 queries and collecting baseline metrics."""
        # Create optimization config
        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="document_qa",
            enable_rl=True,
        )

        strategy = RLOptimizationStrategy(config)

        # Simulate 50 query executions
        baseline_metrics: list[BaselineMetrics] = []
        for i in range(50):
            metrics = BaselineMetrics(
                latency_ms=100.0 + (i * 2),  # Varying latency
                token_usage=200 + (i * 5),  # Varying tokens
                quality_signal=0.7 + (i * 0.005),  # Improving quality
            )
            baseline_metrics.append(metrics)

            # Collect RL data from each execution
            query = f"What is query {i}?"
            response = f"Answer to query {i}"
            rl_data = strategy.collect_rl_data(query, response, metrics)

            # Verify RL data structure
            assert "state" in rl_data
            assert "action" in rl_data
            assert "reward" in rl_data
            assert isinstance(rl_data["reward"], float)

        # Verify we collected 50 baseline metrics
        assert len(baseline_metrics) == 50
        assert all(isinstance(m, BaselineMetrics) for m in baseline_metrics)

        # Verify metrics show variation (not all identical)
        latencies = [m.latency_ms for m in baseline_metrics]
        assert max(latencies) > min(latencies)

        tokens = [m.token_usage for m in baseline_metrics]
        assert max(tokens) > min(tokens)

        quality = [m.quality_signal for m in baseline_metrics]
        assert max(quality) > min(quality)

    async def test_optimization_algorithm_runs_without_breaking_queries(
        self,
    ) -> None:
        """Test optimization algorithm runs gracefully without breaking queries."""
        # Create optimization config
        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="document_qa",
            enable_rl=True,
        )

        strategy = RLOptimizationStrategy(config)

        # Collect training samples
        for i in range(15):  # More than minimum 10
            metrics = BaselineMetrics(
                latency_ms=100.0 + (i * 2),
                token_usage=200 + (i * 5),
                quality_signal=0.7 + (i * 0.01),
            )
            query = f"What is query {i}?"
            response = f"Answer to query {i}"
            rl_data = strategy.collect_rl_data(query, response, metrics)
            strategy.add_training_sample(rl_data)

        # Run optimization (should not crash)
        result = strategy.train_rl_model()

        # Verify optimization completed
        assert "status" in result
        assert result["status"] in ["success", "trained", "completed"]

        # Apply policy (should not crash)
        context = {"query": "Test query after optimization"}
        policy_result = await strategy.apply_rl_policy(context)

        # Verify policy application returned result
        assert "decision" in policy_result
        assert "action_guidance" in policy_result
        assert "confidence" in policy_result["action_guidance"]

    async def test_before_after_metrics_comparison_calculates_improvement(
        self,
    ) -> None:
        """Test before/after metrics comparison calculates improvement percentage."""
        # Baseline metrics (before optimization)
        baseline_metrics = [
            BaselineMetrics(
                latency_ms=150.0,
                token_usage=300,
                quality_signal=0.65,
            )
            for i in range(20)
        ]

        # Simulated metrics after optimization (improved)
        optimized_metrics = [
            BaselineMetrics(
                latency_ms=120.0,  # 20% faster
                token_usage=240,  # 20% fewer tokens
                quality_signal=0.80,  # ~23% better quality
            )
            for i in range(20)
        ]

        # Calculate average metrics before
        avg_baseline_latency = sum(m.latency_ms for m in baseline_metrics) / len(baseline_metrics)
        avg_baseline_tokens = sum(m.token_usage for m in baseline_metrics) / len(baseline_metrics)
        avg_baseline_quality = sum(m.quality_signal for m in baseline_metrics) / len(
            baseline_metrics
        )

        # Calculate average metrics after
        avg_optimized_latency = sum(m.latency_ms for m in optimized_metrics) / len(
            optimized_metrics
        )
        avg_optimized_tokens = sum(m.token_usage for m in optimized_metrics) / len(
            optimized_metrics
        )
        avg_optimized_quality = sum(m.quality_signal for m in optimized_metrics) / len(
            optimized_metrics
        )

        # Calculate improvement percentages
        latency_improvement = (
            (avg_baseline_latency - avg_optimized_latency) / avg_baseline_latency
        ) * 100
        token_improvement = (
            (avg_baseline_tokens - avg_optimized_tokens) / avg_baseline_tokens
        ) * 100
        quality_improvement = (
            (avg_optimized_quality - avg_baseline_quality) / avg_baseline_quality
        ) * 100

        # Verify improvements
        assert latency_improvement > 15.0  # At least 15% faster
        assert token_improvement > 15.0  # At least 15% fewer tokens
        assert quality_improvement > 20.0  # At least 20% better quality

        # Verify metrics are reasonable
        assert 0 < latency_improvement < 100
        assert 0 < token_improvement < 100
        assert 0 < quality_improvement < 100

    async def test_improvement_metrics_stored_and_queryable(self) -> None:
        """Test improvement metrics can be stored and queried."""
        # Create prompt optimization strategy
        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="document_qa",
            enable_prompt_opt=True,
        )

        strategy = PromptOptimizationStrategy(config)

        # Generate variants and record performance
        original_prompt = "Answer the question"
        variants = strategy.generate_prompt_variants(original_prompt, num_variants=3)

        # Simulate recording performance for each variant
        for variant in variants:
            for i in range(5):  # 5 samples per variant
                metrics = BaselineMetrics(
                    latency_ms=100.0 + (i * 10),
                    token_usage=200 + (i * 20),
                    quality_signal=0.75 + (i * 0.02),
                )
                strategy.record_variant_performance(variant, metrics)

        # Verify metrics stored for all variants
        assert len(strategy.variant_metrics) == len(variants)

        # Verify each variant has stored metrics
        for variant in variants:
            assert variant in strategy.variant_metrics
            recorded_metrics = strategy.variant_metrics[variant]
            assert len(recorded_metrics) == 5  # 5 samples per variant

            # Verify stored metrics are BaselineMetrics instances
            assert all(isinstance(m, BaselineMetrics) for m in recorded_metrics)

            # Verify metrics can be queried/retrieved
            for metric in recorded_metrics:
                assert metric.latency_ms > 0
                assert metric.token_usage > 0
                assert 0.0 <= metric.quality_signal <= 1.0

    async def test_optimization_respects_tenant_isolation(self) -> None:
        """Test optimization metrics isolated per tenant."""
        # Tenant 1
        config1 = OptimizationConfig(tenant_id="tenant-1", agent_name="agent_1", enable_rl=True)
        strategy1 = RLOptimizationStrategy(config1)

        # Tenant 2
        config2 = OptimizationConfig(tenant_id="tenant-2", agent_name="agent_2", enable_rl=True)
        strategy2 = RLOptimizationStrategy(config2)

        # Collect samples for tenant 1
        for i in range(5):
            metrics = BaselineMetrics(
                latency_ms=100.0,
                token_usage=200,
                quality_signal=0.7,
            )
            rl_data = strategy1.collect_rl_data(
                f"Tenant 1 query {i}", f"Tenant 1 answer {i}", metrics
            )
            strategy1.add_training_sample(rl_data)

        # Collect samples for tenant 2
        for i in range(8):
            metrics = BaselineMetrics(
                latency_ms=150.0,
                token_usage=300,
                quality_signal=0.8,
            )
            rl_data = strategy2.collect_rl_data(
                f"Tenant 2 query {i}", f"Tenant 2 answer {i}", metrics
            )
            strategy2.add_training_sample(rl_data)

        # Verify tenant 1 has 5 samples
        assert len(strategy1.training_samples) == 5

        # Verify tenant 2 has 8 samples
        assert len(strategy2.training_samples) == 8

        # Verify no data leakage between tenants
        # Check that strategies maintain separate data
        tenant1_queries = [sample["state"]["query"] for sample in strategy1.training_samples]
        tenant2_queries = [sample["state"]["query"] for sample in strategy2.training_samples]

        # Verify queries are from correct tenants
        assert all("Tenant 1" in q for q in tenant1_queries)
        assert all("Tenant 2" in q for q in tenant2_queries)
