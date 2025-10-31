"""Agent Lightning configuration and initialization.

This module provides configuration management and factory functions for
integrating Agent Lightning optimization layer with existing LangGraph agents.
"""

from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.models.optimization_models import OptimizationConfig


class AgentLightningSettings(BaseSettings):
    """Agent Lightning configuration settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="AGENT_LIGHTNING_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Feature flags
    enabled: bool = Field(default=False, description="Enable Agent Lightning optimization")
    # Default optimization settings
    enable_rl: bool = Field(default=True, description="Enable Reinforcement Learning optimization")
    enable_prompt_opt: bool = Field(
        default=True, description="Enable Automatic Prompt Optimization"
    )
    enable_sft: bool = Field(
        default=False, description="Enable Supervised Fine-Tuning (requires training data)"
    )

    # Performance settings
    optimization_interval: int = Field(
        default=50,
        description="Number of agent runs before triggering optimization",
        ge=10,
    )
    wrapper_timeout_ms: int = Field(
        default=100,
        description="Maximum wrapper overhead timeout in milliseconds",
        ge=10,
        le=1000,
    )


# Global settings instance
_settings: AgentLightningSettings | None = None


def get_agent_lightning_settings() -> AgentLightningSettings:
    """Get or create Agent Lightning settings singleton.

    Returns:
        AgentLightningSettings: Configuration settings for Agent Lightning

    Example:
        >>> settings = get_agent_lightning_settings()
        >>> if settings.enabled:
        ...     print(f"Agent Lightning enabled with RL={settings.enable_rl}")
    """
    global _settings
    if _settings is None:
        _settings = AgentLightningSettings()
    return _settings


def create_optimization_config(
    tenant_id: str,
    agent_name: str = "default",
    metric_target: str = "answer_quality",
    enable_rl: bool | None = None,
    enable_prompt_opt: bool | None = None,
    enable_sft: bool | None = None,
) -> OptimizationConfig:
    """Create an OptimizationConfig for a specific agent and tenant.

    This factory function creates optimization configurations with settings
    from environment variables as defaults, allowing per-agent overrides.

    Args:
        tenant_id: Unique identifier for the tenant (for multi-tenant isolation)
        agent_name: Name of the agent being optimized (e.g., "document_qa")
        metric_target: Target metric for optimization (e.g., "answer_quality", "token_efficiency")
        enable_rl: Override for RL optimization (None = use default from settings)
        enable_prompt_opt: Override for Prompt Optimization (None = use default)
        enable_sft: Override for SFT (None = use default)

    Returns:
        OptimizationConfig: Configuration instance ready for wrapping agents

    Example:
        >>> config = create_optimization_config(
        ...     tenant_id="tenant-123",
        ...     agent_name="document_qa",
        ...     metric_target="answer_quality",
        ...     enable_rl=True
        ... )
        >>> print(config.enable_rl)
        True
    """
    settings = get_agent_lightning_settings()

    return OptimizationConfig(
        tenant_id=tenant_id,
        agent_name=agent_name,
        enable_rl=enable_rl if enable_rl is not None else settings.enable_rl,
        enable_prompt_opt=(
            enable_prompt_opt if enable_prompt_opt is not None else settings.enable_prompt_opt
        ),
        enable_sft=enable_sft if enable_sft is not None else settings.enable_sft,
        metric_target=metric_target,
    )


def wrap_agent_with_lightning(
    agent: Any,
    config: OptimizationConfig,
) -> Any:
    """Wrap an existing agent with Agent Lightning optimization layer.

    This is the primary integration point for adding Agent Lightning to
    existing LangGraph/LangChain agents. The wrapper is transparent and
    preserves the agent's original API.

    Args:
        agent: The LangGraph/LangChain agent to wrap
        config: Optimization configuration for this agent

    Returns:
        Any: Wrapped agent with Agent Lightning optimization (same API as original)

    Raises:
        RuntimeError: If Agent Lightning is not enabled in settings
        ImportError: If agentlightning package is not installed

    Example:
        >>> from langgraph.graph import StateGraph
        >>> original_agent = StateGraph(...)
        >>> config = create_optimization_config(tenant_id="tenant-123")
        >>> wrapped_agent = wrap_agent_with_lightning(original_agent, config)
        >>> # wrapped_agent has same API as original_agent
        >>> result = await wrapped_agent.invoke(query)
    """
    settings = get_agent_lightning_settings()

    if not settings.enabled:
        # If Agent Lightning is disabled, return original agent unwrapped
        return agent

    try:
        # Import Agent Lightning SDK (conditional import for graceful degradation)
        import agentlightning
    except ImportError as e:
        raise ImportError(
            "agentlightning package not installed. Install with: pip install agentlightning>=0.1.0"
        ) from e

    # Wrap the agent with Agent Lightning optimization
    # This preserves the original agent's API while adding optimization capabilities
    wrapped_agent = agentlightning.wrap(
        agent,
        tenant_id=config.tenant_id,
        agent_name=config.agent_name,
        optimization_config={
            "enable_rl": config.enable_rl,
            "enable_prompt_opt": config.enable_prompt_opt,
            "enable_sft": config.enable_sft,
            "metric_target": config.metric_target,
        },
    )

    return wrapped_agent


def is_agent_lightning_available() -> bool:
    """Check if Agent Lightning wrapper is available and enabled.

    Returns:
        bool: True if Agent Lightning is enabled in settings and wrapper exists

    Example:
        >>> if is_agent_lightning_available():
        ...     print("Agent Lightning ready to use")
        ... else:
        ...     print("Agent Lightning not available")
    """
    try:
        # Check if our custom wrapper implementation exists
        from app.services.agent_wrapper_service import wrap  # noqa: F401

        settings = get_agent_lightning_settings()
        return settings.enabled
    except ImportError:
        return False
