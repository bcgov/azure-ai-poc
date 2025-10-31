"""Integration tests for Agent Lightning Prometheus metrics instrumentation.

Tests that Agent Lightning optimization workflows properly record Prometheus metrics
for monitoring, alerting, and observability dashboards.

Written FIRST per TDD approach - these tests should FAIL until implementation is complete.
"""

import pytest
from prometheus_client import REGISTRY


class TestAgentLightningPrometheusMetrics:
    """Test cases for Agent Lightning Prometheus metrics recording."""

    @pytest.fixture(autouse=True)
    def clear_metrics(self):
        """Clear Prometheus metrics before each test."""
        # Note: In production, metrics accumulate. In tests, we need to be careful
        # about metric state. This fixture documents the test isolation approach.
        yield
        # Cleanup if needed - Prometheus client doesn't easily support clearing
        # individual metrics, so tests should verify increments/changes rather than
        # absolute values where possible

    def test_optimization_improvement_percent_gauge_exists(self) -> None:
        """Test that improvement percent gauge metric exists and can be set."""
        from app.core.agent_lightning_metrics import (
            agent_lightning_optimization_improvement_percent,
        )

        # Verify metric exists
        assert agent_lightning_optimization_improvement_percent is not None

        # Set metric value with labels
        agent_lightning_optimization_improvement_percent.labels(
            tenant_id="tenant-123",
            agent_name="query_planner",
            optimization_algorithm="rl",
        ).set(15.5)

        # Verify metric was recorded in registry
        metric_families = REGISTRY.collect()
        metric_found = False
        for family in metric_families:
            if family.name == "agent_lightning_optimization_improvement_percent":
                metric_found = True
                # Verify it's a gauge type
                assert family.type == "gauge"
                # Verify labels exist in samples
                for sample in family.samples:
                    if (
                        sample.labels.get("tenant_id") == "tenant-123"
                        and sample.labels.get("agent_name") == "query_planner"
                        and sample.labels.get("optimization_algorithm") == "rl"
                    ):
                        assert sample.value == 15.5
                        break

        assert metric_found, "Improvement percent gauge metric not found in registry"

    def test_tokens_saved_counter_exists(self) -> None:
        """Test that tokens saved counter metric exists and can be incremented."""
        from app.core.agent_lightning_metrics import (
            agent_lightning_tokens_saved_total,
        )

        # Verify metric exists
        assert agent_lightning_tokens_saved_total is not None

        # Get initial value
        initial_value = None
        metric_families = list(REGISTRY.collect())
        for family in metric_families:
            # Counter metrics strip _total suffix from family name
            if family.name == "agent_lightning_tokens_saved":
                for sample in family.samples:
                    if (
                        sample.labels.get("tenant_id") == "tenant-456"
                        and sample.labels.get("agent_name") == "document_analyzer"
                        and sample.labels.get("optimization_algorithm") == "prompt"
                    ):
                        initial_value = sample.value
                        break

        # Increment counter
        agent_lightning_tokens_saved_total.labels(
            tenant_id="tenant-456",
            agent_name="document_analyzer",
            optimization_algorithm="prompt",
        ).inc(150)

        # Verify counter was incremented
        metric_families = list(REGISTRY.collect())
        metric_found = False
        value_found = False
        for family in metric_families:
            # Counter metrics strip _total suffix from family name
            if family.name == "agent_lightning_tokens_saved":
                metric_found = True
                # Verify it's a counter type
                assert family.type == "counter"
                # Verify value increased (sample name will have _total suffix)
                for sample in family.samples:
                    if (
                        sample.name == "agent_lightning_tokens_saved_total"
                        and sample.labels.get("tenant_id") == "tenant-456"
                        and sample.labels.get("agent_name") == "document_analyzer"
                        and sample.labels.get("optimization_algorithm") == "prompt"
                    ):
                        value_found = True
                        if initial_value is not None:
                            assert sample.value >= initial_value + 150
                        else:
                            assert sample.value >= 150
                        break

        assert metric_found, "Tokens saved counter metric not found in registry"
        assert value_found, "Counter value with correct labels not found"

    def test_cost_roi_dollars_gauge_exists(self) -> None:
        """Test that cost ROI dollars gauge metric exists and can be set."""
        from app.core.agent_lightning_metrics import agent_lightning_cost_roi_dollars

        # Verify metric exists
        assert agent_lightning_cost_roi_dollars is not None

        # Set metric value with labels
        agent_lightning_cost_roi_dollars.labels(
            tenant_id="tenant-789",
            agent_name="answer_generator",
            optimization_algorithm="sft",
        ).set(42.75)

        # Verify metric was recorded
        metric_families = list(REGISTRY.collect())
        metric_found = False
        for family in metric_families:
            if family.name == "agent_lightning_cost_roi_dollars":
                metric_found = True
                # Verify it's a gauge type
                assert family.type == "gauge"
                # Verify value
                for sample in family.samples:
                    if (
                        sample.labels.get("tenant_id") == "tenant-789"
                        and sample.labels.get("agent_name") == "answer_generator"
                        and sample.labels.get("optimization_algorithm") == "sft"
                    ):
                        assert sample.value == 42.75
                        break

        assert metric_found, "Cost ROI dollars gauge metric not found in registry"

    def test_optimization_latency_histogram_exists(self) -> None:
        """Test that optimization latency histogram metric exists and can record observations."""
        from app.core.agent_lightning_metrics import (
            agent_lightning_optimization_latency_ms,
        )

        # Verify metric exists
        assert agent_lightning_optimization_latency_ms is not None

        # Record observation
        agent_lightning_optimization_latency_ms.labels(
            tenant_id="tenant-histogram",
            agent_name="query_planner",
            optimization_algorithm="rl",
        ).observe(1250.5)

        # Verify metric was recorded
        metric_families = list(REGISTRY.collect())
        metric_found = False
        for family in metric_families:
            if family.name == "agent_lightning_optimization_latency_ms":
                metric_found = True
                # Verify it's a histogram type
                assert family.type == "histogram"
                # Verify observation was recorded (check count)
                for sample in family.samples:
                    if (
                        sample.name.endswith("_count")
                        and sample.labels.get("tenant_id") == "tenant-histogram"
                        and sample.labels.get("agent_name") == "query_planner"
                        and sample.labels.get("optimization_algorithm") == "rl"
                    ):
                        assert sample.value >= 1  # At least one observation
                        break

        assert metric_found, "Optimization latency histogram metric not found in registry"

    def test_all_metrics_tagged_with_tenant_id(self) -> None:
        """Test all Agent Lightning metrics include tenant_id label."""
        from app.core.agent_lightning_metrics import (
            agent_lightning_cost_roi_dollars,
            agent_lightning_optimization_improvement_percent,
            agent_lightning_optimization_latency_ms,
            agent_lightning_tokens_saved_total,
        )

        tenant_id = "tenant-label-test"

        # Set/increment each metric with tenant_id
        agent_lightning_optimization_improvement_percent.labels(
            tenant_id=tenant_id,
            agent_name="test_agent",
            optimization_algorithm="test",
        ).set(10.0)

        agent_lightning_tokens_saved_total.labels(
            tenant_id=tenant_id,
            agent_name="test_agent",
            optimization_algorithm="test",
        ).inc(100)

        agent_lightning_cost_roi_dollars.labels(
            tenant_id=tenant_id,
            agent_name="test_agent",
            optimization_algorithm="test",
        ).set(5.0)

        agent_lightning_optimization_latency_ms.labels(
            tenant_id=tenant_id,
            agent_name="test_agent",
            optimization_algorithm="test",
        ).observe(500.0)

        # Verify all metrics have tenant_id in their labels
        metric_families = list(REGISTRY.collect())
        agent_lightning_metrics = [
            "agent_lightning_optimization_improvement_percent",
            "agent_lightning_tokens_saved",  # Counter strips _total suffix
            "agent_lightning_cost_roi_dollars",
            "agent_lightning_optimization_latency_ms",
        ]

        for metric_name in agent_lightning_metrics:
            found_with_tenant_id = False
            for family in metric_families:
                if family.name == metric_name:
                    for sample in family.samples:
                        if sample.labels.get("tenant_id") == tenant_id:
                            found_with_tenant_id = True
                            break
                    break

            assert found_with_tenant_id, f"Metric {metric_name} does not have tenant_id label"

    def test_all_metrics_tagged_with_agent_name(self) -> None:
        """Test all Agent Lightning metrics include agent_name label."""
        from app.core.agent_lightning_metrics import (
            agent_lightning_cost_roi_dollars,
            agent_lightning_optimization_improvement_percent,
            agent_lightning_optimization_latency_ms,
            agent_lightning_tokens_saved_total,
        )

        agent_name = "test_agent_name"

        # Set/increment each metric with agent_name
        agent_lightning_optimization_improvement_percent.labels(
            tenant_id="tenant-test",
            agent_name=agent_name,
            optimization_algorithm="test",
        ).set(10.0)

        agent_lightning_tokens_saved_total.labels(
            tenant_id="tenant-test",
            agent_name=agent_name,
            optimization_algorithm="test",
        ).inc(100)

        agent_lightning_cost_roi_dollars.labels(
            tenant_id="tenant-test",
            agent_name=agent_name,
            optimization_algorithm="test",
        ).set(5.0)

        agent_lightning_optimization_latency_ms.labels(
            tenant_id="tenant-test",
            agent_name=agent_name,
            optimization_algorithm="test",
        ).observe(500.0)

        # Verify all metrics have agent_name in their labels
        metric_families = list(REGISTRY.collect())
        agent_lightning_metrics = [
            "agent_lightning_optimization_improvement_percent",
            "agent_lightning_tokens_saved",  # Counter strips _total suffix
            "agent_lightning_cost_roi_dollars",
            "agent_lightning_optimization_latency_ms",
        ]

        for metric_name in agent_lightning_metrics:
            found_with_agent_name = False
            for family in metric_families:
                if family.name == metric_name:
                    for sample in family.samples:
                        if sample.labels.get("agent_name") == agent_name:
                            found_with_agent_name = True
                            break
                    break

            assert found_with_agent_name, f"Metric {metric_name} does not have agent_name label"

    def test_all_metrics_tagged_with_optimization_algorithm(self) -> None:
        """Test all Agent Lightning metrics include optimization_algorithm label."""
        from app.core.agent_lightning_metrics import (
            agent_lightning_cost_roi_dollars,
            agent_lightning_optimization_improvement_percent,
            agent_lightning_optimization_latency_ms,
            agent_lightning_tokens_saved_total,
        )

        algorithm = "test_algorithm"

        # Set/increment each metric with optimization_algorithm
        agent_lightning_optimization_improvement_percent.labels(
            tenant_id="tenant-test",
            agent_name="test_agent",
            optimization_algorithm=algorithm,
        ).set(10.0)

        agent_lightning_tokens_saved_total.labels(
            tenant_id="tenant-test",
            agent_name="test_agent",
            optimization_algorithm=algorithm,
        ).inc(100)

        agent_lightning_cost_roi_dollars.labels(
            tenant_id="tenant-test",
            agent_name="test_agent",
            optimization_algorithm=algorithm,
        ).set(5.0)

        agent_lightning_optimization_latency_ms.labels(
            tenant_id="tenant-test",
            agent_name="test_agent",
            optimization_algorithm=algorithm,
        ).observe(500.0)

        # Verify all metrics have optimization_algorithm in their labels
        metric_families = list(REGISTRY.collect())
        agent_lightning_metrics = [
            "agent_lightning_optimization_improvement_percent",
            "agent_lightning_tokens_saved",  # Counter strips _total suffix
            "agent_lightning_cost_roi_dollars",
            "agent_lightning_optimization_latency_ms",
        ]

        for metric_name in agent_lightning_metrics:
            found_with_algorithm = False
            for family in metric_families:
                if family.name == metric_name:
                    for sample in family.samples:
                        if sample.labels.get("optimization_algorithm") == algorithm:
                            found_with_algorithm = True
                            break
                    break

            assert found_with_algorithm, (
                f"Metric {metric_name} does not have optimization_algorithm label"
            )
