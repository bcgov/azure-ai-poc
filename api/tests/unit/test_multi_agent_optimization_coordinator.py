"""Unit tests for multi-agent optimization coordinator.

Tests for T034: MultiAgentOptimizationCoordinator functionality.
"""

from app.models.optimization_models import BaselineMetrics
from app.services.multi_agent_optimization_coordinator import (
    MultiAgentOptimizationCoordinator,
)


class TestMultiAgentOptimizationCoordinator:
    """Unit tests for multi-agent optimization coordinator."""

    def test_coordinator_can_be_instantiated(self) -> None:
        """Test coordinator can be instantiated with tenant_id."""
        coordinator = MultiAgentOptimizationCoordinator(tenant_id="test-tenant")

        assert coordinator.tenant_id == "test-tenant"
        assert coordinator.config is not None
        assert coordinator.agent_names == [
            "query_planner",
            "document_analyzer",
            "answer_generator",
        ]

    def test_collect_metrics_from_all_agents(self) -> None:
        """Test collecting and aggregating metrics from all agents."""
        coordinator = MultiAgentOptimizationCoordinator(tenant_id="test-tenant")

        metrics_by_agent = {
            "query_planner": [
                BaselineMetrics(latency_ms=50.0, token_usage=30, quality_signal=0.8)
                for _ in range(10)
            ],
            "document_analyzer": [
                BaselineMetrics(latency_ms=150.0, token_usage=100, quality_signal=0.75)
                for _ in range(10)
            ],
            "answer_generator": [
                BaselineMetrics(latency_ms=250.0, token_usage=180, quality_signal=0.85)
                for _ in range(10)
            ],
        }

        aggregated = coordinator.collect_metrics_all_agents(metrics_by_agent)

        # All agents should have aggregated metrics
        assert "query_planner" in aggregated
        assert "document_analyzer" in aggregated
        assert "answer_generator" in aggregated

        # Check query planner metrics
        assert aggregated["query_planner"]["avg_latency_ms"] == 50.0
        assert aggregated["query_planner"]["avg_token_usage"] == 30.0
        assert aggregated["query_planner"]["avg_quality_signal"] == 0.8
        assert aggregated["query_planner"]["sample_count"] == 10

    def test_calculate_workflow_improvement(self) -> None:
        """Test calculating workflow-level improvement."""
        coordinator = MultiAgentOptimizationCoordinator(tenant_id="test-tenant")

        baseline = {
            "query_planner": [
                BaselineMetrics(latency_ms=100.0, token_usage=50, quality_signal=0.7)
                for _ in range(10)
            ],
            "document_analyzer": [
                BaselineMetrics(latency_ms=200.0, token_usage=150, quality_signal=0.75)
                for _ in range(10)
            ],
            "answer_generator": [
                BaselineMetrics(latency_ms=300.0, token_usage=200, quality_signal=0.80)
                for _ in range(10)
            ],
        }

        optimized = {
            "query_planner": [
                BaselineMetrics(latency_ms=80.0, token_usage=45, quality_signal=0.75)
                for _ in range(10)
            ],
            "document_analyzer": [
                BaselineMetrics(latency_ms=180.0, token_usage=140, quality_signal=0.80)
                for _ in range(10)
            ],
            "answer_generator": [
                BaselineMetrics(latency_ms=280.0, token_usage=190, quality_signal=0.85)
                for _ in range(10)
            ],
        }

        improvement = coordinator.calculate_workflow_improvement(baseline, optimized)

        # Should show improvement in all metrics
        assert improvement["latency_improvement_percent"] > 0
        assert improvement["token_improvement_percent"] > 0
        assert improvement["quality_improvement_percent"] > 0

    def test_trigger_selective_optimization_query_planner(self) -> None:
        """Test triggering optimization for query planner."""
        coordinator = MultiAgentOptimizationCoordinator(tenant_id="test-tenant")

        result = coordinator.trigger_selective_optimization("query_planner")

        assert result["status"] == "optimization_triggered"
        assert result["agent_name"] == "query_planner"
        assert result["algorithm"] == "rl"
        assert result["tenant_id"] == "test-tenant"

    def test_trigger_selective_optimization_document_analyzer(self) -> None:
        """Test triggering optimization for document analyzer."""
        coordinator = MultiAgentOptimizationCoordinator(tenant_id="test-tenant")

        result = coordinator.trigger_selective_optimization("document_analyzer")

        assert result["status"] == "optimization_triggered"
        assert result["agent_name"] == "document_analyzer"
        assert result["algorithm"] == "prompt_optimization"
        assert result["tenant_id"] == "test-tenant"

    def test_trigger_selective_optimization_answer_generator(self) -> None:
        """Test triggering optimization for answer generator."""
        coordinator = MultiAgentOptimizationCoordinator(tenant_id="test-tenant")

        result = coordinator.trigger_selective_optimization("answer_generator")

        assert result["status"] == "optimization_triggered"
        assert result["agent_name"] == "answer_generator"
        assert result["algorithm"] == "sft"
        assert result["tenant_id"] == "test-tenant"

    def test_empty_metrics_handled_gracefully(self) -> None:
        """Test empty metrics are handled gracefully."""
        coordinator = MultiAgentOptimizationCoordinator(tenant_id="test-tenant")

        aggregated = coordinator.collect_metrics_all_agents({})

        assert aggregated == {}

    def test_partial_agent_metrics(self) -> None:
        """Test handling metrics from only some agents."""
        coordinator = MultiAgentOptimizationCoordinator(tenant_id="test-tenant")

        metrics_by_agent = {
            "query_planner": [
                BaselineMetrics(latency_ms=50.0, token_usage=30, quality_signal=0.8)
                for _ in range(10)
            ],
            # document_analyzer missing
            "answer_generator": [
                BaselineMetrics(latency_ms=250.0, token_usage=180, quality_signal=0.85)
                for _ in range(10)
            ],
        }

        aggregated = coordinator.collect_metrics_all_agents(metrics_by_agent)

        # Only present agents should be in results
        assert "query_planner" in aggregated
        assert "document_analyzer" not in aggregated
        assert "answer_generator" in aggregated
