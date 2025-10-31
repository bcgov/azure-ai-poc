"""Integration tests for OptimizationAnalyticsService.

Tests the analytics service to ensure accurate generation of:
- Improvement reports
- Cost impact analyses
- ROI dashboard data
"""

import pytest

from app.models.optimization_models import BaselineMetrics
from app.services.optimization_analytics_service import OptimizationAnalyticsService


class TestOptimizationAnalyticsService:
    """Integration tests for optimization analytics service."""

    @pytest.fixture
    def service(self) -> OptimizationAnalyticsService:
        """Create analytics service for testing."""
        return OptimizationAnalyticsService(tenant_id="test-tenant-123", token_cost_per_1k=0.002)

    @pytest.fixture
    def baseline_metrics(self) -> list[BaselineMetrics]:
        """Create baseline metrics for testing."""
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
        """Create optimized metrics for testing."""
        return [
            BaselineMetrics(
                quality_signal=0.90,
                latency_ms=800,
                token_usage=400,
            )
            for _ in range(5)
        ]

    def test_generate_improvement_report_structure(
        self,
        service: OptimizationAnalyticsService,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
    ) -> None:
        """Test improvement report structure and required fields."""
        report = service.generate_improvement_report(
            agent_name="query_planner",
            baseline_metrics=baseline_metrics,
            optimized_metrics=optimized_metrics,
        )

        # Verify top-level structure
        assert "agent_name" in report
        assert report["agent_name"] == "query_planner"
        assert "tenant_id" in report
        assert report["tenant_id"] == "test-tenant-123"
        assert "baseline_summary" in report
        assert "optimized_summary" in report
        assert "improvements" in report
        assert "timestamp" in report

        # Verify baseline summary
        baseline = report["baseline_summary"]
        assert "avg_quality_signal" in baseline
        assert "avg_latency_ms" in baseline
        assert "avg_token_usage" in baseline
        assert "sample_count" in baseline

        # Verify optimized summary
        optimized = report["optimized_summary"]
        assert "avg_quality_signal" in optimized
        assert "avg_latency_ms" in optimized
        assert "avg_token_usage" in optimized
        assert "sample_count" in optimized

        # Verify improvements
        improvements = report["improvements"]
        assert "quality_improvement" in improvements
        assert "latency_improvement" in improvements
        assert "token_improvement" in improvements

    def test_generate_improvement_report_accuracy(
        self,
        service: OptimizationAnalyticsService,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
    ) -> None:
        """Test improvement report calculation accuracy."""
        report = service.generate_improvement_report(
            agent_name="query_planner",
            baseline_metrics=baseline_metrics,
            optimized_metrics=optimized_metrics,
        )

        # Verify baseline summary values
        baseline = report["baseline_summary"]
        assert baseline["avg_quality_signal"] == pytest.approx(0.75, abs=0.01)
        assert baseline["avg_latency_ms"] == pytest.approx(1000.0, abs=0.1)
        assert baseline["avg_token_usage"] == pytest.approx(500.0, abs=0.1)
        assert baseline["sample_count"] == 5.0

        # Verify optimized summary values
        optimized = report["optimized_summary"]
        assert optimized["avg_quality_signal"] == pytest.approx(0.90, abs=0.01)
        assert optimized["avg_latency_ms"] == pytest.approx(800.0, abs=0.1)
        assert optimized["avg_token_usage"] == pytest.approx(400.0, abs=0.1)
        assert optimized["sample_count"] == 5.0

        # Verify improvements (all should be 20%)
        improvements = report["improvements"]
        assert improvements["quality_improvement"] == pytest.approx(20.0, abs=0.1)
        assert improvements["latency_improvement"] == pytest.approx(20.0, abs=0.1)
        assert improvements["token_improvement"] == pytest.approx(20.0, abs=0.1)

    def test_calculate_cost_impact_structure(
        self,
        service: OptimizationAnalyticsService,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
    ) -> None:
        """Test cost impact calculation structure and required fields."""
        impact = service.calculate_cost_impact(
            agent_name="query_planner",
            baseline_metrics=baseline_metrics,
            optimized_metrics=optimized_metrics,
            projected_queries=10000,
            optimization_cost_usd=10.0,
        )

        # Verify top-level structure
        assert "agent_name" in impact
        assert impact["agent_name"] == "query_planner"
        assert "tenant_id" in impact
        assert impact["tenant_id"] == "test-tenant-123"
        assert "token_savings" in impact
        assert "cost_roi" in impact
        assert "projected_queries" in impact
        assert impact["projected_queries"] == 10000
        assert "breakeven_queries" in impact
        assert "timestamp" in impact

        # Verify token savings structure
        token_savings = impact["token_savings"]
        assert "baseline_tokens_per_query" in token_savings
        assert "optimized_tokens_per_query" in token_savings
        assert "tokens_saved_per_query" in token_savings
        assert "total_tokens_saved" in token_savings

        # Verify cost ROI structure
        cost_roi = impact["cost_roi"]
        assert "baseline_cost_usd" in cost_roi
        assert "optimized_cost_usd" in cost_roi
        assert "cost_saved_usd" in cost_roi
        assert "optimization_cost_usd" in cost_roi
        assert "net_roi_usd" in cost_roi
        assert "roi_percent" in cost_roi

    def test_calculate_cost_impact_accuracy(
        self,
        service: OptimizationAnalyticsService,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
    ) -> None:
        """Test cost impact calculation accuracy."""
        impact = service.calculate_cost_impact(
            agent_name="query_planner",
            baseline_metrics=baseline_metrics,
            optimized_metrics=optimized_metrics,
            projected_queries=10000,
            optimization_cost_usd=5.0,
        )

        # Verify token savings
        # 100 tokens saved per query * 10,000 queries = 1,000,000 total tokens saved
        token_savings = impact["token_savings"]
        assert token_savings["tokens_saved_per_query"] == pytest.approx(100.0, abs=0.1)
        assert token_savings["total_tokens_saved"] == 1000000

        # Verify cost ROI
        # Baseline: (500 * 10000 / 1000) * $0.002 = $10.00
        # Optimized: (400 * 10000 / 1000) * $0.002 = $8.00
        # Saved: $2.00
        # Net ROI: $2.00 - $5.00 = -$3.00
        # ROI %: (-3.00 / 5.00) * 100 = -60%
        cost_roi = impact["cost_roi"]
        assert cost_roi["baseline_cost_usd"] == pytest.approx(10.0, abs=0.01)
        assert cost_roi["optimized_cost_usd"] == pytest.approx(8.0, abs=0.01)
        assert cost_roi["cost_saved_usd"] == pytest.approx(2.0, abs=0.01)
        assert cost_roi["net_roi_usd"] == pytest.approx(-3.0, abs=0.01)
        assert cost_roi["roi_percent"] == pytest.approx(-60.0, abs=0.1)

        # Verify breakeven queries
        # Need to save $5.00 / $0.0002 per query = 25,000 queries
        assert impact["breakeven_queries"] == 25000

    def test_calculate_cost_impact_with_positive_roi(
        self,
        service: OptimizationAnalyticsService,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
    ) -> None:
        """Test cost impact with positive ROI scenario."""
        impact = service.calculate_cost_impact(
            agent_name="query_planner",
            baseline_metrics=baseline_metrics,
            optimized_metrics=optimized_metrics,
            projected_queries=100000,  # Large volume
            optimization_cost_usd=10.0,
        )

        # With 100k queries: saves $20, costs $10, net ROI = $10 (100%)
        cost_roi = impact["cost_roi"]
        assert cost_roi["cost_saved_usd"] == pytest.approx(20.0, abs=0.01)
        assert cost_roi["net_roi_usd"] == pytest.approx(10.0, abs=0.01)
        assert cost_roi["roi_percent"] == pytest.approx(100.0, abs=0.1)

    def test_generate_roi_dashboard_data_structure(
        self,
        service: OptimizationAnalyticsService,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
    ) -> None:
        """Test ROI dashboard data structure."""
        dashboard = service.generate_roi_dashboard_data(
            agent_name="query_planner",
            baseline_metrics=baseline_metrics,
            optimized_metrics=optimized_metrics,
            projected_queries=100000,
            optimization_cost_usd=10.0,
        )

        # Verify top-level structure
        assert "agent_name" in dashboard
        assert dashboard["agent_name"] == "query_planner"
        assert "tenant_id" in dashboard
        assert dashboard["tenant_id"] == "test-tenant-123"
        assert "summary" in dashboard
        assert "improvements" in dashboard
        assert "cost_impact" in dashboard
        assert "recommendations" in dashboard
        assert "projected_queries" in dashboard
        assert "timestamp" in dashboard

        # Verify summary structure
        summary = dashboard["summary"]
        assert "overall_improvement" in summary
        assert "quality_improvement" in summary
        assert "token_improvement" in summary
        assert "latency_improvement" in summary
        assert "net_roi_usd" in summary
        assert "roi_percent" in summary
        assert "tokens_saved" in summary
        assert "cost_saved_usd" in summary

        # Verify improvements structure
        improvements = dashboard["improvements"]
        assert "quality" in improvements
        assert "token_efficiency" in improvements
        assert "latency" in improvements

        # Verify cost impact structure
        cost_impact = dashboard["cost_impact"]
        assert "tokens_saved" in cost_impact
        assert "cost_saved_usd" in cost_impact
        assert "optimization_cost_usd" in cost_impact
        assert "net_roi_usd" in cost_impact
        assert "roi_percent" in cost_impact
        assert "breakeven_queries" in cost_impact

        # Verify recommendations is a list
        assert isinstance(dashboard["recommendations"], list)
        assert len(dashboard["recommendations"]) > 0

    def test_generate_roi_dashboard_data_overall_improvement(
        self,
        service: OptimizationAnalyticsService,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
    ) -> None:
        """Test overall improvement calculation in dashboard.

        Overall improvement is weighted:
        - 50% quality
        - 30% token efficiency
        - 20% latency

        With all at 20%: (0.5 * 20) + (0.3 * 20) + (0.2 * 20) = 20%
        """
        dashboard = service.generate_roi_dashboard_data(
            agent_name="query_planner",
            baseline_metrics=baseline_metrics,
            optimized_metrics=optimized_metrics,
            projected_queries=100000,
            optimization_cost_usd=10.0,
        )

        # Verify overall improvement is weighted average
        summary = dashboard["summary"]
        assert summary["overall_improvement"] == pytest.approx(20.0, abs=0.1)

    def test_generate_roi_dashboard_data_recommendations_positive_roi(
        self,
        service: OptimizationAnalyticsService,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
    ) -> None:
        """Test recommendations with positive ROI."""
        dashboard = service.generate_roi_dashboard_data(
            agent_name="query_planner",
            baseline_metrics=baseline_metrics,
            optimized_metrics=optimized_metrics,
            projected_queries=100000,  # High volume = positive ROI
            optimization_cost_usd=10.0,
        )

        recommendations = dashboard["recommendations"]
        # Should recommend continuing optimization with positive ROI
        positive_roi_rec = any(
            "Positive ROI" in rec and "continue optimization" in rec for rec in recommendations
        )
        assert positive_roi_rec

        # Should recommend wider rollout with >20% quality improvement
        wider_rollout_rec = any("wider rollout" in rec for rec in recommendations)
        assert wider_rollout_rec

        # Should recommend updating budgets with >30% token improvement
        # (Our test has 20% token improvement, so this should NOT appear)
        budget_rec = any("token allocation budgets" in rec for rec in recommendations)
        assert not budget_rec

    def test_generate_roi_dashboard_data_recommendations_negative_roi(
        self,
        service: OptimizationAnalyticsService,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
    ) -> None:
        """Test recommendations with negative ROI."""
        dashboard = service.generate_roi_dashboard_data(
            agent_name="query_planner",
            baseline_metrics=baseline_metrics,
            optimized_metrics=optimized_metrics,
            projected_queries=1000,  # Low volume = negative ROI
            optimization_cost_usd=10.0,
        )

        recommendations = dashboard["recommendations"]
        # Should mention breakeven point
        breakeven_rec = any("break even" in rec for rec in recommendations)
        assert breakeven_rec

    def test_generate_roi_dashboard_data_recommendations_quality_degradation(
        self,
        service: OptimizationAnalyticsService,
        baseline_metrics: list[BaselineMetrics],
    ) -> None:
        """Test recommendations with quality degradation."""
        # Create metrics with quality degradation
        worse_metrics = [
            BaselineMetrics(
                quality_signal=0.60,  # Worse than baseline 0.75
                latency_ms=800,
                token_usage=400,
            )
            for _ in range(5)
        ]

        dashboard = service.generate_roi_dashboard_data(
            agent_name="query_planner",
            baseline_metrics=baseline_metrics,
            optimized_metrics=worse_metrics,
            projected_queries=100000,
            optimization_cost_usd=10.0,
        )

        recommendations = dashboard["recommendations"]
        # Should warn about quality degradation
        quality_warning = any(
            "Quality degradation" in rec and "review optimization algorithm" in rec
            for rec in recommendations
        )
        assert quality_warning

    def test_analytics_service_with_empty_metrics(
        self, service: OptimizationAnalyticsService
    ) -> None:
        """Test analytics service with empty metrics lists."""
        report = service.generate_improvement_report(
            agent_name="query_planner", baseline_metrics=[], optimized_metrics=[]
        )

        # Should return zero improvements
        assert report["improvements"]["quality_improvement"] == 0.0
        assert report["improvements"]["latency_improvement"] == 0.0
        assert report["improvements"]["token_improvement"] == 0.0

        # Summaries should be empty
        assert report["baseline_summary"] == {}
        assert report["optimized_summary"] == {}

    def test_analytics_service_tenant_isolation(
        self,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
    ) -> None:
        """Test that analytics service maintains tenant isolation."""
        # Create service for different tenant
        service1 = OptimizationAnalyticsService(tenant_id="tenant-1")
        service2 = OptimizationAnalyticsService(tenant_id="tenant-2")

        # Generate reports for both tenants
        report1 = service1.generate_improvement_report(
            agent_name="agent-1",
            baseline_metrics=baseline_metrics,
            optimized_metrics=optimized_metrics,
        )

        report2 = service2.generate_improvement_report(
            agent_name="agent-2",
            baseline_metrics=baseline_metrics,
            optimized_metrics=optimized_metrics,
        )

        # Verify tenant IDs are isolated
        assert report1["tenant_id"] == "tenant-1"
        assert report2["tenant_id"] == "tenant-2"
        assert report1["tenant_id"] != report2["tenant_id"]

    def test_analytics_service_integration_scenario(
        self,
        service: OptimizationAnalyticsService,
        baseline_metrics: list[BaselineMetrics],
        optimized_metrics: list[BaselineMetrics],
    ) -> None:
        """Test full analytics workflow integration.

        Simulates a complete workflow:
        1. Generate improvement report
        2. Calculate cost impact
        3. Generate ROI dashboard data
        """
        # Step 1: Generate improvement report
        improvement_report = service.generate_improvement_report(
            agent_name="query_planner",
            baseline_metrics=baseline_metrics,
            optimized_metrics=optimized_metrics,
        )
        assert improvement_report["improvements"]["quality_improvement"] > 0

        # Step 2: Calculate cost impact
        cost_impact = service.calculate_cost_impact(
            agent_name="query_planner",
            baseline_metrics=baseline_metrics,
            optimized_metrics=optimized_metrics,
            projected_queries=100000,
            optimization_cost_usd=10.0,
        )
        assert cost_impact["cost_roi"]["net_roi_usd"] > 0

        # Step 3: Generate dashboard data (combines above)
        dashboard = service.generate_roi_dashboard_data(
            agent_name="query_planner",
            baseline_metrics=baseline_metrics,
            optimized_metrics=optimized_metrics,
            projected_queries=100000,
            optimization_cost_usd=10.0,
        )

        # Verify consistency across all three outputs
        assert (
            dashboard["improvements"]["quality"]
            == improvement_report["improvements"]["quality_improvement"]
        )
        assert dashboard["cost_impact"]["net_roi_usd"] == cost_impact["cost_roi"]["net_roi_usd"]
        assert dashboard["summary"]["overall_improvement"] > 0
        assert len(dashboard["recommendations"]) > 0
