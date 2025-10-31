"""Unit tests for selective agent optimization.

T029: Tests for selecting and optimizing individual agents in multi-agent workflows.
"""

from app.models.optimization_models import BaselineMetrics, OptimizationConfig


class TestSelectiveAgentOptimization:
    """Unit tests for selective agent optimization."""

    def test_select_agent_for_optimization(self) -> None:
        """Test selecting a specific agent for optimization."""
        # Import will be added after implementation
        from app.core.selective_optimization_config import SelectiveOptimizationConfig

        config = SelectiveOptimizationConfig(tenant_id="test-tenant")

        # Select query planner for optimization
        agent_config = config.get_agent_config("query_planner")

        assert agent_config is not None
        assert isinstance(agent_config, OptimizationConfig)
        assert agent_config.agent_name == "query_planner"
        assert agent_config.tenant_id == "test-tenant"

    def test_query_planner_uses_rl_optimization(self) -> None:
        """Test query planner configured with RL optimization."""
        from app.core.selective_optimization_config import SelectiveOptimizationConfig

        config = SelectiveOptimizationConfig(tenant_id="test-tenant")
        agent_config = config.get_agent_config("query_planner")

        # Query planner should use RL for decision optimization
        assert agent_config.enable_rl is True
        assert agent_config.enable_prompt_opt is False
        assert agent_config.enable_sft is False

    def test_document_analyzer_uses_prompt_optimization(self) -> None:
        """Test document analyzer configured with prompt optimization."""
        from app.core.selective_optimization_config import SelectiveOptimizationConfig

        config = SelectiveOptimizationConfig(tenant_id="test-tenant")
        agent_config = config.get_agent_config("document_analyzer")

        # Document analyzer should use prompt optimization for retrieval
        assert agent_config.enable_rl is False
        assert agent_config.enable_prompt_opt is True
        assert agent_config.enable_sft is False

    def test_answer_generator_uses_sft_optimization(self) -> None:
        """Test answer generator configured with SFT optimization."""
        from app.core.selective_optimization_config import SelectiveOptimizationConfig

        config = SelectiveOptimizationConfig(tenant_id="test-tenant")
        agent_config = config.get_agent_config("answer_generator")

        # Answer generator should use SFT for quality improvement
        assert agent_config.enable_rl is False
        assert agent_config.enable_prompt_opt is False
        assert agent_config.enable_sft is True

    def test_per_agent_algorithm_configuration(self) -> None:
        """Test each agent has distinct algorithm configuration."""
        from app.core.selective_optimization_config import SelectiveOptimizationConfig

        config = SelectiveOptimizationConfig(tenant_id="test-tenant")

        query_planner = config.get_agent_config("query_planner")
        document_analyzer = config.get_agent_config("document_analyzer")
        answer_generator = config.get_agent_config("answer_generator")

        # Each agent should have different optimization strategy
        assert query_planner.enable_rl is True
        assert document_analyzer.enable_prompt_opt is True
        assert answer_generator.enable_sft is True

        # Verify they don't share configurations
        assert query_planner.agent_name != document_analyzer.agent_name
        assert document_analyzer.agent_name != answer_generator.agent_name

    def test_selective_optimization_doesnt_affect_other_agents(self) -> None:
        """Test optimizing one agent doesn't affect others."""
        from app.core.selective_optimization_config import SelectiveOptimizationConfig

        config = SelectiveOptimizationConfig(tenant_id="test-tenant")

        # Get independent configs
        config1 = config.get_agent_config("query_planner")
        config2 = config.get_agent_config("document_analyzer")

        # Modify config1 (simulate optimization)
        config1.metric_target = "latency"

        # config2 should remain unchanged
        assert config2.metric_target == "answer_quality"  # Default

    def test_unknown_agent_returns_default_config(self) -> None:
        """Test requesting config for unknown agent returns default."""
        from app.core.selective_optimization_config import SelectiveOptimizationConfig

        config = SelectiveOptimizationConfig(tenant_id="test-tenant")
        unknown_config = config.get_agent_config("unknown_agent")

        # Should return a valid config with default settings
        assert unknown_config is not None
        assert unknown_config.agent_name == "unknown_agent"
        assert unknown_config.tenant_id == "test-tenant"

    def test_selective_optimization_respects_tenant_isolation(self) -> None:
        """Test selective optimization maintains tenant isolation."""
        from app.core.selective_optimization_config import SelectiveOptimizationConfig

        # Tenant 1
        config1 = SelectiveOptimizationConfig(tenant_id="tenant-1")
        agent1 = config1.get_agent_config("query_planner")

        # Tenant 2
        config2 = SelectiveOptimizationConfig(tenant_id="tenant-2")
        agent2 = config2.get_agent_config("query_planner")

        # Same agent, different tenants
        assert agent1.tenant_id == "tenant-1"
        assert agent2.tenant_id == "tenant-2"
        assert agent1.tenant_id != agent2.tenant_id

    def test_agent_configs_can_collect_independent_metrics(self) -> None:
        """Test each agent can collect metrics independently."""
        from app.core.selective_optimization_config import SelectiveOptimizationConfig

        config = SelectiveOptimizationConfig(tenant_id="test-tenant")

        # Simulate metrics collection for different agents
        query_planner_config = config.get_agent_config("query_planner")
        document_analyzer_config = config.get_agent_config("document_analyzer")

        # Each config can be used independently
        query_metrics = BaselineMetrics(latency_ms=50.0, token_usage=100, quality_signal=0.8)
        doc_metrics = BaselineMetrics(latency_ms=200.0, token_usage=300, quality_signal=0.75)

        # Verify metrics are for different agents
        assert query_planner_config.agent_name == "query_planner"
        assert document_analyzer_config.agent_name == "document_analyzer"
        assert query_metrics.latency_ms != doc_metrics.latency_ms
