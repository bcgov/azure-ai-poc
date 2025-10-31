"""Unit tests for SFT (Supervised Fine-Tuning) optimization strategy.

T024: Tests for SFT optimization strategy implementation.
"""

import pytest

from app.models.optimization_models import BaselineMetrics, OptimizationConfig
from app.services.sft_optimization_strategy import SFTOptimizationStrategy


class TestSFTOptimizationStrategy:
    """Unit tests for SFT optimization strategy."""

    def test_sft_strategy_can_be_instantiated(self) -> None:
        """Test SFT strategy can be created with config."""
        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_sft=True,
        )

        strategy = SFTOptimizationStrategy(config)

        assert strategy.config == config
        assert strategy.config.tenant_id == "test-tenant"
        assert strategy.config.agent_name == "test_agent"
        assert hasattr(strategy, "training_data")

    def test_sft_strategy_collects_high_quality_training_data(self) -> None:
        """Test SFT strategy collects high-quality outputs for training."""
        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_sft=True,
        )

        strategy = SFTOptimizationStrategy(config)

        # High quality output (quality_signal >= 0.8)
        query = "What is the capital of France?"
        response = "The capital of France is Paris."
        metrics = BaselineMetrics(
            latency_ms=100.0,
            token_usage=50,
            quality_signal=0.95,  # High quality
        )

        result = strategy.collect_training_data(query, response, metrics)

        # Should accept high quality data
        assert result["accepted"] is True
        assert result["reason"] == "high_quality"
        assert len(strategy.training_data) == 1

    def test_sft_strategy_filters_low_quality_training_data(self) -> None:
        """Test SFT strategy filters out low-quality outputs."""
        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_sft=True,
        )

        strategy = SFTOptimizationStrategy(config)

        # Low quality output (quality_signal < 0.8)
        query = "What is machine learning?"
        response = "ML is stuff."
        metrics = BaselineMetrics(
            latency_ms=50.0,
            token_usage=20,
            quality_signal=0.4,  # Low quality
        )

        result = strategy.collect_training_data(query, response, metrics)

        # Should reject low quality data
        assert result["accepted"] is False
        assert result["reason"] == "low_quality"
        assert len(strategy.training_data) == 0

    @pytest.mark.asyncio
    async def test_sft_strategy_fine_tunes_model_with_sufficient_data(
        self,
    ) -> None:
        """Test SFT strategy fine-tunes model when enough data collected."""
        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_sft=True,
        )

        strategy = SFTOptimizationStrategy(config)

        # Collect sufficient training data (20+ samples)
        for i in range(25):
            query = f"Question {i}?"
            response = f"Detailed answer to question {i}."
            metrics = BaselineMetrics(
                latency_ms=100.0,
                token_usage=100,
                quality_signal=0.85,  # High quality
            )
            strategy.collect_training_data(query, response, metrics)

        # Fine-tune model
        result = await strategy.fine_tune_model()

        # Should succeed with sufficient data
        assert result["status"] in ["success", "fine_tuned", "completed"]
        assert result["samples_used"] == 25
        assert "model_id" in result

    @pytest.mark.asyncio
    async def test_sft_strategy_requires_minimum_training_samples(self) -> None:
        """Test SFT strategy requires minimum samples for fine-tuning."""
        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_sft=True,
        )

        strategy = SFTOptimizationStrategy(config)

        # Collect insufficient training data (< 20 samples)
        for i in range(5):
            query = f"Question {i}?"
            response = f"Answer {i}."
            metrics = BaselineMetrics(
                latency_ms=100.0,
                token_usage=50,
                quality_signal=0.9,
            )
            strategy.collect_training_data(query, response, metrics)

        # Attempt to fine-tune
        result = await strategy.fine_tune_model()

        # Should fail with insufficient data
        assert result["status"] == "insufficient_data"
        assert result["samples_available"] == 5
        assert result["samples_required"] >= 20

    @pytest.mark.asyncio
    async def test_sft_strategy_deploys_finetuned_model(self) -> None:
        """Test SFT strategy can deploy fine-tuned model."""
        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_sft=True,
        )

        strategy = SFTOptimizationStrategy(config)

        # Deploy a fine-tuned model
        model_id = "ft-model-12345"
        result = await strategy.deploy_finetuned_model(model_id)

        # Should return deployment status
        assert result["status"] in ["success", "deployed", "pending"]
        assert result["model_id"] == model_id
        assert "deployment_time" in result or "eta" in result

    @pytest.mark.asyncio
    async def test_sft_strategy_handles_fine_tuning_failures_gracefully(
        self,
    ) -> None:
        """Test SFT strategy handles fine-tuning failures without crashing."""
        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="test_agent",
            enable_sft=True,
        )

        strategy = SFTOptimizationStrategy(config)

        # Collect training data
        for i in range(25):
            query = f"Question {i}?"
            response = f"Answer {i}."
            metrics = BaselineMetrics(
                latency_ms=100.0,
                token_usage=50,
                quality_signal=0.85,
            )
            strategy.collect_training_data(query, response, metrics)

        # Simulate fine-tuning (may fail in test environment)
        result = await strategy.fine_tune_model()

        # Should return status (success or error, but not crash)
        assert "status" in result
        assert isinstance(result["status"], str)

    def test_sft_strategy_respects_tenant_isolation(self) -> None:
        """Test SFT strategy maintains tenant isolation."""
        # Tenant 1
        config1 = OptimizationConfig(
            tenant_id="tenant-1",
            agent_name="agent_1",
            enable_sft=True,
        )
        strategy1 = SFTOptimizationStrategy(config1)

        # Tenant 2
        config2 = OptimizationConfig(
            tenant_id="tenant-2",
            agent_name="agent_2",
            enable_sft=True,
        )
        strategy2 = SFTOptimizationStrategy(config2)

        # Collect data for tenant 1
        for i in range(3):
            metrics = BaselineMetrics(
                latency_ms=100.0,
                token_usage=50,
                quality_signal=0.9,
            )
            strategy1.collect_training_data(f"Tenant 1 query {i}", f"Tenant 1 answer {i}", metrics)

        # Collect data for tenant 2
        for i in range(5):
            metrics = BaselineMetrics(
                latency_ms=150.0,
                token_usage=75,
                quality_signal=0.85,
            )
            strategy2.collect_training_data(f"Tenant 2 query {i}", f"Tenant 2 answer {i}", metrics)

        # Verify tenant 1 has 3 samples
        assert len(strategy1.training_data) == 3

        # Verify tenant 2 has 5 samples
        assert len(strategy2.training_data) == 5

        # Verify no data leakage between tenants
        tenant1_queries = [sample["query"] for sample in strategy1.training_data]
        tenant2_queries = [sample["query"] for sample in strategy2.training_data]

        assert all("Tenant 1" in q for q in tenant1_queries)
        assert all("Tenant 2" in q for q in tenant2_queries)
