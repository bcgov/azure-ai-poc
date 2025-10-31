"""Test cases for agent_wrapper_service.py (Agent wrapper service).

This module tests the core agent wrapper service that wraps LangGraph/LangChain
agents with Agent Lightning optimization. Tests written FIRST per TDD approach.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.optimization_models import BaselineMetrics, OptimizationConfig


class TestAgentWrapper:
    """Test cases for AgentWrapper class."""

    @pytest.fixture
    def mock_agent(self) -> MagicMock:
        """Create a mock LangGraph agent."""
        agent = MagicMock()
        agent.invoke = MagicMock(return_value={"output": "test response"})
        agent.ainvoke = AsyncMock(return_value={"output": "test response async"})
        return agent

    @pytest.fixture
    def optimization_config(self) -> OptimizationConfig:
        """Create a test optimization config."""
        return OptimizationConfig(
            tenant_id="tenant-123",
            agent_name="test_agent",
            enable_rl=True,
            enable_prompt_opt=False,
            enable_sft=False,
            metric_target="answer_quality",
        )

    def test_wrap_returns_wrapped_agent(
        self, mock_agent: MagicMock, optimization_config: OptimizationConfig
    ) -> None:
        """Test wrap() returns a wrapped agent instance."""
        from app.services.agent_wrapper_service import wrap

        wrapped = wrap(mock_agent, optimization_config)

        assert wrapped is not None
        assert wrapped is not mock_agent  # Should be a different object
        assert hasattr(wrapped, "invoke")  # Preserves agent API

    def test_wrapped_agent_invoke_calls_original(
        self, mock_agent: MagicMock, optimization_config: OptimizationConfig
    ) -> None:
        """Test wrapped agent's invoke() calls original agent's invoke()."""
        from app.services.agent_wrapper_service import wrap

        wrapped = wrap(mock_agent, optimization_config)
        query = {"input": "test query"}

        result = wrapped.invoke(query)

        mock_agent.invoke.assert_called_once()
        assert result == {"output": "test response"}

    @pytest.mark.asyncio
    async def test_wrapped_agent_ainvoke_calls_original(
        self, mock_agent: MagicMock, optimization_config: OptimizationConfig
    ) -> None:
        """Test wrapped agent's ainvoke() calls original agent's ainvoke()."""
        from app.services.agent_wrapper_service import wrap

        wrapped = wrap(mock_agent, optimization_config)
        query = {"input": "test query async"}

        result = await wrapped.ainvoke(query)

        mock_agent.ainvoke.assert_called_once()
        assert result == {"output": "test response async"}

    def test_wrapped_agent_preserves_output_schema(
        self, mock_agent: MagicMock, optimization_config: OptimizationConfig
    ) -> None:
        """Test wrapped agent preserves exact output schema from original."""
        from app.services.agent_wrapper_service import wrap

        # Original returns complex nested structure
        complex_output = {
            "answer": "test",
            "sources": [{"doc": "1", "score": 0.9}],
            "metadata": {"tokens": 100},
        }
        mock_agent.invoke.return_value = complex_output

        wrapped = wrap(mock_agent, optimization_config)
        result = wrapped.invoke({"input": "test"})

        assert result == complex_output  # Exact match

    def test_wrapped_agent_handles_agent_exceptions_gracefully(
        self, mock_agent: MagicMock, optimization_config: OptimizationConfig
    ) -> None:
        """Test wrapper doesn't suppress agent exceptions."""
        from app.services.agent_wrapper_service import wrap

        mock_agent.invoke.side_effect = ValueError("Agent failed")

        wrapped = wrap(mock_agent, optimization_config)

        with pytest.raises(ValueError, match="Agent failed"):
            wrapped.invoke({"input": "test"})

    def test_wrapped_agent_handles_wrapper_failures_gracefully(
        self, mock_agent: MagicMock, optimization_config: OptimizationConfig
    ) -> None:
        """Test wrapper failures don't break agent execution."""
        from app.services.agent_wrapper_service import wrap

        wrapped = wrap(mock_agent, optimization_config)

        # Simulate wrapper metric collection failure (should not affect result)
        with patch(
            "app.services.agent_wrapper_service.AgentWrapper._collect_metrics",
            side_effect=Exception("Metrics collection failed"),
        ):
            result = wrapped.invoke({"input": "test"})

            # Agent still returns correct result despite wrapper failure
            assert result == {"output": "test response"}

    def test_get_baseline_metrics_returns_valid_metrics(
        self, mock_agent: MagicMock, optimization_config: OptimizationConfig
    ) -> None:
        """Test get_baseline_metrics() returns valid BaselineMetrics."""
        from app.services.agent_wrapper_service import get_baseline_metrics

        mock_agent.invoke.return_value = {"output": "test"}

        metrics = get_baseline_metrics(mock_agent, {"input": "test"})

        assert isinstance(metrics, BaselineMetrics)
        assert metrics.latency_ms > 0
        assert metrics.token_usage >= 0  # May be 0 if not in response

    def test_get_baseline_metrics_measures_actual_latency(
        self, mock_agent: MagicMock, optimization_config: OptimizationConfig
    ) -> None:
        """Test get_baseline_metrics() measures actual agent latency."""
        # Simulate agent taking 100ms
        import time

        from app.services.agent_wrapper_service import get_baseline_metrics

        def slow_invoke(query: dict[str, Any]) -> dict[str, Any]:
            time.sleep(0.1)
            return {"output": "test"}

        mock_agent.invoke.side_effect = slow_invoke

        metrics = get_baseline_metrics(mock_agent, {"input": "test"})

        # Should measure ~100ms (allow ±50ms tolerance)
        assert 50 < metrics.latency_ms < 150

    def test_get_optimization_metrics_returns_valid_metrics(
        self, mock_agent: MagicMock, optimization_config: OptimizationConfig
    ) -> None:
        """Test get_optimization_metrics() returns OptimizationMetrics."""
        from app.services.agent_wrapper_service import get_optimization_metrics, wrap

        baseline = BaselineMetrics(latency_ms=1200.0, token_usage=500)
        wrapped = wrap(mock_agent, optimization_config)

        metrics = get_optimization_metrics(wrapped, {"input": "test"}, baseline)

        assert metrics is not None
        assert metrics.latency_ms > 0
        assert metrics.token_usage >= 0
        assert metrics.token_savings is not None  # Calculated from baseline

    def test_get_optimization_metrics_calculates_improvements(
        self, mock_agent: MagicMock, optimization_config: OptimizationConfig
    ) -> None:
        """Test get_optimization_metrics() calculates improvement metrics."""
        from app.services.agent_wrapper_service import get_optimization_metrics, wrap

        baseline = BaselineMetrics(latency_ms=1200.0, token_usage=500)

        # Mock wrapped agent to return with metadata showing fewer tokens
        mock_agent.invoke.return_value = {"output": "test", "metadata": {"tokens": 400}}
        wrapped = wrap(mock_agent, optimization_config)

        metrics = get_optimization_metrics(wrapped, {"input": "test"}, baseline)

        assert metrics.token_savings == 100  # 500 - 400
        assert metrics.improvement_percent is not None

    def test_wrapped_agent_captures_metrics_without_breaking_output(
        self, mock_agent: MagicMock, optimization_config: OptimizationConfig
    ) -> None:
        """Test wrapper captures metrics but doesn't modify agent output."""
        from app.services.agent_wrapper_service import wrap

        original_output = {"answer": "test", "confidence": 0.95}
        mock_agent.invoke.return_value = original_output

        wrapped = wrap(mock_agent, optimization_config)
        result = wrapped.invoke({"input": "test"})

        # Output is EXACTLY the same (no metrics injected)
        assert result == original_output
        assert "metrics" not in result
        assert "wrapper_metadata" not in result

    def test_wrap_with_disabled_optimization_returns_original(self, mock_agent: MagicMock) -> None:
        """Test wrap() returns original agent when optimization disabled."""
        from app.services.agent_wrapper_service import wrap

        config = OptimizationConfig(
            tenant_id="tenant-123",
            agent_name="test_agent",
            enable_rl=False,
            enable_prompt_opt=False,
            enable_sft=False,  # All disabled
        )

        wrapped = wrap(mock_agent, config)

        # When all optimizations disabled, should return original (or transparent wrapper)
        result = wrapped.invoke({"input": "test"})
        assert result == {"output": "test response"}

    def test_wrapper_preserves_agent_attributes(
        self, mock_agent: MagicMock, optimization_config: OptimizationConfig
    ) -> None:
        """Test wrapper preserves custom agent attributes."""
        from app.services.agent_wrapper_service import wrap

        # Add custom attributes to agent
        mock_agent.custom_config = {"temperature": 0.7}
        mock_agent.model_name = "gpt-4o-mini"

        wrapped = wrap(mock_agent, optimization_config)

        # Custom attributes should be preserved
        assert hasattr(wrapped, "custom_config")
        assert hasattr(wrapped, "model_name")
        assert wrapped.custom_config == {"temperature": 0.7}
        assert wrapped.model_name == "gpt-4o-mini"
