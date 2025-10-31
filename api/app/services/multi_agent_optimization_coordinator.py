"""Multi-agent optimization coordinator for selective agent optimization.

T034: Coordinator for managing optimization across multiple agents in a workflow.
"""

from app.core.selective_optimization_config import SelectiveOptimizationConfig
from app.models.optimization_models import BaselineMetrics


class MultiAgentOptimizationCoordinator:
    """Coordinator for multi-agent selective optimization.

    Manages optimization across multiple agents in a workflow:
    - Query Planner: RL optimization
    - Document Analyzer: Prompt optimization
    - Answer Generator: SFT optimization

    Ensures workflow coordination is preserved while optimizing individual agents.
    """

    def __init__(self, tenant_id: str) -> None:
        """Initialize multi-agent optimization coordinator.

        Args:
            tenant_id: Tenant identifier for isolation
        """
        self.tenant_id = tenant_id
        self.config = SelectiveOptimizationConfig(tenant_id=tenant_id)
        self.agent_names = ["query_planner", "document_analyzer", "answer_generator"]

    def collect_metrics_all_agents(
        self, metrics_by_agent: dict[str, list[BaselineMetrics]]
    ) -> dict[str, dict[str, float]]:
        """Collect and aggregate metrics from all agents independently.

        Args:
            metrics_by_agent: Dictionary mapping agent names to their metrics lists

        Returns:
            Dictionary with per-agent aggregated metrics
        """
        aggregated_metrics = {}

        for agent_name in self.agent_names:
            if agent_name not in metrics_by_agent:
                continue

            metrics = metrics_by_agent[agent_name]
            if not metrics:
                continue

            # Calculate averages for this agent
            avg_latency = sum(m.latency_ms for m in metrics) / len(metrics)
            avg_tokens = sum(m.token_usage for m in metrics) / len(metrics)
            avg_quality = sum(m.quality_signal for m in metrics) / len(metrics)

            aggregated_metrics[agent_name] = {
                "avg_latency_ms": avg_latency,
                "avg_token_usage": avg_tokens,
                "avg_quality_signal": avg_quality,
                "sample_count": len(metrics),
            }

        return aggregated_metrics

    def calculate_workflow_improvement(
        self,
        baseline_metrics: dict[str, list[BaselineMetrics]],
        optimized_metrics: dict[str, list[BaselineMetrics]],
    ) -> dict[str, float]:
        """Calculate workflow-level improvement from individual agent improvements.

        Args:
            baseline_metrics: Dictionary mapping agent names to baseline metrics
            optimized_metrics: Dictionary mapping agent names to optimized metrics

        Returns:
            Dictionary with workflow-level improvement percentages
        """
        # Collect metrics for all agents
        baseline_agg = self.collect_metrics_all_agents(baseline_metrics)
        optimized_agg = self.collect_metrics_all_agents(optimized_metrics)

        # Calculate workflow-level averages
        workflow_baseline = self._calculate_workflow_averages(baseline_agg)
        workflow_optimized = self._calculate_workflow_averages(optimized_agg)

        # Calculate improvement percentages
        latency_improvement = 0.0
        if workflow_baseline["avg_latency_ms"] > 0:
            latency_improvement = (
                (workflow_baseline["avg_latency_ms"] - workflow_optimized["avg_latency_ms"])
                / workflow_baseline["avg_latency_ms"]
            ) * 100

        token_improvement = 0.0
        if workflow_baseline["avg_token_usage"] > 0:
            token_improvement = (
                (workflow_baseline["avg_token_usage"] - workflow_optimized["avg_token_usage"])
                / workflow_baseline["avg_token_usage"]
            ) * 100

        quality_improvement = 0.0
        if workflow_baseline["avg_quality_signal"] > 0:
            quality_improvement = (
                (workflow_optimized["avg_quality_signal"] - workflow_baseline["avg_quality_signal"])
                / workflow_baseline["avg_quality_signal"]
            ) * 100

        return {
            "latency_improvement_percent": latency_improvement,
            "token_improvement_percent": token_improvement,
            "quality_improvement_percent": quality_improvement,
        }

    def _calculate_workflow_averages(
        self, agent_metrics: dict[str, dict[str, float]]
    ) -> dict[str, float]:
        """Calculate workflow-level averages from agent metrics.

        Args:
            agent_metrics: Dictionary of aggregated metrics per agent

        Returns:
            Dictionary with workflow-level averages
        """
        if not agent_metrics:
            return {
                "avg_latency_ms": 0.0,
                "avg_token_usage": 0.0,
                "avg_quality_signal": 0.0,
            }

        # Calculate workflow averages (simple average across agents)
        total_agents = len(agent_metrics)
        total_latency = sum(m["avg_latency_ms"] for m in agent_metrics.values())
        total_tokens = sum(m["avg_token_usage"] for m in agent_metrics.values())
        total_quality = sum(m["avg_quality_signal"] for m in agent_metrics.values())

        return {
            "avg_latency_ms": total_latency / total_agents,
            "avg_token_usage": total_tokens / total_agents,
            "avg_quality_signal": total_quality / total_agents,
        }

    def trigger_selective_optimization(self, agent_name: str) -> dict[str, str]:
        """Trigger optimization for a specific agent.

        Args:
            agent_name: Name of the agent to optimize

        Returns:
            Dictionary with optimization status and algorithm used
        """
        # Get agent configuration
        agent_config = self.config.get_agent_config(agent_name)

        # Determine which algorithm is enabled
        algorithm = "none"
        if agent_config.enable_rl:
            algorithm = "rl"
        elif agent_config.enable_prompt_opt:
            algorithm = "prompt_optimization"
        elif agent_config.enable_sft:
            algorithm = "sft"

        return {
            "status": "optimization_triggered",
            "agent_name": agent_name,
            "algorithm": algorithm,
            "tenant_id": self.tenant_id,
        }
