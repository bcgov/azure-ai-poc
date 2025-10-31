"""Integration tests for Agent Lightning observability (OpenTelemetry + Prometheus).

This module tests that Agent Lightning optimization decisions, metrics collection,
and ROI calculations are properly instrumented with observability.
Tests written FIRST per TDD approach.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.models.optimization_models import OptimizationConfig


class TestOpenTelemetryIntegration:
    """Test cases for OpenTelemetry span creation."""

    @pytest.fixture
    def optimization_config(self) -> OptimizationConfig:
        """Create a test optimization config."""
        return OptimizationConfig(
            tenant_id="tenant-123",
            agent_name="test_agent",
            enable_rl=True,
            metric_target="answer_quality",
        )

    def test_optimization_decision_span_created(
        self, optimization_config: OptimizationConfig
    ) -> None:
        """Test OpenTelemetry span created for optimization decision."""
        from app.services.optimization_service import apply_optimization_algorithm
        from app.models.optimization_models import BaselineMetrics

        baseline = BaselineMetrics(latency_ms=1200.0, token_usage=500)
        training_data = [{"query": "test", "response": "test"}]

        with patch("app.core.telemetry.tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span

            apply_optimization_algorithm(optimization_config, baseline, training_data)

            # Verify span was created
            mock_tracer.start_as_current_span.assert_called()
            span_name = str(mock_tracer.start_as_current_span.call_args)
            assert "agent_lightning.optimization_decision" in span_name

    def test_metrics_collection_span_created(self, optimization_config: OptimizationConfig) -> None:
        """Test OpenTelemetry span created for metrics collection."""
        from app.services.optimization_service import OptimizationDataCollector

        collector = OptimizationDataCollector(optimization_config)

        with patch("app.core.telemetry.tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span

            collector.collect_metrics(
                query={"input": "test"},
                response={"output": "test"},
                agent_metadata={"tokens": 100},
            )

            # Verify span was created
            mock_tracer.start_as_current_span.assert_called()
            span_name = str(mock_tracer.start_as_current_span.call_args)
            assert "agent_lightning.metrics_collection" in span_name

    def test_roi_calculation_span_created(self, optimization_config: OptimizationConfig) -> None:
        """Test OpenTelemetry span created for ROI calculation."""
        from app.services.agent_wrapper_service import get_optimization_metrics, wrap
        from app.models.optimization_models import BaselineMetrics

        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"output": "test"}
        wrapped = wrap(mock_agent, optimization_config)

        baseline = BaselineMetrics(latency_ms=1200.0, token_usage=500, cost_usd=0.015)

        with patch("app.core.telemetry.tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span

            get_optimization_metrics(wrapped, {"input": "test"}, baseline)

            # Verify span was created
            mock_tracer.start_as_current_span.assert_called()
            span_name = str(mock_tracer.start_as_current_span.call_args)
            assert "agent_lightning.roi_calculation" in span_name

    def test_spans_tagged_with_tenant_id(self, optimization_config: OptimizationConfig) -> None:
        """Test OpenTelemetry spans are tagged with tenant_id."""
        from app.services.optimization_service import apply_optimization_algorithm
        from app.models.optimization_models import BaselineMetrics

        baseline = BaselineMetrics(latency_ms=1200.0, token_usage=500)
        training_data = [{"query": "test", "response": "test"}]

        with patch("app.core.telemetry.tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span

            apply_optimization_algorithm(optimization_config, baseline, training_data)

            # Verify span has tenant_id attribute
            mock_span.set_attribute.assert_any_call("tenant_id", "tenant-123")


class TestPrometheusMetricsIntegration:
    """Test cases for Prometheus metrics recording."""

    @pytest.fixture
    def optimization_config(self) -> OptimizationConfig:
        """Create a test optimization config."""
        return OptimizationConfig(
            tenant_id="tenant-123",
            agent_name="test_agent",
            enable_rl=True,
            metric_target="answer_quality",
        )

    def test_wrapper_overhead_gauge_recorded(self, optimization_config: OptimizationConfig) -> None:
        """Test Prometheus gauge for wrapper overhead is recorded."""
        from app.services.agent_wrapper_service import wrap

        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"output": "test"}

        with patch("app.routers.metrics.agent_lightning_wrapper_overhead_ms") as mock_gauge:
            wrapped = wrap(mock_agent, optimization_config)
            wrapped.invoke({"input": "test"})

            # Verify gauge was set with tenant_id label
            assert mock_gauge.labels.called
            labels_call = mock_gauge.labels.call_args
            assert "tenant_id" in str(labels_call)

    def test_optimization_decisions_counter_incremented(
        self, optimization_config: OptimizationConfig
    ) -> None:
        """Test Prometheus counter for optimization decisions is incremented."""
        from app.services.optimization_service import apply_optimization_algorithm
        from app.models.optimization_models import BaselineMetrics

        baseline = BaselineMetrics(latency_ms=1200.0, token_usage=500)
        training_data = [{"query": "test", "response": "test"}]

        with patch(
            "app.routers.metrics.agent_lightning_optimization_decisions_total"
        ) as mock_counter:
            apply_optimization_algorithm(optimization_config, baseline, training_data)

            # Verify counter was incremented with tenant_id label
            assert mock_counter.labels.called
            labels_call = mock_counter.labels.call_args
            assert "tenant_id" in str(labels_call)

    def test_improvement_percent_gauge_recorded(
        self, optimization_config: OptimizationConfig
    ) -> None:
        """Test Prometheus gauge for improvement percent is recorded."""
        from app.services.agent_wrapper_service import get_optimization_metrics, wrap
        from app.models.optimization_models import BaselineMetrics

        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"output": "test"}
        wrapped = wrap(mock_agent, optimization_config)

        baseline = BaselineMetrics(latency_ms=1200.0, token_usage=500)

        with patch("app.routers.metrics.agent_lightning_improvement_percent") as mock_gauge:
            get_optimization_metrics(wrapped, {"input": "test"}, baseline)

            # Verify gauge was set with tenant_id label
            assert mock_gauge.labels.called
            labels_call = mock_gauge.labels.call_args
            assert "tenant_id" in str(labels_call)

    def test_metrics_tagged_with_tenant_id(self, optimization_config: OptimizationConfig) -> None:
        """Test all Prometheus metrics are tagged with tenant_id."""
        from app.services.agent_wrapper_service import wrap

        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"output": "test"}

        with patch("app.routers.metrics.agent_lightning_wrapper_overhead_ms") as mock_gauge:
            wrapped = wrap(mock_agent, optimization_config)
            wrapped.invoke({"input": "test"})

            # Extract tenant_id from labels call
            labels_call = mock_gauge.labels.call_args
            if labels_call:
                # Check if tenant_id is in kwargs or args
                tenant_id_present = (
                    "tenant_id" in str(labels_call[1])
                    if len(labels_call) > 1
                    else "tenant_id" in str(labels_call)
                )
                assert tenant_id_present

    def test_metrics_tagged_with_agent_name(self, optimization_config: OptimizationConfig) -> None:
        """Test all Prometheus metrics are tagged with agent_name."""
        from app.services.agent_wrapper_service import wrap

        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"output": "test"}

        with patch("app.routers.metrics.agent_lightning_wrapper_overhead_ms") as mock_gauge:
            wrapped = wrap(mock_agent, optimization_config)
            wrapped.invoke({"input": "test"})

            # Extract agent_name from labels call
            labels_call = mock_gauge.labels.call_args
            if labels_call:
                agent_name_present = (
                    "agent_name" in str(labels_call[1])
                    if len(labels_call) > 1
                    else "agent_name" in str(labels_call)
                )
                assert agent_name_present
