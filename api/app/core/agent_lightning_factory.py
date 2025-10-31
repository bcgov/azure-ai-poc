"""Factory for creating Agent Lightning wrapped agents.

This module provides factory functions for creating agents wrapped with
Agent Lightning optimization capabilities.
"""

from typing import Any

from app.core.agent_lightning_config import (
    OptimizationConfig,
    get_agent_lightning_settings,
    is_agent_lightning_available,
)
from app.core.logger import get_logger

logger = get_logger(__name__)


def create_wrapped_document_qa_agent(agent: Any, tenant_id: str = "default") -> Any:
    """Create a document QA agent wrapped with Agent Lightning.

    This factory encapsulates the logic for wrapping a LangGraph document QA
    agent with Agent Lightning optimization. It configures optimization targets
    specifically for document QA workflows:
    - Answer quality optimization
    - Token efficiency optimization
    - Response latency optimization

    Args:
        agent: The base LangGraph agent to wrap
        tenant_id: Tenant identifier for multi-tenant isolation

    Returns:
        The wrapped agent if Agent Lightning is available, otherwise the original agent

    Example:
        >>> from langgraph.graph import StateGraph
        >>> base_agent = StateGraph(...).compile()
        >>> optimized_agent = create_wrapped_document_qa_agent(base_agent, "tenant-123")
    """
    try:
        # Check if Agent Lightning is available
        if not is_agent_lightning_available():
            logger.warning("Agent Lightning not available - returning unwrapped agent")
            return agent

        # Import Agent Lightning components
        from app.services.agent_wrapper_service import wrap

        # Get Agent Lightning settings
        settings = get_agent_lightning_settings()

        # Create optimization configuration for document QA
        config = OptimizationConfig(
            agent_name="langgraph_document_qa",
            tenant_id=tenant_id,
            enable_rl=settings.enable_rl,
            enable_prompt_opt=settings.enable_prompt_opt,
            enable_sft=settings.enable_sft,
            # Primary optimization target for document QA
            metric_target="answer_quality",
        )

        # Wrap the agent with Agent Lightning
        wrapped_agent = wrap(agent, config)

        logger.info(
            f"Document QA agent wrapped with Agent Lightning for tenant: {tenant_id}",
            extra={
                "tenant_id": tenant_id,
                "agent_name": "langgraph_document_qa",
                "optimization_enabled": config.optimization_enabled,
                "rl_enabled": config.enable_rl,
                "prompt_opt_enabled": config.enable_prompt_opt,
                "sft_enabled": config.enable_sft,
            },
        )

        return wrapped_agent

    except ImportError:
        logger.warning("Agent Lightning SDK not installed - returning unwrapped agent")
        return agent
    except Exception as e:
        logger.error(
            f"Error wrapping document QA agent with Agent Lightning: {e}",
            exc_info=True,
        )
        return agent


def create_optimization_config(
    agent_name: str,
    tenant_id: str,
    metric_target: str = "answer_quality",
) -> OptimizationConfig:
    """Create an optimization configuration for an agent.

    This is a convenience function for creating OptimizationConfig objects
    with appropriate defaults from settings.

    Args:
        agent_name: Name of the agent being optimized
        tenant_id: Tenant identifier
        metric_target: Primary optimization target metric

    Returns:
        OptimizationConfig configured with current settings
    """
    settings = get_agent_lightning_settings()

    return OptimizationConfig(
        agent_name=agent_name,
        tenant_id=tenant_id,
        enable_rl=settings.enable_rl,
        enable_prompt_opt=settings.enable_prompt_opt,
        enable_sft=settings.enable_sft,
        metric_target=metric_target,
    )
