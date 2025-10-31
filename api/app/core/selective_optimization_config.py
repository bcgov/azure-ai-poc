"""Selective optimization configuration for multi-agent workflows.

T032: Configuration for applying different optimization algorithms to different agents.
"""

from app.models.optimization_models import OptimizationConfig


class SelectiveOptimizationConfig:
    """Configuration for selective agent optimization.

    Allows each agent in a multi-agent workflow to use a different
    optimization algorithm:
    - Query Planner: RL optimization for decision making
    - Document Analyzer: Prompt optimization for retrieval
    - Answer Generator: SFT optimization for quality improvement

    This maintains tenant isolation while enabling per-agent optimization.
    """

    def __init__(self, tenant_id: str) -> None:
        """Initialize selective optimization config.

        Args:
            tenant_id: Tenant identifier for isolation
        """
        self.tenant_id = tenant_id

        # Pre-configure optimization strategies for each agent
        self._agent_configs = {
            "query_planner": OptimizationConfig(
                agent_name="query_planner",
                tenant_id=tenant_id,
                enable_rl=True,
                enable_prompt_opt=False,
                enable_sft=False,
                metric_target="latency",  # RL optimizes decision speed
            ),
            "document_analyzer": OptimizationConfig(
                agent_name="document_analyzer",
                tenant_id=tenant_id,
                enable_rl=False,
                enable_prompt_opt=True,
                enable_sft=False,
                metric_target="answer_quality",  # Prompt opt improves retrieval
            ),
            "answer_generator": OptimizationConfig(
                agent_name="answer_generator",
                tenant_id=tenant_id,
                enable_rl=False,
                enable_prompt_opt=False,
                enable_sft=True,
                metric_target="answer_quality",  # SFT improves generation quality
            ),
        }

    def get_agent_config(self, agent_name: str) -> OptimizationConfig:
        """Get optimization configuration for a specific agent.

        Args:
            agent_name: Name of the agent (query_planner, document_analyzer, answer_generator)

        Returns:
            OptimizationConfig for the specified agent, or default config if unknown
        """
        # Return pre-configured optimization for known agents
        if agent_name in self._agent_configs:
            return self._agent_configs[agent_name]

        # For unknown agents, return a default config with all optimizations disabled
        return OptimizationConfig(
            agent_name=agent_name,
            tenant_id=self.tenant_id,
            enable_rl=False,
            enable_prompt_opt=False,
            enable_sft=False,
            metric_target="answer_quality",
        )
