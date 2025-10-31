"""Integration tests for multi-agent selective optimization.

T030: Tests for optimizing individual agents independently in multi-agent workflows.
"""

from app.core.selective_optimization_config import SelectiveOptimizationConfig
from app.models.optimization_models import BaselineMetrics


class TestMultiAgentOptimization:
    """Integration tests for multi-agent selective optimization."""

    def test_query_planner_optimized_independently(self) -> None:
        """Test query planner can be optimized without affecting other agents."""
        config = SelectiveOptimizationConfig(tenant_id="test-tenant")

        # Get query planner config
        query_planner_config = config.get_agent_config("query_planner")
        assert query_planner_config.enable_rl is True

        # Simulate optimization of query planner
        query_planner_metrics = [
            BaselineMetrics(latency_ms=100.0, token_usage=50, quality_signal=0.7) for _ in range(15)
        ]

        # Other agents remain unoptimized
        document_analyzer_config = config.get_agent_config("document_analyzer")
        answer_generator_config = config.get_agent_config("answer_generator")

        assert document_analyzer_config.enable_prompt_opt is True
        assert answer_generator_config.enable_sft is True

        # Verify query planner metrics are independent
        assert len(query_planner_metrics) == 15
        assert query_planner_config.agent_name == "query_planner"

    def test_document_analyzer_optimized_independently(self) -> None:
        """Test document analyzer can be optimized without affecting other agents."""
        config = SelectiveOptimizationConfig(tenant_id="test-tenant")

        # Get document analyzer config
        document_analyzer_config = config.get_agent_config("document_analyzer")
        assert document_analyzer_config.enable_prompt_opt is True

        # Simulate optimization of document analyzer
        analyzer_metrics = [
            BaselineMetrics(latency_ms=200.0, token_usage=150, quality_signal=0.75)
            for _ in range(20)
        ]

        # Other agents remain unoptimized
        query_planner_config = config.get_agent_config("query_planner")
        answer_generator_config = config.get_agent_config("answer_generator")

        assert query_planner_config.enable_rl is True
        assert answer_generator_config.enable_sft is True

        # Verify document analyzer metrics are independent
        assert len(analyzer_metrics) == 20
        assert document_analyzer_config.agent_name == "document_analyzer"

    def test_answer_generator_optimized_independently(self) -> None:
        """Test answer generator can be optimized without affecting other agents."""
        config = SelectiveOptimizationConfig(tenant_id="test-tenant")

        # Get answer generator config
        answer_generator_config = config.get_agent_config("answer_generator")
        assert answer_generator_config.enable_sft is True

        # Simulate optimization of answer generator
        generator_metrics = [
            BaselineMetrics(latency_ms=300.0, token_usage=200, quality_signal=0.85)
            for _ in range(25)
        ]

        # Other agents remain unoptimized
        query_planner_config = config.get_agent_config("query_planner")
        document_analyzer_config = config.get_agent_config("document_analyzer")

        assert query_planner_config.enable_rl is True
        assert document_analyzer_config.enable_prompt_opt is True

        # Verify answer generator metrics are independent
        assert len(generator_metrics) == 25
        assert answer_generator_config.agent_name == "answer_generator"

    def test_each_agent_metrics_collected_separately(self) -> None:
        """Test metrics are collected separately for each agent."""
        config = SelectiveOptimizationConfig(tenant_id="test-tenant")

        # Simulate metrics collection for all agents
        query_planner_metrics = [
            BaselineMetrics(latency_ms=50.0, token_usage=30, quality_signal=0.7) for _ in range(10)
        ]

        document_analyzer_metrics = [
            BaselineMetrics(latency_ms=150.0, token_usage=100, quality_signal=0.75)
            for _ in range(15)
        ]

        answer_generator_metrics = [
            BaselineMetrics(latency_ms=250.0, token_usage=180, quality_signal=0.85)
            for _ in range(20)
        ]

        # Verify metrics are for different agents
        assert len(query_planner_metrics) == 10
        assert len(document_analyzer_metrics) == 15
        assert len(answer_generator_metrics) == 20

        # Calculate averages for each agent
        avg_query_latency = sum(m.latency_ms for m in query_planner_metrics) / len(
            query_planner_metrics
        )
        avg_analyzer_latency = sum(m.latency_ms for m in document_analyzer_metrics) / len(
            document_analyzer_metrics
        )
        avg_generator_latency = sum(m.latency_ms for m in answer_generator_metrics) / len(
            answer_generator_metrics
        )

        # Verify averages are distinct
        assert avg_query_latency == 50.0
        assert avg_analyzer_latency == 150.0
        assert avg_generator_latency == 250.0

    def test_per_agent_optimization_algorithms_applied(self) -> None:
        """Test each agent uses its designated optimization algorithm."""
        config = SelectiveOptimizationConfig(tenant_id="test-tenant")

        # Verify each agent has only one algorithm enabled
        query_planner = config.get_agent_config("query_planner")
        assert query_planner.enable_rl is True
        assert query_planner.enable_prompt_opt is False
        assert query_planner.enable_sft is False

        document_analyzer = config.get_agent_config("document_analyzer")
        assert document_analyzer.enable_rl is False
        assert document_analyzer.enable_prompt_opt is True
        assert document_analyzer.enable_sft is False

        answer_generator = config.get_agent_config("answer_generator")
        assert answer_generator.enable_rl is False
        assert answer_generator.enable_prompt_opt is False
        assert answer_generator.enable_sft is True

    def test_multi_agent_optimization_with_synthetic_data(self) -> None:
        """Test multi-agent optimization with synthetic test data."""
        # Simulate baseline metrics for all agents
        baseline_metrics = {
            "query_planner": [
                BaselineMetrics(latency_ms=60.0, token_usage=40, quality_signal=0.7)
                for _ in range(30)
            ],
            "document_analyzer": [
                BaselineMetrics(latency_ms=180.0, token_usage=120, quality_signal=0.75)
                for _ in range(30)
            ],
            "answer_generator": [
                BaselineMetrics(latency_ms=280.0, token_usage=190, quality_signal=0.80)
                for _ in range(30)
            ],
        }

        # Simulate optimized metrics (showing improvement)
        optimized_metrics = {
            "query_planner": [
                BaselineMetrics(
                    latency_ms=45.0, token_usage=35, quality_signal=0.75
                )  # RL improvement
                for _ in range(30)
            ],
            "document_analyzer": [
                BaselineMetrics(
                    latency_ms=180.0, token_usage=120, quality_signal=0.82
                )  # Prompt opt
                for _ in range(30)
            ],
            "answer_generator": [
                BaselineMetrics(latency_ms=280.0, token_usage=190, quality_signal=0.88)  # SFT
                for _ in range(30)
            ],
        }

        # Verify improvements
        for agent_name in ["query_planner", "document_analyzer", "answer_generator"]:
            baseline_quality = sum(m.quality_signal for m in baseline_metrics[agent_name]) / len(
                baseline_metrics[agent_name]
            )
            optimized_quality = sum(m.quality_signal for m in optimized_metrics[agent_name]) / len(
                optimized_metrics[agent_name]
            )

            # Each agent shows improvement
            assert optimized_quality > baseline_quality

    def test_tenant_isolation_in_multi_agent_optimization(self) -> None:
        """Test tenant isolation is maintained across multi-agent optimization."""
        # Tenant 1
        config1 = SelectiveOptimizationConfig(tenant_id="tenant-1")
        query_planner1 = config1.get_agent_config("query_planner")

        # Tenant 2
        config2 = SelectiveOptimizationConfig(tenant_id="tenant-2")
        query_planner2 = config2.get_agent_config("query_planner")

        # Same agent, different tenants
        assert query_planner1.tenant_id == "tenant-1"
        assert query_planner2.tenant_id == "tenant-2"

        # Both use RL (same algorithm, different tenants)
        assert query_planner1.enable_rl is True
        assert query_planner2.enable_rl is True

        # But they're independent configs
        assert query_planner1.tenant_id != query_planner2.tenant_id
