"""Test cases for optimization_models.py (Agent Lightning data models).

This module tests Pydantic models used for Agent Lightning configuration
and metrics tracking. Tests written FIRST per TDD approach.
"""

import pytest
from pydantic import ValidationError

from app.models.optimization_models import (
    BaselineMetrics,
    OptimizationConfig,
    OptimizationMetrics,
)


class TestOptimizationConfig:
    """Test cases for OptimizationConfig Pydantic model."""

    def test_optimization_config_valid_default(self) -> None:
        """Test OptimizationConfig with valid defaults."""
        config = OptimizationConfig(tenant_id="tenant-123")

        assert config.tenant_id == "tenant-123"
        assert config.agent_name == "default"
        assert config.enable_rl is True
        assert config.enable_prompt_opt is True
        assert config.enable_sft is False
        assert config.metric_target == "answer_quality"

    def test_optimization_config_valid_custom(self) -> None:
        """Test OptimizationConfig with all custom values."""
        config = OptimizationConfig(
            tenant_id="tenant-456",
            agent_name="document_qa",
            enable_rl=False,
            enable_prompt_opt=True,
            enable_sft=True,
            metric_target="token_efficiency",
        )

        assert config.tenant_id == "tenant-456"
        assert config.agent_name == "document_qa"
        assert config.enable_rl is False
        assert config.enable_prompt_opt is True
        assert config.enable_sft is True
        assert config.metric_target == "token_efficiency"

    def test_optimization_config_all_metrics_targets(self) -> None:
        """Test OptimizationConfig accepts all valid metric_target values."""
        valid_targets = ["answer_quality", "token_efficiency", "latency", "cost"]

        for target in valid_targets:
            config = OptimizationConfig(tenant_id="tenant-123", metric_target=target)
            assert config.metric_target == target

    def test_optimization_config_missing_tenant_id(self) -> None:
        """Test OptimizationConfig raises ValidationError without tenant_id."""
        with pytest.raises(ValidationError) as exc_info:
            OptimizationConfig()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("tenant_id",) for error in errors)
        assert any(error["type"] == "missing" for error in errors)

    def test_optimization_config_empty_tenant_id(self) -> None:
        """Test OptimizationConfig rejects empty tenant_id."""
        with pytest.raises(ValidationError) as exc_info:
            OptimizationConfig(tenant_id="")

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("tenant_id",) for error in errors)

    def test_optimization_config_invalid_metric_target(self) -> None:
        """Test OptimizationConfig rejects invalid metric_target."""
        with pytest.raises(ValidationError) as exc_info:
            OptimizationConfig(
                tenant_id="tenant-123",
                metric_target="invalid_target",  # type: ignore[arg-type]
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("metric_target",) for error in errors)

    def test_optimization_config_forbids_extra_fields(self) -> None:
        """Test OptimizationConfig rejects unknown fields (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            OptimizationConfig(
                tenant_id="tenant-123",
                unknown_field="value",  # type: ignore[call-arg]
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("unknown_field",) for error in errors)
        assert any(error["type"] == "extra_forbidden" for error in errors)


class TestBaselineMetrics:
    """Test cases for BaselineMetrics Pydantic model."""

    def test_baseline_metrics_valid_required_only(self) -> None:
        """Test BaselineMetrics with only required fields."""
        metrics = BaselineMetrics(
            latency_ms=1200.0,
            token_usage=500,
        )

        assert metrics.latency_ms == 1200.0
        assert metrics.token_usage == 500
        assert metrics.quality_signal is None
        assert metrics.cost_usd is None

    def test_baseline_metrics_valid_all_fields(self) -> None:
        """Test BaselineMetrics with all fields populated."""
        metrics = BaselineMetrics(
            latency_ms=1200.0,
            token_usage=500,
            quality_signal=0.85,
            cost_usd=0.015,
        )

        assert metrics.latency_ms == 1200.0
        assert metrics.token_usage == 500
        assert metrics.quality_signal == 0.85
        assert metrics.cost_usd == 0.015

    def test_baseline_metrics_quality_signal_bounds(self) -> None:
        """Test BaselineMetrics quality_signal is bounded [0.0, 1.0]."""
        # Valid bounds
        metrics_low = BaselineMetrics(latency_ms=1000.0, token_usage=400, quality_signal=0.0)
        assert metrics_low.quality_signal == 0.0

        metrics_high = BaselineMetrics(latency_ms=1000.0, token_usage=400, quality_signal=1.0)
        assert metrics_high.quality_signal == 1.0

        # Invalid: quality_signal < 0
        with pytest.raises(ValidationError):
            BaselineMetrics(latency_ms=1000.0, token_usage=400, quality_signal=-0.1)

        # Invalid: quality_signal > 1.0
        with pytest.raises(ValidationError):
            BaselineMetrics(latency_ms=1000.0, token_usage=400, quality_signal=1.1)

    def test_baseline_metrics_negative_latency_rejected(self) -> None:
        """Test BaselineMetrics rejects negative latency_ms."""
        with pytest.raises(ValidationError):
            BaselineMetrics(latency_ms=-100.0, token_usage=500)

    def test_baseline_metrics_negative_token_usage_rejected(self) -> None:
        """Test BaselineMetrics rejects negative token_usage."""
        with pytest.raises(ValidationError):
            BaselineMetrics(latency_ms=1000.0, token_usage=-50)

    def test_baseline_metrics_negative_cost_rejected(self) -> None:
        """Test BaselineMetrics rejects negative cost_usd."""
        with pytest.raises(ValidationError):
            BaselineMetrics(latency_ms=1000.0, token_usage=500, cost_usd=-0.01)

    def test_baseline_metrics_frozen(self) -> None:
        """Test BaselineMetrics is immutable (frozen=True)."""
        metrics = BaselineMetrics(latency_ms=1200.0, token_usage=500)

        with pytest.raises(ValidationError):
            metrics.latency_ms = 1300.0  # type: ignore[misc]


class TestOptimizationMetrics:
    """Test cases for OptimizationMetrics Pydantic model."""

    def test_optimization_metrics_valid_required_only(self) -> None:
        """Test OptimizationMetrics with only required fields."""
        metrics = OptimizationMetrics(
            latency_ms=1100.0,
            token_usage=400,
        )

        assert metrics.latency_ms == 1100.0
        assert metrics.token_usage == 400
        assert metrics.quality_signal is None
        assert metrics.cost_usd is None
        assert metrics.improvement_percent is None
        assert metrics.token_savings is None
        assert metrics.latency_change_ms is None
        assert metrics.roi_percent is None

    def test_optimization_metrics_valid_all_fields(self) -> None:
        """Test OptimizationMetrics with all fields populated."""
        metrics = OptimizationMetrics(
            latency_ms=1100.0,
            token_usage=400,
            quality_signal=0.88,
            cost_usd=0.012,
            improvement_percent=15.5,
            token_savings=100,
            latency_change_ms=-100.0,
            roi_percent=20.0,
        )

        assert metrics.latency_ms == 1100.0
        assert metrics.token_usage == 400
        assert metrics.quality_signal == 0.88
        assert metrics.cost_usd == 0.012
        assert metrics.improvement_percent == 15.5
        assert metrics.token_savings == 100
        assert metrics.latency_change_ms == -100.0
        assert metrics.roi_percent == 20.0

    def test_optimization_metrics_frozen(self) -> None:
        """Test OptimizationMetrics is immutable (frozen=True)."""
        metrics = OptimizationMetrics(latency_ms=1100.0, token_usage=400)

        with pytest.raises(ValidationError):
            metrics.latency_ms = 1200.0  # type: ignore[misc]

    def test_optimization_metrics_from_baseline_comparison_token_savings(self) -> None:
        """Test from_baseline_comparison calculates token_savings correctly."""
        baseline = BaselineMetrics(latency_ms=1200.0, token_usage=500)

        optimized = OptimizationMetrics.from_baseline_comparison(
            baseline=baseline,
            optimized_latency_ms=1100.0,
            optimized_token_usage=400,
        )

        assert optimized.token_savings == 100  # 500 - 400

    def test_optimization_metrics_from_baseline_comparison_latency_change(self) -> None:
        """Test from_baseline_comparison calculates latency_change_ms correctly."""
        baseline = BaselineMetrics(latency_ms=1200.0, token_usage=500)

        optimized = OptimizationMetrics.from_baseline_comparison(
            baseline=baseline,
            optimized_latency_ms=1100.0,
            optimized_token_usage=400,
        )

        assert optimized.latency_change_ms == -100.0  # 1100 - 1200 (negative = faster)

    def test_optimization_metrics_from_baseline_comparison_improvement_without_quality(
        self,
    ) -> None:
        """Test improvement_percent calculation WITHOUT quality_signal."""
        baseline = BaselineMetrics(latency_ms=1000.0, token_usage=500)

        optimized = OptimizationMetrics.from_baseline_comparison(
            baseline=baseline,
            optimized_latency_ms=900.0,  # 10% faster
            optimized_token_usage=400,  # 20% token savings
        )

        # Expected: 0.6 * 20% (token) + 0.4 * 10% (latency) = 12% + 4% = 16%
        assert optimized.improvement_percent is not None
        assert pytest.approx(optimized.improvement_percent, rel=0.01) == 16.0

    def test_optimization_metrics_from_baseline_comparison_improvement_with_quality(
        self,
    ) -> None:
        """Test improvement_percent calculation WITH quality_signal."""
        baseline = BaselineMetrics(
            latency_ms=1000.0,
            token_usage=500,
            quality_signal=0.80,
        )

        optimized = OptimizationMetrics.from_baseline_comparison(
            baseline=baseline,
            optimized_latency_ms=900.0,  # 10% faster
            optimized_token_usage=400,  # 20% token savings
            optimized_quality_signal=0.88,  # 10% quality improvement
        )

        # Expected: 0.5 * 10% (quality) + 0.3 * 20% (token) + 0.2 * 10% (latency)
        # = 5% + 6% + 2% = 13%
        assert optimized.improvement_percent is not None
        assert pytest.approx(optimized.improvement_percent, rel=0.01) == 13.0

    def test_optimization_metrics_from_baseline_comparison_roi_percent(self) -> None:
        """Test from_baseline_comparison calculates roi_percent correctly."""
        baseline = BaselineMetrics(
            latency_ms=1200.0,
            token_usage=500,
            cost_usd=0.015,
        )

        optimized = OptimizationMetrics.from_baseline_comparison(
            baseline=baseline,
            optimized_latency_ms=1100.0,
            optimized_token_usage=400,
            optimized_cost_usd=0.012,
        )

        # ROI = (0.015 - 0.012) / 0.015 * 100 = 20%
        assert optimized.roi_percent is not None
        assert pytest.approx(optimized.roi_percent, rel=0.01) == 20.0

    def test_optimization_metrics_from_baseline_comparison_no_roi_without_cost(
        self,
    ) -> None:
        """Test roi_percent is None when cost_usd not provided."""
        baseline = BaselineMetrics(latency_ms=1200.0, token_usage=500)

        optimized = OptimizationMetrics.from_baseline_comparison(
            baseline=baseline,
            optimized_latency_ms=1100.0,
            optimized_token_usage=400,
        )

        assert optimized.roi_percent is None
