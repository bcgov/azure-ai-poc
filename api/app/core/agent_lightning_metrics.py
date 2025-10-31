"""Agent Lightning Prometheus metrics definitions.

Provides Prometheus metrics for monitoring Agent Lightning optimization workflows
including improvement percentages, token savings, cost ROI, and optimization latency.

All metrics are labeled with tenant_id, agent_name, and optimization_algorithm
for multi-dimensional analysis and alerting.
"""

from prometheus_client import Counter, Gauge, Histogram

# Gauge: Optimization improvement percentage by agent
agent_lightning_optimization_improvement_percent = Gauge(
    "agent_lightning_optimization_improvement_percent",
    "Optimization improvement percentage achieved by agent",
    labelnames=["tenant_id", "agent_name", "optimization_algorithm"],
)

# Counter: Total tokens saved across all optimizations
agent_lightning_tokens_saved_total = Counter(
    "agent_lightning_tokens_saved_total",
    "Cumulative tokens saved through optimization",
    labelnames=["tenant_id", "agent_name", "optimization_algorithm"],
)

# Gauge: Cost ROI in dollars
agent_lightning_cost_roi_dollars = Gauge(
    "agent_lightning_cost_roi_dollars",
    "Estimated cost savings (ROI) in dollars from optimization",
    labelnames=["tenant_id", "agent_name", "optimization_algorithm"],
)

# Histogram: Optimization operation latency in milliseconds
agent_lightning_optimization_latency_ms = Histogram(
    "agent_lightning_optimization_latency_ms",
    "Time taken to complete optimization operation in milliseconds",
    labelnames=["tenant_id", "agent_name", "optimization_algorithm"],
    buckets=(
        50,
        100,
        250,
        500,
        1000,
        2500,
        5000,
        10000,
        30000,
        60000,
    ),  # Buckets in ms
)


__all__ = [
    "agent_lightning_optimization_improvement_percent",
    "agent_lightning_tokens_saved_total",
    "agent_lightning_cost_roi_dollars",
    "agent_lightning_optimization_latency_ms",
]
