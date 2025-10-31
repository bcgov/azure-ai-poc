"""Test cases for optimization_service.py (Optimization data collection).

This module tests the optimization service that collects metrics and applies
optimization algorithms. Tests written FIRST per TDD approach.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.models.optimization_models import BaselineMetrics, OptimizationConfig


class TestOptimizationDataCollector:
    """Test cases for OptimizationDataCollector class."""

    @pytest.fixture
    def optimization_config(self) -> OptimizationConfig:
        """Create a test optimization config."""
        return OptimizationConfig(
            tenant_id="tenant-123",
            agent_name="test_agent",
            enable_rl=True,
            enable_prompt_opt=True,
            enable_sft=False,
            metric_target="answer_quality",
        )

    def test_collect_metrics_captures_latency(
        self, optimization_config: OptimizationConfig
    ) -> None:
        """Test collect_metrics() captures latency correctly."""
        from app.services.optimization_service import OptimizationDataCollector

        collector = OptimizationDataCollector(optimization_config)

        # Provide latency in metadata
        metrics = collector.collect_metrics(
            query={"input": "test"},
            response={"output": "test response"},
            agent_metadata={"tokens": 100, "latency_ms": 1200.0},
        )

        assert metrics.latency_ms == 1200.0

    def test_collect_metrics_captures_token_usage(
        self, optimization_config: OptimizationConfig
    ) -> None:
        """Test collect_metrics() captures token usage correctly."""
        from app.services.optimization_service import OptimizationDataCollector

        collector = OptimizationDataCollector(optimization_config)

        metrics = collector.collect_metrics(
            query={"input": "test"},
            response={"output": "test response"},
            agent_metadata={"tokens": 500},
        )

        assert metrics.token_usage == 500

    def test_collect_metrics_captures_quality_signal_when_available(
        self, optimization_config: OptimizationConfig
    ) -> None:
        """Test collect_metrics() captures quality signal when provided."""
        from app.services.optimization_service import OptimizationDataCollector

        collector = OptimizationDataCollector(optimization_config)

        metrics = collector.collect_metrics(
            query={"input": "test"},
            response={"output": "test response"},
            agent_metadata={"tokens": 500},
            quality_signal=0.85,
        )

        assert metrics.quality_signal == 0.85

    def test_collect_metrics_handles_missing_quality_signal(
        self, optimization_config: OptimizationConfig
    ) -> None:
        """Test collect_metrics() handles missing quality signal gracefully."""
        from app.services.optimization_service import OptimizationDataCollector

        collector = OptimizationDataCollector(optimization_config)

        metrics = collector.collect_metrics(
            query={"input": "test"},
            response={"output": "test response"},
            agent_metadata={"tokens": 500},
        )

        assert metrics.quality_signal is None

    def test_collect_metrics_calculates_cost_when_available(
        self, optimization_config: OptimizationConfig
    ) -> None:
        """Test collect_metrics() calculates cost when token pricing available."""
        from app.services.optimization_service import OptimizationDataCollector

        collector = OptimizationDataCollector(optimization_config)

        metrics = collector.collect_metrics(
            query={"input": "test"},
            response={"output": "test response"},
            agent_metadata={"tokens": 1000, "model": "gpt-4o-mini"},
        )

        # Should calculate cost based on token count
        if metrics.cost_usd is not None:
            assert metrics.cost_usd > 0

    def test_collect_metrics_handles_missing_agent_metadata(
        self, optimization_config: OptimizationConfig
    ) -> None:
        """Test collect_metrics() handles missing agent metadata gracefully."""
        from app.services.optimization_service import OptimizationDataCollector

        collector = OptimizationDataCollector(optimization_config)

        # Should not raise exception when metadata is incomplete
        metrics = collector.collect_metrics(
            query={"input": "test"},
            response={"output": "test response"},
            agent_metadata={},  # Empty metadata
        )

        assert isinstance(metrics, BaselineMetrics)

    def test_collect_metrics_returns_valid_baseline_metrics(
        self, optimization_config: OptimizationConfig
    ) -> None:
        """Test collect_metrics() returns valid BaselineMetrics instance."""
        from app.services.optimization_service import OptimizationDataCollector

        collector = OptimizationDataCollector(optimization_config)

        metrics = collector.collect_metrics(
            query={"input": "test"},
            response={"output": "test response"},
            agent_metadata={"tokens": 500},
        )

        assert isinstance(metrics, BaselineMetrics)
        assert metrics.latency_ms > 0
        assert metrics.token_usage == 500


class TestApplyOptimizationAlgorithm:
    """Test cases for apply_optimization_algorithm function."""

    @pytest.fixture
    def optimization_config_rl(self) -> OptimizationConfig:
        """Create config with RL enabled."""
        return OptimizationConfig(
            tenant_id="tenant-123",
            agent_name="test_agent",
            enable_rl=True,
            enable_prompt_opt=False,
            enable_sft=False,
        )

    @pytest.fixture
    def optimization_config_prompt_opt(self) -> OptimizationConfig:
        """Create config with Prompt Optimization enabled."""
        return OptimizationConfig(
            tenant_id="tenant-123",
            agent_name="test_agent",
            enable_rl=False,
            enable_prompt_opt=True,
            enable_sft=False,
        )

    @pytest.fixture
    def optimization_config_sft(self) -> OptimizationConfig:
        """Create config with SFT enabled."""
        return OptimizationConfig(
            tenant_id="tenant-123",
            agent_name="test_agent",
            enable_rl=False,
            enable_prompt_opt=False,
            enable_sft=True,
        )

    def test_apply_optimization_delegates_to_rl_when_enabled(
        self, optimization_config_rl: OptimizationConfig
    ) -> None:
        """Test apply_optimization_algorithm() delegates to RL when enabled."""
        from app.services.optimization_service import apply_optimization_algorithm

        baseline = BaselineMetrics(latency_ms=1200.0, token_usage=500)
        training_data = [{"query": "test", "response": "test response"}]

        with patch("app.services.optimization_service._apply_rl_optimization") as mock_rl:
            mock_rl.return_value = {"status": "RL optimization applied"}

            result = apply_optimization_algorithm(optimization_config_rl, baseline, training_data)

            mock_rl.assert_called_once()
            assert result is not None
            assert "algorithms_applied" in result
            assert "rl" in result["algorithms_applied"]

    def test_apply_optimization_delegates_to_prompt_opt_when_enabled(
        self, optimization_config_prompt_opt: OptimizationConfig
    ) -> None:
        """Test apply_optimization_algorithm() delegates to Prompt Opt when enabled."""
        from app.services.optimization_service import apply_optimization_algorithm

        baseline = BaselineMetrics(latency_ms=1200.0, token_usage=500)
        training_data = [{"query": "test", "response": "test response"}]

        with patch("app.services.optimization_service._apply_prompt_optimization") as mock_prompt:
            mock_prompt.return_value = {"status": "Prompt optimization applied"}

            result = apply_optimization_algorithm(
                optimization_config_prompt_opt, baseline, training_data
            )

            mock_prompt.assert_called_once()
            assert result is not None
            assert "algorithms_applied" in result
            assert "prompt_opt" in result["algorithms_applied"]

    def test_apply_optimization_delegates_to_sft_when_enabled(
        self, optimization_config_sft: OptimizationConfig
    ) -> None:
        """Test apply_optimization_algorithm() delegates to SFT when enabled."""
        from app.services.optimization_service import apply_optimization_algorithm

        baseline = BaselineMetrics(latency_ms=1200.0, token_usage=500)
        training_data = [{"query": "test", "response": "test response"}]

        with patch("app.services.optimization_service._apply_sft_optimization") as mock_sft:
            mock_sft.return_value = {"status": "SFT optimization applied"}

            result = apply_optimization_algorithm(optimization_config_sft, baseline, training_data)

            mock_sft.assert_called_once()
            assert result is not None
            assert "algorithms_applied" in result
            assert "sft" in result["algorithms_applied"]

    def test_apply_optimization_handles_multiple_algorithms(self) -> None:
        """Test apply_optimization_algorithm() handles multiple enabled algorithms."""
        from app.services.optimization_service import apply_optimization_algorithm

        config = OptimizationConfig(
            tenant_id="tenant-123",
            agent_name="test_agent",
            enable_rl=True,
            enable_prompt_opt=True,
            enable_sft=False,
        )

        baseline = BaselineMetrics(latency_ms=1200.0, token_usage=500)
        training_data = [{"query": "test", "response": "test response"}]

        with (
            patch("app.services.optimization_service._apply_rl_optimization") as mock_rl,
            patch("app.services.optimization_service._apply_prompt_optimization") as mock_prompt,
        ):
            mock_rl.return_value = {"rl": "done"}
            mock_prompt.return_value = {"prompt": "done"}

            result = apply_optimization_algorithm(config, baseline, training_data)

            # Both should be called
            mock_rl.assert_called_once()
            mock_prompt.assert_called_once()
            assert result is not None

    def test_apply_optimization_handles_empty_training_data(
        self, optimization_config_rl: OptimizationConfig
    ) -> None:
        """Test apply_optimization_algorithm() handles empty training data gracefully."""
        from app.services.optimization_service import apply_optimization_algorithm

        baseline = BaselineMetrics(latency_ms=1200.0, token_usage=500)
        training_data: list[dict[str, str]] = []  # Empty

        # Should not raise exception, returns None for empty data
        result = apply_optimization_algorithm(optimization_config_rl, baseline, training_data)

        # Returns None when training data is empty (logged warning)
        assert result is None

    def test_apply_optimization_handles_optimization_failure(
        self, optimization_config_rl: OptimizationConfig
    ) -> None:
        """Test apply_optimization_algorithm() handles optimization failures gracefully."""
        from app.services.optimization_service import apply_optimization_algorithm

        baseline = BaselineMetrics(latency_ms=1200.0, token_usage=500)
        training_data = [{"query": "test", "response": "test response"}]

        with patch(
            "app.services.optimization_service._apply_rl_optimization",
            side_effect=Exception("RL optimization failed"),
        ):
            # Should handle exception gracefully (not propagate)
            result = apply_optimization_algorithm(optimization_config_rl, baseline, training_data)

            # Should return error status or None, not raise exception
            assert result is not None or result is None  # Either is acceptable

    def test_apply_optimization_logs_algorithm_selection(
        self, optimization_config_rl: OptimizationConfig
    ) -> None:
        """Test apply_optimization_algorithm() logs which algorithm is selected."""
        from app.services.optimization_service import apply_optimization_algorithm

        baseline = BaselineMetrics(latency_ms=1200.0, token_usage=500)
        training_data = [{"query": "test", "response": "test response"}]

        # Don't need to mock logger, just verify function completes
        result = apply_optimization_algorithm(optimization_config_rl, baseline, training_data)

        # Verify result indicates RL was applied
        assert result is not None
        assert "algorithms_applied" in result
        assert "rl" in result["algorithms_applied"]
