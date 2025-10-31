"""Integration tests for Agent Lightning OpenTelemetry instrumentation.

Tests that Agent Lightning optimization workflows are properly instrumented with
OpenTelemetry spans for debugging, tracing, and observability.

Written FIRST per TDD approach - these tests should FAIL until implementation is complete.
"""

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


class TestAgentLightningSpans:
    """Test cases for Agent Lightning OpenTelemetry span creation."""

    @pytest.fixture(scope="class")
    def tracer_setup(self):
        """Set up in-memory span exporter for testing."""
        # Create in-memory exporter to capture spans
        exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        yield exporter

        # Cleanup after all tests
        exporter.clear()

    def test_optimization_decision_span_created_with_attributes(
        self, tracer_setup: InMemorySpanExporter
    ) -> None:
        """Test OpenTelemetry span created for optimization decision with correct attributes."""
        from app.core.agent_lightning_observability import AgentLightningTracer

        # Clear any previous spans
        tracer_setup.clear()

        tracer_obj = AgentLightningTracer(tenant_id="tenant-123")

        # Create optimization decision span
        with tracer_obj.create_optimization_decision_span(
            agent_name="query_planner", algorithm="rl", reason="baseline_latency_high"
        ):
            pass  # Simulate optimization decision

        # Verify span was created and exported
        spans = tracer_setup.get_finished_spans()
        assert len(spans) == 1

        span = spans[0]
        assert span.name == "agent_lightning.optimization_decision"

        # Verify required attributes
        attributes = dict(span.attributes)
        assert attributes["tenant_id"] == "tenant-123"
        assert attributes["agent_name"] == "query_planner"
        assert attributes["algorithm"] == "rl"
        assert attributes["reason"] == "baseline_latency_high"

    def test_metrics_collection_span_created_with_attributes(
        self, tracer_setup: InMemorySpanExporter
    ) -> None:
        """Test OpenTelemetry span created for metrics collection with correct attributes."""
        from app.core.agent_lightning_observability import AgentLightningTracer

        # Clear any previous spans
        tracer_setup.clear()

        tracer_obj = AgentLightningTracer(tenant_id="tenant-456")

        # Create metrics collection span
        with tracer_obj.create_metrics_collection_span(
            agent_name="document_analyzer",
            metric_count=5,
            baseline_latency_ms=1200.0,
            baseline_tokens=500,
        ):
            pass  # Simulate metrics collection

        # Verify span was created and exported
        spans = tracer_setup.get_finished_spans()
        assert len(spans) == 1

        span = spans[0]
        assert span.name == "agent_lightning.metrics_collection"

        # Verify required attributes
        attributes = dict(span.attributes)
        assert attributes["tenant_id"] == "tenant-456"
        assert attributes["agent_name"] == "document_analyzer"
        assert attributes["metric_count"] == 5
        assert attributes["baseline_latency_ms"] == 1200.0
        assert attributes["baseline_tokens"] == 500

    def test_roi_calculation_span_created_with_attributes(
        self, tracer_setup: InMemorySpanExporter
    ) -> None:
        """Test OpenTelemetry span created for ROI calculation with correct attributes."""
        from app.core.agent_lightning_observability import AgentLightningTracer

        # Clear any previous spans
        tracer_setup.clear()

        tracer_obj = AgentLightningTracer(tenant_id="tenant-789")

        # Create ROI calculation span
        with tracer_obj.create_roi_calculation_span(
            agent_name="answer_generator",
            improvement_percent=18.5,
            token_savings=150,
            cost_reduction_usd=0.0045,
            roi_dollars=12.75,
        ):
            pass  # Simulate ROI calculation

        # Verify span was created and exported
        spans = tracer_setup.get_finished_spans()
        assert len(spans) == 1

        span = spans[0]
        assert span.name == "agent_lightning.roi_calculation"

        # Verify required attributes
        attributes = dict(span.attributes)
        assert attributes["tenant_id"] == "tenant-789"
        assert attributes["agent_name"] == "answer_generator"
        assert attributes["improvement_percent"] == 18.5
        assert attributes["token_savings"] == 150
        assert attributes["cost_reduction_usd"] == 0.0045
        assert attributes["roi_dollars"] == 12.75

    def test_span_hierarchies_parent_child_relationships(
        self, tracer_setup: InMemorySpanExporter
    ) -> None:
        """Test span hierarchies are correct (parent-child relationships)."""
        from app.core.agent_lightning_observability import AgentLightningTracer

        # Clear any previous spans
        tracer_setup.clear()

        tracer_obj = AgentLightningTracer(tenant_id="tenant-hierarchy")

        # Create parent span (optimization decision)
        with tracer_obj.create_optimization_decision_span(
            agent_name="query_planner", algorithm="rl", reason="baseline_quality_low"
        ):
            # Create child span (metrics collection)
            with tracer_obj.create_metrics_collection_span(
                agent_name="query_planner",
                metric_count=3,
                baseline_latency_ms=800.0,
                baseline_tokens=300,
            ):
                pass

            # Create another child span (ROI calculation)
            with tracer_obj.create_roi_calculation_span(
                agent_name="query_planner",
                improvement_percent=15.0,
                token_savings=50,
                cost_reduction_usd=0.0015,
                roi_dollars=5.25,
            ):
                pass

        # Verify span hierarchy
        spans = tracer_setup.get_finished_spans()
        assert len(spans) == 3

        # Find parent and children
        parent_span = next(s for s in spans if s.name == "agent_lightning.optimization_decision")
        child_spans = [
            s for s in spans if s.parent and s.parent.span_id == parent_span.context.span_id
        ]

        assert len(child_spans) == 2
        assert any(s.name == "agent_lightning.metrics_collection" for s in child_spans)
        assert any(s.name == "agent_lightning.roi_calculation" for s in child_spans)

    def test_all_spans_tagged_with_tenant_id(self, tracer_setup: InMemorySpanExporter) -> None:
        """Test all spans are tagged with tenant_id for multi-tenant correlation."""
        from app.core.agent_lightning_observability import AgentLightningTracer

        # Clear any previous spans
        tracer_setup.clear()

        tenant_id = "tenant-multi-tenant-test"
        tracer_obj = AgentLightningTracer(tenant_id=tenant_id)  # Create multiple spans
        with tracer_obj.create_optimization_decision_span(
            agent_name="query_planner", algorithm="rl", reason="test"
        ):
            pass

        with tracer_obj.create_metrics_collection_span(
            agent_name="document_analyzer",
            metric_count=3,
            baseline_latency_ms=1000.0,
            baseline_tokens=400,
        ):
            pass

        with tracer_obj.create_roi_calculation_span(
            agent_name="answer_generator",
            improvement_percent=12.0,
            token_savings=100,
            cost_reduction_usd=0.003,
            roi_dollars=8.5,
        ):
            pass

        # Verify all spans have tenant_id
        spans = tracer_setup.get_finished_spans()
        assert len(spans) == 3

        for span in spans:
            attributes = dict(span.attributes)
            assert "tenant_id" in attributes
            assert attributes["tenant_id"] == tenant_id

    def test_span_with_exception_records_error(self, tracer_setup: InMemorySpanExporter) -> None:
        """Test span records exception when error occurs during operation."""
        from app.core.agent_lightning_observability import AgentLightningTracer

        # Clear any previous spans
        tracer_setup.clear()

        tracer_obj = AgentLightningTracer(tenant_id="tenant-error")

        # Create span that encounters error
        try:
            with tracer_obj.create_optimization_decision_span(
                agent_name="query_planner", algorithm="rl", reason="test_error"
            ):
                raise ValueError("Simulated optimization error")
        except ValueError:
            pass  # Expected error

        # Verify span recorded the error
        spans = tracer_setup.get_finished_spans()
        assert len(spans) == 1

        span = spans[0]
        # Check span status indicates error
        assert span.status.is_ok is False

        # Check span events contain exception
        events = list(span.events)
        assert len(events) > 0
        assert any("exception" in event.name.lower() for event in events)
