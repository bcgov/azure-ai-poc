"""Integration tests for ROI metrics calculation accuracy.

Tests the ROICalculator class to ensure accurate calculations for:
- Improvement percentages (quality, latency, token usage)
- Token savings calculations
- Cost estimation and ROI calculations
"""

import pytest

from app.core.optimization_roi_calculator import ROICalculator
from app.models.optimization_models import BaselineMetrics


class TestROIMetricsCalculation:
    """Integration tests for ROI calculator accuracy."""

    @pytest.fixture
    def calculator(self) -> ROICalculator:
        """Create ROI calculator with standard token cost."""
        return ROICalculator(token_cost_per_1k=0.002)

    @pytest.fixture
    def baseline_metrics(self) -> list[BaselineMetrics]:
        """Create baseline metrics for testing.

        Returns:
            List of 5 baseline metrics with:
            - quality_signal: 0.75
            - latency_ms: 1000
            - token_usage: 500
        """
        return [
            BaselineMetrics(
                quality_signal=0.75,
                latency_ms=1000,
                token_usage=500,
            )
            for _ in range(5)
        ]

    @pytest.fixture
    def optimized_metrics(self) -> list[BaselineMetrics]:
        """Create optimized metrics for testing.

        Returns:
            List of 5 optimized metrics with:
            - quality_signal: 0.90 (20% improvement)
            - latency_ms: 800 (20% improvement)
            - token_usage: 400 (20% improvement)
        """
        return [
            BaselineMetrics(
                quality_signal=0.90,
                latency_ms=800,
                token_usage=400,
            )
            for _ in range(5)
        ]

    def test_improvement_percent_calculation_accuracy(
        self,
        calculator: ROICalculator,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
    ) -> None:
        """Test improvement percentage calculation accuracy.

        Verifies:
        - Quality improvement is 20% (0.75 -> 0.90)
        - Latency improvement is 20% (1000ms -> 800ms)
        - Token improvement is 20% (500 -> 400 tokens)
        """
        improvement = calculator.calculate_improvement_percent(baseline_metrics, optimized_metrics)

        # Verify quality improvement
        assert "quality_improvement" in improvement
        assert improvement["quality_improvement"] == pytest.approx(20.0, abs=0.1)

        # Verify latency improvement
        assert "latency_improvement" in improvement
        assert improvement["latency_improvement"] == pytest.approx(20.0, abs=0.1)

        # Verify token improvement
        assert "token_improvement" in improvement
        assert improvement["token_improvement"] == pytest.approx(20.0, abs=0.1)

    def test_improvement_percent_with_negative_improvement(
        self, calculator: ROICalculator, baseline_metrics: list[BaselineMetrics]
    ) -> None:
        """Test improvement percentage calculation with regression.

        Verifies that negative improvements (regressions) are calculated correctly.
        """
        # Create metrics that are worse than baseline
        worse_metrics = [
            BaselineMetrics(
                quality_signal=0.60,  # Worse than 0.75
                latency_ms=1200,  # Worse than 1000
                token_usage=600,  # Worse than 500
            )
            for _ in range(5)
        ]

        improvement = calculator.calculate_improvement_percent(baseline_metrics, worse_metrics)

        # All improvements should be negative
        assert improvement["quality_improvement"] < 0
        assert improvement["latency_improvement"] < 0
        assert improvement["token_improvement"] < 0

    def test_improvement_percent_with_empty_metrics(self, calculator: ROICalculator) -> None:
        """Test improvement percentage with empty metrics lists.

        Verifies that calculator handles edge case gracefully.
        """
        improvement = calculator.calculate_improvement_percent([], [])

        assert improvement == {
            "quality_improvement": 0.0,
            "latency_improvement": 0.0,
            "token_improvement": 0.0,
        }

    def test_token_savings_calculation_accuracy(
        self,
        calculator: ROICalculator,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
    ) -> None:
        """Test token savings calculation accuracy.

        Verifies:
        - Baseline tokens per query: 500
        - Optimized tokens per query: 400
        - Tokens saved per query: 100
        - Total tokens saved (1000 queries): 100,000
        """
        savings = calculator.calculate_token_savings(
            baseline_metrics, optimized_metrics, projected_queries=1000
        )

        # Verify token averages
        assert savings["baseline_tokens_per_query"] == pytest.approx(500.0, abs=0.1)
        assert savings["optimized_tokens_per_query"] == pytest.approx(400.0, abs=0.1)

        # Verify savings calculations
        assert savings["tokens_saved_per_query"] == pytest.approx(100.0, abs=0.1)
        assert savings["total_tokens_saved"] == 100000
        assert savings["projected_queries"] == 1000

    def test_token_savings_with_different_projections(
        self,
        calculator: ROICalculator,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
    ) -> None:
        """Test token savings with different projection scales.

        Verifies that projected savings scale correctly:
        - 10 queries: 1,000 tokens saved
        - 1,000 queries: 100,000 tokens saved
        - 100,000 queries: 10,000,000 tokens saved
        """
        # Test small projection
        savings_small = calculator.calculate_token_savings(
            baseline_metrics, optimized_metrics, projected_queries=10
        )
        assert savings_small["total_tokens_saved"] == 1000

        # Test medium projection
        savings_medium = calculator.calculate_token_savings(
            baseline_metrics, optimized_metrics, projected_queries=1000
        )
        assert savings_medium["total_tokens_saved"] == 100000

        # Test large projection
        savings_large = calculator.calculate_token_savings(
            baseline_metrics, optimized_metrics, projected_queries=100000
        )
        assert savings_large["total_tokens_saved"] == 10000000

    def test_token_savings_with_empty_metrics(self, calculator: ROICalculator) -> None:
        """Test token savings with empty metrics lists."""
        savings = calculator.calculate_token_savings([], [], projected_queries=1000)

        assert savings == {
            "baseline_tokens_per_query": 0,
            "optimized_tokens_per_query": 0,
            "tokens_saved_per_query": 0,
            "total_tokens_saved": 0,
            "projected_queries": 1000,
        }

    def test_cost_roi_calculation_accuracy(
        self,
        calculator: ROICalculator,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
    ) -> None:
        """Test cost ROI calculation accuracy.

        With 1000 queries and token_cost_per_1k=$0.002:
        - Baseline cost: (500 tokens * 1000 queries / 1000) * $0.002 = $1.00
        - Optimized cost: (400 tokens * 1000 queries / 1000) * $0.002 = $0.80
        - Cost saved: $0.20
        - Optimization cost: $10.00
        - Net ROI: $0.20 - $10.00 = -$9.80
        - ROI percent: (-9.80 / 10.00) * 100 = -98%
        """
        roi = calculator.calculate_cost_roi(
            baseline_metrics,
            optimized_metrics,
            projected_queries=1000,
            optimization_cost_usd=10.0,
        )

        # Verify costs
        assert roi["baseline_cost_usd"] == pytest.approx(1.0, abs=0.01)
        assert roi["optimized_cost_usd"] == pytest.approx(0.8, abs=0.01)
        assert roi["cost_saved_usd"] == pytest.approx(0.2, abs=0.01)

        # Verify ROI calculations
        assert roi["optimization_cost_usd"] == pytest.approx(10.0, abs=0.01)
        assert roi["net_roi_usd"] == pytest.approx(-9.8, abs=0.01)
        assert roi["roi_percent"] == pytest.approx(-98.0, abs=0.1)

    def test_cost_roi_with_positive_roi(
        self,
        calculator: ROICalculator,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
    ) -> None:
        """Test cost ROI calculation with positive ROI.

        With 100,000 queries and token_cost_per_1k=$0.002:
        - Baseline cost: (500 * 100000 / 1000) * $0.002 = $100.00
        - Optimized cost: (400 * 100000 / 1000) * $0.002 = $80.00
        - Cost saved: $20.00
        - Optimization cost: $10.00
        - Net ROI: $20.00 - $10.00 = $10.00
        - ROI percent: ($10.00 / $10.00) * 100 = 100%
        """
        roi = calculator.calculate_cost_roi(
            baseline_metrics,
            optimized_metrics,
            projected_queries=100000,
            optimization_cost_usd=10.0,
        )

        # Verify positive ROI
        assert roi["baseline_cost_usd"] == pytest.approx(100.0, abs=0.01)
        assert roi["optimized_cost_usd"] == pytest.approx(80.0, abs=0.01)
        assert roi["cost_saved_usd"] == pytest.approx(20.0, abs=0.01)
        assert roi["net_roi_usd"] == pytest.approx(10.0, abs=0.01)
        assert roi["roi_percent"] == pytest.approx(100.0, abs=0.1)

    def test_cost_roi_with_high_token_cost(
        self, baseline_metrics: list[BaselineMetrics], optimized_metrics: list[BaselineMetrics]
    ) -> None:
        """Test cost ROI with different token pricing.

        Tests with higher token cost ($0.01 per 1k tokens):
        - Baseline cost: (500 * 1000 / 1000) * $0.01 = $5.00
        - Optimized cost: (400 * 1000 / 1000) * $0.01 = $4.00
        - Cost saved: $1.00
        - Optimization cost: $0.50
        - Net ROI: $1.00 - $0.50 = $0.50
        - ROI percent: ($0.50 / $0.50) * 100 = 100%
        """
        calculator_high_cost = ROICalculator(token_cost_per_1k=0.01)

        roi = calculator_high_cost.calculate_cost_roi(
            baseline_metrics,
            optimized_metrics,
            projected_queries=1000,
            optimization_cost_usd=0.5,
        )

        # Verify costs with higher token pricing
        assert roi["baseline_cost_usd"] == pytest.approx(5.0, abs=0.01)
        assert roi["optimized_cost_usd"] == pytest.approx(4.0, abs=0.01)
        assert roi["cost_saved_usd"] == pytest.approx(1.0, abs=0.01)
        assert roi["net_roi_usd"] == pytest.approx(0.5, abs=0.01)
        assert roi["roi_percent"] == pytest.approx(100.0, abs=0.1)

    def test_cost_roi_with_empty_metrics(self, calculator: ROICalculator) -> None:
        """Test cost ROI with empty metrics lists."""
        roi = calculator.calculate_cost_roi(
            [], [], projected_queries=1000, optimization_cost_usd=10.0
        )

        assert roi == {
            "baseline_cost_usd": 0.0,
            "optimized_cost_usd": 0.0,
            "cost_saved_usd": 0.0,
            "optimization_cost_usd": 10.0,
            "net_roi_usd": -10.0,
            "roi_percent": -100.0,
            "projected_queries": 1000,
        }

    def test_cost_roi_with_zero_optimization_cost(
        self,
        calculator: ROICalculator,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
    ) -> None:
        """Test cost ROI when optimization cost is zero.

        Verifies that ROI calculation handles zero optimization cost gracefully.
        When optimization cost is 0 and there are savings, ROI is infinity.
        """
        roi = calculator.calculate_cost_roi(
            baseline_metrics,
            optimized_metrics,
            projected_queries=1000,
            optimization_cost_usd=0.0,
        )

        # With zero optimization cost, net ROI equals cost saved
        assert roi["net_roi_usd"] == roi["cost_saved_usd"]
        # ROI percent is infinity when optimization cost is 0 and there are savings
        assert roi["roi_percent"] == float("inf")

    def test_integration_all_calculations_together(
        self,
        calculator: ROICalculator,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
    ) -> None:
        """Test all ROI calculations together in an integration scenario.

        Simulates a real-world optimization scenario:
        1. Calculate improvement percentages
        2. Calculate token savings
        3. Calculate cost ROI

        Verifies that all calculations are consistent with each other.
        """
        # Step 1: Calculate improvements
        improvement = calculator.calculate_improvement_percent(baseline_metrics, optimized_metrics)
        assert improvement["token_improvement"] == pytest.approx(20.0, abs=0.1)

        # Step 2: Calculate token savings
        savings = calculator.calculate_token_savings(
            baseline_metrics, optimized_metrics, projected_queries=100000
        )
        assert savings["tokens_saved_per_query"] == pytest.approx(100.0, abs=0.1)
        assert savings["total_tokens_saved"] == 10000000

        # Step 3: Calculate cost ROI
        roi = calculator.calculate_cost_roi(
            baseline_metrics,
            optimized_metrics,
            projected_queries=100000,
            optimization_cost_usd=10.0,
        )
        assert roi["cost_saved_usd"] == pytest.approx(20.0, abs=0.01)
        assert roi["net_roi_usd"] > 0  # Positive ROI
        assert roi["roi_percent"] > 0  # Positive ROI percentage

        # Verify consistency: cost_saved_usd should equal
        # (tokens_saved * token_cost_per_1k) / 1000
        expected_cost_saved = (savings["total_tokens_saved"] / 1000) * calculator.token_cost_per_1k
        assert roi["cost_saved_usd"] == pytest.approx(expected_cost_saved, abs=0.01)
