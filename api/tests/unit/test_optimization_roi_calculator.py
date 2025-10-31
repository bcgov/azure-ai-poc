"""Unit tests for optimization ROI calculator.

T026: Tests for ROI calculation functionality.
"""

from app.core.optimization_roi_calculator import ROICalculator
from app.models.optimization_models import BaselineMetrics


class TestROICalculator:
    """Unit tests for ROI calculator."""

    def test_roi_calculator_can_be_instantiated(self) -> None:
        """Test ROI calculator can be created."""
        calculator = ROICalculator()

        assert calculator.token_cost_per_1k == 0.002  # Default cost
        assert hasattr(calculator, "calculate_improvement_percent")
        assert hasattr(calculator, "calculate_token_savings")
        assert hasattr(calculator, "calculate_cost_roi")

    def test_roi_calculator_calculates_improvement_percent(self) -> None:
        """Test improvement percentage calculation."""
        calculator = ROICalculator()

        # Baseline metrics (before optimization)
        baseline = [
            BaselineMetrics(
                latency_ms=150.0,
                token_usage=300,
                quality_signal=0.65,
            )
            for _ in range(10)
        ]

        # Optimized metrics (after optimization)
        optimized = [
            BaselineMetrics(
                latency_ms=120.0,  # 20% faster
                token_usage=240,  # 20% fewer tokens
                quality_signal=0.80,  # ~23% better quality
            )
            for _ in range(10)
        ]

        improvement = calculator.calculate_improvement_percent(baseline, optimized)

        # Verify improvements calculated correctly
        assert improvement["quality_improvement"] > 20.0
        assert improvement["quality_improvement"] < 25.0
        assert improvement["latency_improvement"] == 20.0
        assert improvement["token_improvement"] == 20.0

    def test_roi_calculator_handles_no_improvement(self) -> None:
        """Test ROI calculator handles case with no improvement."""
        calculator = ROICalculator()

        # Identical metrics
        baseline = [
            BaselineMetrics(
                latency_ms=100.0,
                token_usage=200,
                quality_signal=0.75,
            )
            for _ in range(5)
        ]

        optimized = [
            BaselineMetrics(
                latency_ms=100.0,
                token_usage=200,
                quality_signal=0.75,
            )
            for _ in range(5)
        ]

        improvement = calculator.calculate_improvement_percent(baseline, optimized)

        # No improvement should be 0%
        assert improvement["quality_improvement"] == 0.0
        assert improvement["latency_improvement"] == 0.0
        assert improvement["token_improvement"] == 0.0

    def test_roi_calculator_calculates_token_savings(self) -> None:
        """Test token savings calculation."""
        calculator = ROICalculator()

        baseline = [
            BaselineMetrics(latency_ms=100.0, token_usage=300, quality_signal=0.7)
            for _ in range(10)
        ]

        optimized = [
            BaselineMetrics(latency_ms=80.0, token_usage=240, quality_signal=0.8) for _ in range(10)
        ]

        savings = calculator.calculate_token_savings(baseline, optimized, projected_queries=1000)

        # Verify token savings
        assert savings["baseline_tokens_per_query"] == 300.0
        assert savings["optimized_tokens_per_query"] == 240.0
        assert savings["tokens_saved_per_query"] == 60.0
        assert savings["total_tokens_saved"] == 60000  # 60 * 1000
        assert savings["projected_queries"] == 1000

    def test_roi_calculator_calculates_cost_roi(self) -> None:
        """Test cost ROI calculation."""
        calculator = ROICalculator(token_cost_per_1k=0.002)

        baseline = [
            BaselineMetrics(latency_ms=100.0, token_usage=300, quality_signal=0.7)
            for _ in range(10)
        ]

        optimized = [
            BaselineMetrics(latency_ms=80.0, token_usage=240, quality_signal=0.8) for _ in range(10)
        ]

        roi = calculator.calculate_cost_roi(
            baseline,
            optimized,
            projected_queries=10000,
            optimization_cost_usd=5.0,
        )

        # Baseline cost: 300 * 10000 / 1000 * 0.002 = $6.00
        # Optimized cost: 240 * 10000 / 1000 * 0.002 = $4.80
        # Cost saved: $6.00 - $4.80 = $1.20
        # Net ROI: $1.20 - $5.00 = -$3.80 (negative, optimization not yet paid off)

        assert roi["baseline_cost_usd"] == 6.0
        assert roi["optimized_cost_usd"] == 4.8
        assert roi["cost_saved_usd"] == 1.2
        assert roi["optimization_cost_usd"] == 5.0
        assert roi["net_roi_usd"] == -3.8
        assert roi["roi_percent"] < 0  # Negative ROI

    def test_roi_calculator_calculates_positive_roi(self) -> None:
        """Test positive ROI calculation with high volume."""
        calculator = ROICalculator(token_cost_per_1k=0.002)

        baseline = [
            BaselineMetrics(latency_ms=100.0, token_usage=500, quality_signal=0.6)
            for _ in range(10)
        ]

        optimized = [
            BaselineMetrics(latency_ms=80.0, token_usage=300, quality_signal=0.85)
            for _ in range(10)
        ]

        roi = calculator.calculate_cost_roi(
            baseline,
            optimized,
            projected_queries=100000,  # High volume
            optimization_cost_usd=10.0,
        )

        # Baseline cost: 500 * 100000 / 1000 * 0.002 = $100.00
        # Optimized cost: 300 * 100000 / 1000 * 0.002 = $60.00
        # Cost saved: $100.00 - $60.00 = $40.00
        # Net ROI: $40.00 - $10.00 = $30.00 (positive!)

        assert roi["baseline_cost_usd"] == 100.0
        assert roi["optimized_cost_usd"] == 60.0
        assert roi["cost_saved_usd"] == 40.0
        assert roi["net_roi_usd"] == 30.0
        assert roi["roi_percent"] == 300.0  # 300% ROI

    def test_roi_calculator_handles_empty_metrics(self) -> None:
        """Test ROI calculator handles empty metrics gracefully."""
        calculator = ROICalculator()

        improvement = calculator.calculate_improvement_percent([], [])
        savings = calculator.calculate_token_savings([], [], projected_queries=1000)
        roi = calculator.calculate_cost_roi(
            [], [], projected_queries=1000, optimization_cost_usd=10.0
        )

        # Should return zero/default values without crashing
        assert improvement["quality_improvement"] == 0.0
        assert improvement["latency_improvement"] == 0.0
        assert improvement["token_improvement"] == 0.0

        assert savings["total_tokens_saved"] == 0

        assert roi["net_roi_usd"] == -10.0  # Only optimization cost
        assert roi["roi_percent"] == -100.0

    def test_roi_calculator_supports_custom_token_cost(self) -> None:
        """Test ROI calculator supports custom token pricing."""
        # Premium model pricing
        calculator = ROICalculator(token_cost_per_1k=0.01)

        baseline = [
            BaselineMetrics(latency_ms=100.0, token_usage=1000, quality_signal=0.7)
            for _ in range(10)
        ]

        optimized = [
            BaselineMetrics(latency_ms=80.0, token_usage=800, quality_signal=0.8) for _ in range(10)
        ]

        roi = calculator.calculate_cost_roi(
            baseline,
            optimized,
            projected_queries=1000,
            optimization_cost_usd=5.0,
        )

        # Baseline cost: 1000 * 1000 / 1000 * 0.01 = $10.00
        # Optimized cost: 800 * 1000 / 1000 * 0.01 = $8.00
        # Cost saved: $10.00 - $8.00 = $2.00
        # Net ROI: $2.00 - $5.00 = -$3.00

        assert roi["baseline_cost_usd"] == 10.0
        assert roi["optimized_cost_usd"] == 8.0
        assert roi["cost_saved_usd"] == 2.0
        assert roi["net_roi_usd"] == -3.0
