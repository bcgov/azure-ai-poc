"""Agent Lightning OpenTelemetry instrumentation.

Provides OpenTelemetry span creation for Agent Lightning optimization workflows
to enable debugging, tracing, and observability across multi-agent systems.
"""

from collections.abc import Generator
from contextlib import contextmanager

from opentelemetry import trace

from app.core.telemetry import get_tracer


class AgentLightningTracer:
    """OpenTelemetry tracer for Agent Lightning optimization workflows.

    Provides context managers for creating spans with proper attributes
    for optimization decisions, metrics collection, and ROI calculations.
    All spans are tagged with tenant_id for multi-tenant correlation.
    """

    def __init__(self, tenant_id: str) -> None:
        """Initialize tracer with tenant context.

        Args:
            tenant_id: Tenant identifier for multi-tenant correlation
        """
        self.tenant_id = tenant_id
        self.tracer = get_tracer("agent_lightning")

    @contextmanager
    def create_optimization_decision_span(
        self,
        agent_name: str,
        algorithm: str,
        reason: str,
    ) -> Generator[trace.Span, None, None]:
        """Create span for optimization algorithm decision.

        Args:
            agent_name: Name of the agent being optimized (e.g., "query_planner")
            algorithm: Algorithm selected (e.g., "rl", "prompt", "sft")
            reason: Reason for selection (e.g., "baseline_latency_high")

        Yields:
            OpenTelemetry span for the optimization decision
        """
        with self.tracer.start_as_current_span("agent_lightning.optimization_decision") as span:
            span.set_attribute("tenant_id", self.tenant_id)
            span.set_attribute("agent_name", agent_name)
            span.set_attribute("algorithm", algorithm)
            span.set_attribute("reason", reason)
            yield span

    @contextmanager
    def create_metrics_collection_span(
        self,
        agent_name: str,
        metric_count: int,
        baseline_latency_ms: float,
        baseline_tokens: int,
    ) -> Generator[trace.Span, None, None]:
        """Create span for metrics collection.

        Args:
            agent_name: Name of the agent collecting metrics
            metric_count: Number of metrics being collected
            baseline_latency_ms: Baseline latency in milliseconds
            baseline_tokens: Baseline token count

        Yields:
            OpenTelemetry span for metrics collection
        """
        with self.tracer.start_as_current_span("agent_lightning.metrics_collection") as span:
            span.set_attribute("tenant_id", self.tenant_id)
            span.set_attribute("agent_name", agent_name)
            span.set_attribute("metric_count", metric_count)
            span.set_attribute("baseline_latency_ms", baseline_latency_ms)
            span.set_attribute("baseline_tokens", baseline_tokens)
            yield span

    @contextmanager
    def create_roi_calculation_span(
        self,
        agent_name: str,
        improvement_percent: float,
        token_savings: int,
        cost_reduction_usd: float,
        roi_dollars: float,
    ) -> Generator[trace.Span, None, None]:
        """Create span for ROI calculation.

        Args:
            agent_name: Name of the agent being analyzed
            improvement_percent: Improvement percentage achieved
            token_savings: Number of tokens saved
            cost_reduction_usd: Cost reduction in USD
            roi_dollars: Total ROI in dollars

        Yields:
            OpenTelemetry span for ROI calculation
        """
        with self.tracer.start_as_current_span("agent_lightning.roi_calculation") as span:
            span.set_attribute("tenant_id", self.tenant_id)
            span.set_attribute("agent_name", agent_name)
            span.set_attribute("improvement_percent", improvement_percent)
            span.set_attribute("token_savings", token_savings)
            span.set_attribute("cost_reduction_usd", cost_reduction_usd)
            span.set_attribute("roi_dollars", roi_dollars)
            yield span


__all__ = ["AgentLightningTracer"]
