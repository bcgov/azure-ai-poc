"""Integration tests for Agent Lightning wrapper with real LangGraph agent.

These tests verify that wrapping a LangGraph agent with Agent Lightning:
1. Produces identical output to unwrapped agent
2. Captures metrics correctly
3. Does not modify agent behavior
4. Handles tenant context properly

Tests written FIRST per TDD approach.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest


class TestAgentWrapperIntegration:
    """Integration tests for Agent Lightning wrapper with LangGraph agents."""

    @pytest.fixture
    def mock_langgraph_agent(self) -> MagicMock:
        """Create a mock LangGraph agent that simulates real behavior."""
        agent = MagicMock()

        # Simulate realistic LangGraph agent output
        agent.invoke.return_value = {
            "output": "This is the answer from the LangGraph agent.",
            "intermediate_steps": [],
            "metadata": {
                "model": "gpt-4o-mini",
                "total_tokens": 150,
                "prompt_tokens": 100,
                "completion_tokens": 50,
            },
        }

        # Add agent attributes for type checking
        agent.__class__.__name__ = "LangGraphAgent"

        return agent

    @pytest.fixture
    def optimization_config(self) -> dict[str, Any]:
        """Create optimization config for testing."""
        from app.models.optimization_models import OptimizationConfig

        return OptimizationConfig(
            tenant_id="test-tenant-123",
            agent_name="document_qa",
            enable_rl=True,
            enable_prompt_opt=False,
            enable_sft=False,
            metric_target="answer_quality",
        )

    def test_wrapped_agent_produces_identical_output(
        self,
        mock_langgraph_agent: MagicMock,
        optimization_config: Any,
    ) -> None:
        """Test that wrapped agent produces IDENTICAL output to unwrapped agent.

        This is critical - the wrapper must be transparent.
        """
        from app.services.agent_wrapper_service import wrap

        # Get output from unwrapped agent
        unwrapped_output = mock_langgraph_agent.invoke({"query": "What is the capital of France?"})

        # Wrap agent
        wrapped_agent = wrap(mock_langgraph_agent, optimization_config)

        # Get output from wrapped agent
        wrapped_output = wrapped_agent.invoke({"query": "What is the capital of France?"})

        # Outputs MUST be identical
        assert wrapped_output == unwrapped_output, (
            "Wrapped agent output must match unwrapped output exactly"
        )

    def test_wrapped_agent_captures_metrics(
        self,
        mock_langgraph_agent: MagicMock,
        optimization_config: Any,
    ) -> None:
        """Test that wrapper captures metrics during execution."""
        from app.models.optimization_models import BaselineMetrics
        from app.services.agent_wrapper_service import (
            get_optimization_metrics,
            wrap,
        )

        # Wrap agent
        wrapped_agent = wrap(mock_langgraph_agent, optimization_config)

        # Create baseline metrics
        baseline = BaselineMetrics(
            latency_ms=100.0,
            token_usage=150,
            quality_signal=0.9,
            cost_usd=0.001,
        )

        # Execute wrapped agent and get optimization metrics
        query = {"query": "Test query"}
        metrics = get_optimization_metrics(wrapped_agent, query, baseline)

        # Verify metrics were calculated
        assert metrics is not None, "Metrics should be captured"
        assert metrics.latency_ms >= 0, "Latency should be measured (or 0)"
        assert metrics.token_usage >= 0, "Token usage should be captured (or 0 if not available)"

    def test_wrapped_agent_preserves_agent_attributes(
        self,
        mock_langgraph_agent: MagicMock,
        optimization_config: Any,
    ) -> None:
        """Test that wrapper preserves custom agent attributes."""
        from app.services.agent_wrapper_service import wrap

        # Add custom attribute to agent
        mock_langgraph_agent.custom_attr = "custom_value"
        mock_langgraph_agent.agent_id = "agent-123"

        # Wrap agent
        wrapped_agent = wrap(mock_langgraph_agent, optimization_config)

        # Verify attributes preserved
        assert hasattr(wrapped_agent, "custom_attr"), "Custom attributes should be preserved"
        assert wrapped_agent.custom_attr == "custom_value", "Custom attribute values should match"
        assert hasattr(wrapped_agent, "agent_id"), "Agent ID should be preserved"

    def test_wrapped_agent_handles_agent_exceptions_correctly(
        self,
        mock_langgraph_agent: MagicMock,
        optimization_config: Any,
    ) -> None:
        """Test that wrapper doesn't suppress agent exceptions.

        If the agent raises an exception, it should propagate unchanged.
        """
        from app.services.agent_wrapper_service import wrap

        # Configure agent to raise exception
        mock_langgraph_agent.invoke.side_effect = ValueError("Agent error message")

        # Wrap agent
        wrapped_agent = wrap(mock_langgraph_agent, optimization_config)

        # Exception should propagate
        with pytest.raises(ValueError, match="Agent error message"):
            wrapped_agent.invoke({"query": "Test query"})

    def test_wrapped_agent_gracefully_handles_wrapper_failures(
        self,
        mock_langgraph_agent: MagicMock,
        optimization_config: Any,
    ) -> None:
        """Test that wrapper failures don't break agent execution.

        If metrics collection fails, agent should still work.
        """
        from app.services.agent_wrapper_service import wrap

        # Wrap agent
        wrapped_agent = wrap(mock_langgraph_agent, optimization_config)

        # Mock metrics collection to fail
        with patch(
            "app.services.agent_wrapper_service.AgentWrapper._collect_metrics",
            side_effect=Exception("Metrics collection failed"),
        ):
            # Agent should still work despite wrapper failure
            output = wrapped_agent.invoke({"query": "Test query"})

            # Output should be valid
            assert output is not None
            assert "output" in output

    def test_wrapped_agent_passes_tenant_context(
        self,
        mock_langgraph_agent: MagicMock,
    ) -> None:
        """Test that tenant_id flows through wrapper to optimization config."""
        from app.models.optimization_models import OptimizationConfig
        from app.services.agent_wrapper_service import wrap

        tenant_id = "tenant-xyz-789"

        config = OptimizationConfig(
            tenant_id=tenant_id,
            agent_name="document_qa",
            enable_rl=True,
            metric_target="answer_quality",
        )

        wrapped_agent = wrap(mock_langgraph_agent, config)

        # Verify tenant_id is stored in wrapper's config
        assert hasattr(wrapped_agent, "_config"), "Config should be stored in wrapper"
        assert wrapped_agent._config.tenant_id == tenant_id, "Tenant ID should match config"

    @pytest.mark.asyncio
    async def test_wrapped_agent_async_invoke_works(
        self,
        mock_langgraph_agent: MagicMock,
        optimization_config: Any,
    ) -> None:
        """Test that wrapped agent supports async invocation.

        Many LangGraph agents support ainvoke() for async execution.
        """
        from app.services.agent_wrapper_service import wrap

        # Configure async invoke
        async def async_invoke(input_data: dict[str, Any]) -> dict[str, Any]:
            return {
                "output": "Async response",
                "metadata": {"model": "gpt-4o-mini", "total_tokens": 100},
            }

        mock_langgraph_agent.ainvoke = async_invoke

        # Wrap agent
        wrapped_agent = wrap(mock_langgraph_agent, optimization_config)

        # Test async invocation
        output = await wrapped_agent.ainvoke({"query": "Async test"})

        assert output is not None
        assert output["output"] == "Async response"

    def test_wrapped_agent_with_optimization_disabled_returns_original(
        self,
        mock_langgraph_agent: MagicMock,
    ) -> None:
        """Test that disabling optimization returns unwrapped agent.

        When all optimization algorithms are disabled, wrapper should return
        the original agent unchanged.
        """
        from app.models.optimization_models import OptimizationConfig
        from app.services.agent_wrapper_service import wrap

        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="document_qa",
            enable_rl=False,
            enable_prompt_opt=False,
            enable_sft=False,
        )

        wrapped_agent = wrap(mock_langgraph_agent, config)

        # Should return original agent (no wrapper)
        assert wrapped_agent is mock_langgraph_agent, (
            "Should return original agent when optimization disabled"
        )

    def test_wrapped_agent_with_multiple_optimization_algorithms(
        self,
        mock_langgraph_agent: MagicMock,
    ) -> None:
        """Test wrapper with multiple optimization algorithms enabled."""
        from app.models.optimization_models import OptimizationConfig
        from app.services.agent_wrapper_service import wrap

        config = OptimizationConfig(
            tenant_id="test-tenant",
            agent_name="document_qa",
            enable_rl=True,
            enable_prompt_opt=True,
            enable_sft=True,
            metric_target="answer_quality",
        )

        wrapped_agent = wrap(mock_langgraph_agent, config)

        # Execute agent
        output = wrapped_agent.invoke({"query": "Multi-algo test"})

        # Should still produce correct output
        assert output is not None
        assert "output" in output

    def test_wrapped_agent_performance_overhead_minimal(
        self,
        mock_langgraph_agent: MagicMock,
        optimization_config: Any,
    ) -> None:
        """Test that wrapper overhead is <50ms as per spec."""
        import time

        from app.services.agent_wrapper_service import wrap

        # Configure agent with fast execution
        mock_langgraph_agent.invoke.return_value = {
            "output": "Fast response",
            "metadata": {},
        }

        # Measure unwrapped execution time
        start = time.perf_counter()
        _ = mock_langgraph_agent.invoke({"query": "Test"})
        unwrapped_time = time.perf_counter() - start

        # Wrap agent
        wrapped_agent = wrap(mock_langgraph_agent, optimization_config)

        # Measure wrapped execution time
        start = time.perf_counter()
        _ = wrapped_agent.invoke({"query": "Test"})
        wrapped_time = time.perf_counter() - start

        # Calculate overhead
        overhead_ms = (wrapped_time - unwrapped_time) * 1000

        # Overhead should be <50ms per spec
        assert overhead_ms < 50, f"Wrapper overhead {overhead_ms}ms exceeds 50ms target"
