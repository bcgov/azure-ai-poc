"""Unit tests for RL optimization strategy.

Following TDD approach - these tests are written FIRST and will FAIL
until the implementation is created.
"""

import pytest

from app.models.optimization_models import BaselineMetrics, OptimizationConfig


class TestRLOptimizationStrategy:
    """Tests for RL (Reinforcement Learning) optimization strategy."""

    def test_rl_strategy_can_be_instantiated(self) -> None:
        """Test that RL optimization strategy can be created."""
        from app.services.rl_optimization_strategy import RLOptimizationStrategy

        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_rl=True,
            enable_prompt_opt=False,
            enable_sft=False,
        )

        strategy = RLOptimizationStrategy(config)

        assert strategy is not None
        assert strategy.config == config

    def test_rl_strategy_collects_state_action_reward_data(self) -> None:
        """Test RL strategy collects state/action/reward traces."""
        from app.services.rl_optimization_strategy import RLOptimizationStrategy

        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_rl=True,
        )

        strategy = RLOptimizationStrategy(config)

        # Simulate agent execution data
        query = "What is the capital of France?"
        response = "The capital of France is Paris."
        baseline_metrics = BaselineMetrics(
            latency_ms=500.0,
            token_usage=150,
            quality_signal=0.9,
            cost_usd=0.002,
        )

        # Collect RL data (state, action, reward)
        rl_data = strategy.collect_rl_data(
            query=query,
            response=response,
            baseline_metrics=baseline_metrics,
        )

        # Verify RL data structure
        assert rl_data is not None
        assert "state" in rl_data
        assert "action" in rl_data
        assert "reward" in rl_data

        # State should include query context
        assert query in str(rl_data["state"])

        # Action should include response
        assert response in str(rl_data["action"])

        # Reward should be numeric (positive for good, negative for bad)
        assert isinstance(rl_data["reward"], (int, float))

    def test_rl_strategy_calculates_reward_signal(self) -> None:
        """Test RL strategy provides appropriate reward signals."""
        from app.services.rl_optimization_strategy import RLOptimizationStrategy

        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_rl=True,
        )

        strategy = RLOptimizationStrategy(config)

        # High quality response should get positive reward
        high_quality_metrics = BaselineMetrics(
            latency_ms=300.0,
            token_usage=100,
            quality_signal=0.95,  # High quality
            cost_usd=0.001,
        )

        reward_high = strategy._calculate_reward(high_quality_metrics)
        assert reward_high > 0  # Positive reward

        # Low quality response should get negative reward
        low_quality_metrics = BaselineMetrics(
            latency_ms=1000.0,
            token_usage=500,
            quality_signal=0.3,  # Low quality
            cost_usd=0.005,
        )

        reward_low = strategy._calculate_reward(low_quality_metrics)
        assert reward_low < 0  # Negative reward

    def test_rl_strategy_trains_incrementally(self) -> None:
        """Test RL optimizer trains incrementally without requiring all data."""
        from app.services.rl_optimization_strategy import RLOptimizationStrategy

        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_rl=True,
        )

        strategy = RLOptimizationStrategy(config)

        # Add data incrementally
        for i in range(5):
            rl_data = {
                "state": f"query_{i}",
                "action": f"response_{i}",
                "reward": 0.5 + (i * 0.1),
            }
            strategy.add_training_sample(rl_data)

        # Should have collected samples
        assert len(strategy.training_samples) == 5

        # Should be able to train with partial data
        training_result = strategy.train_rl_model()

        assert training_result is not None
        assert "status" in training_result
        # Training may succeed or be pending more data
        assert training_result["status"] in ["success", "pending", "training"]

    @pytest.mark.asyncio
    async def test_rl_strategy_applies_learned_policy(self) -> None:
        """Test RL strategy can apply learned policy to improve decisions."""
        from app.services.rl_optimization_strategy import RLOptimizationStrategy

        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_rl=True,
        )

        strategy = RLOptimizationStrategy(config)

        # Simulate trained policy
        query = "What is machine learning?"
        context = {"query": query, "history": []}

        # Apply policy should return action guidance
        policy_output = await strategy.apply_rl_policy(context)

        assert policy_output is not None
        assert "action_guidance" in policy_output or "decision" in policy_output

    def test_rl_strategy_handles_training_failures_gracefully(self) -> None:
        """Test RL strategy handles training failures without breaking agent."""
        from app.services.rl_optimization_strategy import RLOptimizationStrategy

        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_rl=True,
        )

        strategy = RLOptimizationStrategy(config)

        # Try to train with insufficient data (should not raise exception)
        try:
            result = strategy.train_rl_model()
            # Should return error status instead of raising
            assert result is not None
            assert "status" in result
        except Exception as e:
            pytest.fail(f"Training failure should be handled gracefully: {e}")

    def test_rl_strategy_selects_queries_for_training(self) -> None:
        """Test RL strategy selects appropriate queries for training."""
        from app.services.rl_optimization_strategy import RLOptimizationStrategy

        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_rl=True,
        )

        strategy = RLOptimizationStrategy(config)

        # Create diverse set of queries
        queries = [
            {
                "query": "Simple factual question?",
                "metrics": BaselineMetrics(latency_ms=200.0, token_usage=50, quality_signal=0.95),
            },
            {
                "query": "Complex analytical question requiring reasoning?",
                "metrics": BaselineMetrics(latency_ms=800.0, token_usage=300, quality_signal=0.7),
            },
            {
                "query": "Ambiguous question with unclear intent?",
                "metrics": BaselineMetrics(latency_ms=600.0, token_usage=200, quality_signal=0.5),
            },
        ]

        # Strategy should prioritize queries with lower quality for improvement
        selected = strategy.select_queries_for_training(queries, max_samples=2)

        assert len(selected) <= 2
        # Should prioritize lower quality queries (more room for improvement)
        if len(selected) > 0:
            avg_quality = sum(q["metrics"].quality_signal for q in selected) / len(selected)
            assert avg_quality < 0.8  # Should focus on improvement areas

    def test_rl_strategy_respects_tenant_isolation(self) -> None:
        """Test RL strategy maintains tenant isolation."""
        from app.services.rl_optimization_strategy import RLOptimizationStrategy

        config1 = OptimizationConfig(tenant_id="tenant-1", agent_name="test_agent", enable_rl=True)
        config2 = OptimizationConfig(tenant_id="tenant-2", agent_name="test_agent", enable_rl=True)

        strategy1 = RLOptimizationStrategy(config1)
        strategy2 = RLOptimizationStrategy(config2)

        # Add data to strategy1
        strategy1.add_training_sample({"state": "query_1", "action": "response_1", "reward": 0.8})

        # strategy2 should not see strategy1's data
        assert len(strategy1.training_samples) == 1
        assert len(strategy2.training_samples) == 0
