"""Unit tests for Prompt Optimization strategy.

Following TDD approach - these tests are written FIRST and will FAIL
until the implementation is created.
"""

import pytest

from app.models.optimization_models import BaselineMetrics, OptimizationConfig


class TestPromptOptimizationStrategy:
    """Tests for Prompt Optimization strategy."""

    def test_prompt_strategy_can_be_instantiated(self) -> None:
        """Test that Prompt optimization strategy can be created."""
        from app.services.prompt_optimization_strategy import (
            PromptOptimizationStrategy,
        )

        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_prompt_opt=True,
        )

        strategy = PromptOptimizationStrategy(config)

        assert strategy is not None
        assert strategy.config == config

    def test_prompt_strategy_generates_variants(self) -> None:
        """Test prompt optimization generates prompt variants."""
        from app.services.prompt_optimization_strategy import (
            PromptOptimizationStrategy,
        )

        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_prompt_opt=True,
        )

        strategy = PromptOptimizationStrategy(config)

        # Original prompt
        original_prompt = "Answer the following question: {query}"

        # Generate variants
        variants = strategy.generate_prompt_variants(
            original_prompt=original_prompt, num_variants=3
        )

        # Should generate requested number of variants
        assert len(variants) >= 3
        assert all(isinstance(v, str) for v in variants)
        # Variants should be different from original
        assert any(v != original_prompt for v in variants)

    def test_prompt_strategy_evaluates_variants(self) -> None:
        """Test prompt variants are evaluated against baseline."""
        from app.services.prompt_optimization_strategy import (
            PromptOptimizationStrategy,
        )

        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_prompt_opt=True,
        )

        strategy = PromptOptimizationStrategy(config)

        # Test queries and variants
        test_queries = [
            "What is AI?",
            "Explain machine learning",
            "How does neural network work?",
        ]

        variants = [
            "Answer this question clearly: {query}",
            "Provide a concise answer to: {query}",
            "Respond to the following: {query}",
        ]

        # Evaluate variants
        evaluation_results = strategy.evaluate_variants(
            variants=variants, test_queries=test_queries
        )

        # Should return scores for each variant
        assert len(evaluation_results) == len(variants)
        for result in evaluation_results:
            assert "variant" in result
            assert "score" in result
            assert isinstance(result["score"], (int, float))
            assert 0.0 <= result["score"] <= 1.0

    def test_prompt_strategy_selects_best_variant(self) -> None:
        """Test best-performing variant is selected."""
        from app.services.prompt_optimization_strategy import (
            PromptOptimizationStrategy,
        )

        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_prompt_opt=True,
        )

        strategy = PromptOptimizationStrategy(config)

        # Evaluation results with different scores
        evaluation_results = [
            {"variant": "Variant A", "score": 0.75},
            {"variant": "Variant B", "score": 0.92},  # Best
            {"variant": "Variant C", "score": 0.68},
        ]

        # Select best
        best = strategy.select_best_prompt(evaluation_results)

        assert best == "Variant B"
        # Or returns full result
        if isinstance(best, dict):
            assert best["variant"] == "Variant B"
            assert best["score"] == 0.92

    @pytest.mark.asyncio
    async def test_prompt_strategy_applies_optimization(self) -> None:
        """Test prompt optimization can be applied to agent."""
        from app.services.prompt_optimization_strategy import (
            PromptOptimizationStrategy,
        )

        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_prompt_opt=True,
        )

        strategy = PromptOptimizationStrategy(config)

        original_prompt = "Answer: {query}"
        optimized_prompt = "Provide detailed answer: {query}"

        # Apply optimization
        result = await strategy.apply_prompt_optimization(
            current_prompt=original_prompt, optimized_prompt=optimized_prompt
        )

        assert result is not None
        assert "status" in result
        assert result["status"] in ["success", "applied", "pending"]

    def test_prompt_strategy_handles_failures_gracefully(self) -> None:
        """Test prompt optimization handles failures without breaking agent."""
        from app.services.prompt_optimization_strategy import (
            PromptOptimizationStrategy,
        )

        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_prompt_opt=True,
        )

        strategy = PromptOptimizationStrategy(config)

        # Try to generate variants with invalid input
        try:
            variants = strategy.generate_prompt_variants(original_prompt="", num_variants=3)
            # Should return empty list or minimal variants, not crash
            assert isinstance(variants, list)
        except Exception as e:
            pytest.fail(f"Prompt optimization failure should be handled gracefully: {e}")

    def test_prompt_strategy_collects_performance_metrics(self) -> None:
        """Test prompt strategy collects metrics for each variant."""
        from app.services.prompt_optimization_strategy import (
            PromptOptimizationStrategy,
        )

        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_prompt_opt=True,
        )

        strategy = PromptOptimizationStrategy(config)

        # Record performance for a variant
        variant = "Answer clearly: {query}"
        metrics = BaselineMetrics(
            latency_ms=400.0,
            token_usage=120,
            quality_signal=0.88,
            cost_usd=0.0015,
        )

        strategy.record_variant_performance(variant=variant, metrics=metrics)

        # Should be stored
        assert len(strategy.variant_metrics) > 0
        assert variant in strategy.variant_metrics

    def test_prompt_strategy_respects_tenant_isolation(self) -> None:
        """Test prompt strategy maintains tenant isolation."""
        from app.services.prompt_optimization_strategy import (
            PromptOptimizationStrategy,
        )

        config1 = OptimizationConfig(
            tenant_id="tenant-1", agent_name="test_agent", enable_prompt_opt=True
        )
        config2 = OptimizationConfig(
            tenant_id="tenant-2", agent_name="test_agent", enable_prompt_opt=True
        )

        strategy1 = PromptOptimizationStrategy(config1)
        strategy2 = PromptOptimizationStrategy(config2)

        # Record metrics for strategy1
        metrics = BaselineMetrics(latency_ms=400.0, token_usage=120, quality_signal=0.88)
        strategy1.record_variant_performance(variant="test", metrics=metrics)

        # strategy2 should not see strategy1's data
        assert len(strategy1.variant_metrics) > 0
        assert len(strategy2.variant_metrics) == 0
