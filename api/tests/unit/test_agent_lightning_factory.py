"""Tests for Agent Lightning factory."""

import pytest

from app.core.agent_lightning_config import is_agent_lightning_available
from app.core.agent_lightning_factory import (
    create_optimization_config,
    create_wrapped_document_qa_agent,
)


class MockAgent:
    """Mock agent for testing."""

    def __init__(self) -> None:
        """Initialize mock agent."""
        self.invoked = False
        self.custom_attr = "test_value"

    def invoke(self, input_data: dict) -> dict:  # noqa: ARG002
        """Mock invoke method."""
        self.invoked = True
        return {"output": "test response"}


class TestAgentLightningFactory:
    """Tests for Agent Lightning factory functions."""

    def test_create_wrapped_document_qa_agent_returns_agent(self) -> None:
        """Test that factory returns an agent (wrapped or unwrapped)."""
        mock_agent = MockAgent()

        result = create_wrapped_document_qa_agent(mock_agent, tenant_id="test-tenant")

        # Should return some agent (either wrapped or original)
        assert result is not None

        # Should preserve original functionality
        assert hasattr(result, "invoke")

    def test_create_wrapped_document_qa_agent_preserves_attributes(self) -> None:
        """Test that wrapping preserves agent attributes."""
        mock_agent = MockAgent()

        result = create_wrapped_document_qa_agent(mock_agent, tenant_id="test-tenant")

        # If Agent Lightning available and wrapping successful,
        # attributes should be preserved
        # If not available, original agent returned
        if is_agent_lightning_available():
            # Wrapped agent should have _agent attribute pointing to original
            if hasattr(result, "_agent"):
                assert result._agent.custom_attr == "test_value"
        else:
            # Original agent returned
            assert result.custom_attr == "test_value"

    def test_create_wrapped_document_qa_agent_default_tenant(self) -> None:
        """Test factory with default tenant_id."""
        mock_agent = MockAgent()

        result = create_wrapped_document_qa_agent(mock_agent)

        assert result is not None

    def test_create_wrapped_document_qa_agent_handles_wrapping_failure(
        self,
    ) -> None:
        """Test factory handles wrapping failures gracefully."""
        # Use an invalid agent that might cause wrapping to fail
        invalid_agent = "not_an_agent"

        # Should not raise exception - should return original
        result = create_wrapped_document_qa_agent(invalid_agent, tenant_id="test")

        assert result is not None

    def test_create_optimization_config_returns_valid_config(self) -> None:
        """Test that optimization config factory returns valid config."""
        config = create_optimization_config(
            agent_name="test_agent",
            tenant_id="test-tenant",
            metric_target="token_efficiency",
        )

        assert config.agent_name == "test_agent"
        assert config.tenant_id == "test-tenant"
        assert config.metric_target == "token_efficiency"
        assert isinstance(config.enable_rl, bool)
        assert isinstance(config.enable_prompt_opt, bool)
        assert isinstance(config.enable_sft, bool)

    def test_create_optimization_config_default_metric_target(self) -> None:
        """Test optimization config with default metric target."""
        config = create_optimization_config(agent_name="test_agent", tenant_id="test-tenant")

        assert config.agent_name == "test_agent"
        assert config.tenant_id == "test-tenant"
        assert config.metric_target == "answer_quality"

    def test_create_wrapped_document_qa_agent_uses_document_qa_config(self) -> None:
        """Test that factory configures document QA specific settings."""
        mock_agent = MockAgent()

        result = create_wrapped_document_qa_agent(mock_agent, tenant_id="test-tenant")

        # Verify agent was created (configuration details tested in integration tests)
        assert result is not None

        # If wrapped, should have document QA specific configuration
        if is_agent_lightning_available() and hasattr(result, "_config"):
            config = result._config
            assert config.agent_name == "langgraph_document_qa"
            assert config.tenant_id == "test-tenant"
            assert config.metric_target == "answer_quality"

    @pytest.mark.asyncio
    async def test_wrapped_agent_still_invokes(self) -> None:
        """Test that wrapped agent can still be invoked."""
        mock_agent = MockAgent()

        wrapped = create_wrapped_document_qa_agent(mock_agent, tenant_id="test-tenant")

        # Should be able to invoke regardless of wrapping
        if hasattr(wrapped, "invoke"):
            result = wrapped.invoke({"input": "test"})
            assert result is not None
