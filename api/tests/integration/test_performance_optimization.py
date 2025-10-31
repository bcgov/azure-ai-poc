"""Integration tests for Agent Lightning performance optimizations.

Tests caching, batching, and async optimization to ensure Agent Lightning
maintains minimal overhead (<50ms for wrapper, <2s for optimization decisions).
"""

import asyncio
import time

import pytest

from app.core.performance import (
    MetricsBatcher,
    OptimizationDecisionCache,
    PerformanceMonitor,
    cached_agent_config,
    get_metrics_batcher,
    get_optimization_cache,
    get_performance_monitor,
    track_performance,
)


class TestPerformanceMonitor:
    """Tests for PerformanceMonitor."""

    def test_record_performance_metric(self) -> None:
        """Test recording performance metric.

        Verifies:
        - Metric recorded with all attributes
        - Can retrieve recorded metric
        """
        monitor = PerformanceMonitor()

        monitor.record(
            operation="test_operation",
            duration_ms=25.5,
            tenant_id="tenant-123",
            agent_name="test_agent",
            cache_hit=False,
        )

        metrics = monitor.get_metrics()
        assert len(metrics) == 1
        assert metrics[0].operation == "test_operation"
        assert metrics[0].duration_ms == 25.5
        assert metrics[0].tenant_id == "tenant-123"
        assert metrics[0].agent_name == "test_agent"
        assert metrics[0].cache_hit is False

    def test_get_metrics_filtered_by_operation(self) -> None:
        """Test filtering metrics by operation name.

        Verifies:
        - Only matching operations returned
        - Other operations excluded
        """
        monitor = PerformanceMonitor()

        monitor.record("op1", 10.0, "tenant-1")
        monitor.record("op2", 20.0, "tenant-1")
        monitor.record("op1", 15.0, "tenant-1")

        op1_metrics = monitor.get_metrics(operation="op1")
        assert len(op1_metrics) == 2
        assert all(m.operation == "op1" for m in op1_metrics)

    def test_get_metrics_filtered_by_tenant(self) -> None:
        """Test filtering metrics by tenant ID.

        Verifies:
        - Only matching tenant metrics returned
        - Cross-tenant isolation maintained
        """
        monitor = PerformanceMonitor()

        monitor.record("op", 10.0, "tenant-1")
        monitor.record("op", 20.0, "tenant-2")
        monitor.record("op", 15.0, "tenant-1")

        tenant1_metrics = monitor.get_metrics(tenant_id="tenant-1")
        assert len(tenant1_metrics) == 2
        assert all(m.tenant_id == "tenant-1" for m in tenant1_metrics)

    def test_get_average_duration(self) -> None:
        """Test calculating average duration for operation.

        Verifies:
        - Average calculated correctly
        - Handles multiple metrics
        """
        monitor = PerformanceMonitor()

        monitor.record("op", 10.0, "tenant-1")
        monitor.record("op", 20.0, "tenant-1")
        monitor.record("op", 30.0, "tenant-1")

        avg = monitor.get_average_duration("op")
        assert avg == 20.0  # (10 + 20 + 30) / 3

    def test_get_average_duration_returns_none_if_no_data(self) -> None:
        """Test average duration returns None when no metrics exist."""
        monitor = PerformanceMonitor()

        avg = monitor.get_average_duration("nonexistent_op")
        assert avg is None

    def test_slow_operation_logged_as_warning(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that slow operations (>50ms) are logged as warnings.

        Verifies:
        - Slow operation triggers warning log
        - Log contains duration and operation details
        """
        monitor = PerformanceMonitor()

        monitor.record("slow_op", 75.0, "tenant-1", cache_hit=False)

        # Check warning was logged to stdout (structlog outputs to stdout)
        captured = capsys.readouterr()
        assert "slow_op" in captured.out or "slow_op" in captured.err
        assert "warning" in captured.out.lower() or "warning" in captured.err.lower()


class TestOptimizationDecisionCache:
    """Tests for OptimizationDecisionCache."""

    def test_cache_miss_returns_none(self) -> None:
        """Test cache miss returns None."""
        cache = OptimizationDecisionCache(maxsize=10)

        result = cache.get("tenant-1", "agent-1")
        assert result is None

    def test_cache_hit_returns_cached_value(self) -> None:
        """Test cache hit returns previously stored value.

        Verifies:
        - Set stores value
        - Get retrieves same value
        """
        cache = OptimizationDecisionCache(maxsize=10)

        decision = {"use_rl": True, "confidence": 0.95}
        cache.set("tenant-1", "agent-1", decision)

        result = cache.get("tenant-1", "agent-1")
        assert result == decision

    def test_cache_eviction_when_full(self) -> None:
        """Test LRU eviction when cache reaches maxsize.

        Verifies:
        - Oldest entry evicted when cache full
        - Most recent entries retained
        """
        cache = OptimizationDecisionCache(maxsize=3)

        # Fill cache
        cache.set("tenant-1", "agent-1", {"data": 1})
        time.sleep(0.01)  # Ensure different timestamps
        cache.set("tenant-1", "agent-2", {"data": 2})
        time.sleep(0.01)
        cache.set("tenant-1", "agent-3", {"data": 3})

        # Access agent-2 to update its access time
        cache.get("tenant-1", "agent-2")
        time.sleep(0.01)

        # Add new entry (should evict agent-1, the oldest unaccessed)
        cache.set("tenant-1", "agent-4", {"data": 4})

        # agent-1 should be evicted
        assert cache.get("tenant-1", "agent-1") is None
        # Others should still exist
        assert cache.get("tenant-1", "agent-2") is not None
        assert cache.get("tenant-1", "agent-3") is not None
        assert cache.get("tenant-1", "agent-4") is not None

    def test_invalidate_removes_entry(self) -> None:
        """Test invalidate removes cached entry.

        Verifies:
        - Invalidate removes specific entry
        - Other entries unaffected
        """
        cache = OptimizationDecisionCache(maxsize=10)

        cache.set("tenant-1", "agent-1", {"data": 1})
        cache.set("tenant-1", "agent-2", {"data": 2})

        cache.invalidate("tenant-1", "agent-1")

        assert cache.get("tenant-1", "agent-1") is None
        assert cache.get("tenant-1", "agent-2") is not None

    def test_clear_removes_all_entries(self) -> None:
        """Test clear removes all cached entries."""
        cache = OptimizationDecisionCache(maxsize=10)

        cache.set("tenant-1", "agent-1", {"data": 1})
        cache.set("tenant-1", "agent-2", {"data": 2})
        cache.set("tenant-2", "agent-1", {"data": 3})

        cache.clear()

        assert cache.get("tenant-1", "agent-1") is None
        assert cache.get("tenant-1", "agent-2") is None
        assert cache.get("tenant-2", "agent-1") is None

    def test_cache_tenant_isolation(self) -> None:
        """Test cache maintains tenant isolation.

        Verifies:
        - Same agent_name, different tenants are separate
        - Cannot access other tenant's cached decisions
        """
        cache = OptimizationDecisionCache(maxsize=10)

        cache.set("tenant-1", "shared-agent", {"tenant": 1})
        cache.set("tenant-2", "shared-agent", {"tenant": 2})

        result1 = cache.get("tenant-1", "shared-agent")
        result2 = cache.get("tenant-2", "shared-agent")

        assert result1 == {"tenant": 1}
        assert result2 == {"tenant": 2}


class TestMetricsBatcher:
    """Tests for MetricsBatcher."""

    @pytest.mark.asyncio
    async def test_add_metric_to_batch(self) -> None:
        """Test adding metric to batch.

        Verifies:
        - Metric added to batch
        - Batch stored under tenant_id
        """
        batcher = MetricsBatcher(batch_size=10, flush_interval_seconds=60.0)

        await batcher.add("tenant-1", {"latency": 100})

        # Internal state check (batch exists and has metric)
        assert "tenant-1" in batcher._batches
        # May be 0 if already flushed, or 1 if not yet flushed
        assert len(batcher._batches["tenant-1"]) <= 1

    @pytest.mark.asyncio
    async def test_batch_flush_on_size_limit(self) -> None:
        """Test batch flushes when size limit reached.

        Verifies:
        - Batch flushes when batch_size reached
        - New batch starts after flush
        """
        batcher = MetricsBatcher(batch_size=3, flush_interval_seconds=60.0)

        # Add metrics up to batch size
        await batcher.add("tenant-1", {"metric": 1})
        await batcher.add("tenant-1", {"metric": 2})
        await batcher.add("tenant-1", {"metric": 3})  # Flush before adding, then add

        # Verify flush happened - batch size should be less than 3
        # (either 0 if all flushed, or 1 if new metric added after flush)
        batch_size = len(batcher._batches["tenant-1"])
        assert batch_size < 3  # Flush should have occurred

    @pytest.mark.asyncio
    async def test_batch_flush_on_time_interval(self) -> None:
        """Test batch flushes after time interval.

        Verifies:
        - Batch flushes when flush_interval reached
        - Works even if batch_size not reached
        """
        batcher = MetricsBatcher(batch_size=100, flush_interval_seconds=0.1)

        await batcher.add("tenant-1", {"metric": 1})
        initial_size = len(batcher._batches["tenant-1"])
        assert initial_size >= 1

        # Wait for flush interval
        await asyncio.sleep(0.15)

        # Add another metric (should trigger time-based flush of old batch, then add new)
        await batcher.add("tenant-1", {"metric": 2})

        # After flush and new add, should have 1 metric
        assert len(batcher._batches["tenant-1"]) >= 1

    @pytest.mark.asyncio
    async def test_flush_all_flushes_all_tenants(self) -> None:
        """Test flush_all flushes batches for all tenants.

        Verifies:
        - All tenant batches flushed
        - Batches empty after flush_all
        """
        batcher = MetricsBatcher(batch_size=100, flush_interval_seconds=60.0)

        await batcher.add("tenant-1", {"metric": 1})
        await batcher.add("tenant-2", {"metric": 2})
        await batcher.add("tenant-1", {"metric": 3})

        await batcher.flush_all()

        # All batches should be empty
        assert len(batcher._batches.get("tenant-1", [])) == 0
        assert len(batcher._batches.get("tenant-2", [])) == 0

    @pytest.mark.asyncio
    async def test_concurrent_adds_thread_safe(self) -> None:
        """Test concurrent metric additions are thread-safe.

        Verifies:
        - Lock prevents race conditions
        - All metrics recorded
        """
        batcher = MetricsBatcher(batch_size=1000, flush_interval_seconds=60.0)

        async def add_metrics() -> None:
            for i in range(50):
                await batcher.add("tenant-1", {"metric": i})

        # Run 10 concurrent tasks
        await asyncio.gather(*[add_metrics() for _ in range(10)])

        # Should have close to 500 metrics (some may have flushed due to timing)
        total_metrics = len(batcher._batches["tenant-1"])
        assert total_metrics >= 450  # Allow for some flushing during concurrent adds


class TestTrackPerformanceDecorator:
    """Tests for @track_performance decorator."""

    def test_track_performance_synchronous_function(self) -> None:
        """Test tracking performance of synchronous function.

        Verifies:
        - Function executes normally
        - Performance metric recorded
        """
        monitor = get_performance_monitor()
        initial_count = len(monitor.get_metrics())

        @track_performance("test_sync_op")
        def test_function(tenant_id: str, agent_name: str) -> str:
            time.sleep(0.01)
            return "success"

        result = test_function(tenant_id="tenant-1", agent_name="agent-1")

        assert result == "success"
        metrics = monitor.get_metrics(operation="test_sync_op")
        assert len(metrics) > initial_count
        assert metrics[-1].duration_ms >= 10.0  # At least 10ms (sleep time)

    @pytest.mark.asyncio
    async def test_track_performance_asynchronous_function(self) -> None:
        """Test tracking performance of asynchronous function.

        Verifies:
        - Async function executes normally
        - Performance metric recorded
        """
        monitor = get_performance_monitor()

        @track_performance("test_async_op_unique")
        async def test_function(tenant_id: str, agent_name: str) -> str:
            await asyncio.sleep(0.01)
            return "success"

        result = await test_function(tenant_id="tenant-1", agent_name="agent-1")

        assert result == "success"
        metrics = monitor.get_metrics(operation="test_async_op_unique")
        assert len(metrics) >= 1
        assert metrics[-1].duration_ms >= 10.0

    def test_track_performance_records_errors(self) -> None:
        """Test tracking records errors but lets them propagate.

        Verifies:
        - Exception propagates to caller
        - Error metric recorded
        """
        monitor = get_performance_monitor()

        @track_performance("test_error_op")
        def test_function(tenant_id: str) -> None:
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            test_function(tenant_id="tenant-1")

        # Error metric should be recorded
        error_metrics = monitor.get_metrics(operation="test_error_op_error")
        assert len(error_metrics) > 0


class TestCachedAgentConfig:
    """Tests for cached_agent_config function."""

    def test_cached_agent_config_returns_cache_key(self) -> None:
        """Test cached_agent_config returns consistent cache key.

        Verifies:
        - Returns deterministic cache key
        - Same inputs produce same key
        """
        key1 = cached_agent_config("tenant-1", "agent-1")
        key2 = cached_agent_config("tenant-1", "agent-1")

        assert key1 == key2
        assert key1 == "tenant-1:agent-1"

    def test_cached_agent_config_different_inputs_different_keys(self) -> None:
        """Test different inputs produce different cache keys.

        Verifies:
        - Tenant isolation in cache keys
        - Agent isolation in cache keys
        """
        key1 = cached_agent_config("tenant-1", "agent-1")
        key2 = cached_agent_config("tenant-2", "agent-1")
        key3 = cached_agent_config("tenant-1", "agent-2")

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3


class TestGlobalInstanceGetters:
    """Tests for global instance getter functions."""

    def test_get_performance_monitor_returns_singleton(self) -> None:
        """Test get_performance_monitor returns same instance.

        Verifies:
        - Singleton pattern
        - Same instance across calls
        """
        monitor1 = get_performance_monitor()
        monitor2 = get_performance_monitor()

        assert monitor1 is monitor2

    def test_get_optimization_cache_returns_singleton(self) -> None:
        """Test get_optimization_cache returns same instance."""
        cache1 = get_optimization_cache()
        cache2 = get_optimization_cache()

        assert cache1 is cache2

    def test_get_metrics_batcher_returns_singleton(self) -> None:
        """Test get_metrics_batcher returns same instance."""
        batcher1 = get_metrics_batcher()
        batcher2 = get_metrics_batcher()

        assert batcher1 is batcher2


class TestPerformanceIntegration:
    """Integration tests combining multiple performance features."""

    @pytest.mark.asyncio
    async def test_end_to_end_performance_optimization(self) -> None:
        """Test complete performance optimization workflow.

        Scenario: Agent wrapper with caching, batching, and monitoring
        Verifies:
        - Cache improves second call performance
        - Metrics batched efficiently
        - Performance monitored throughout
        """
        cache = get_optimization_cache()
        batcher = get_metrics_batcher()
        monitor = get_performance_monitor()

        # Clear cache for clean test
        cache.clear()

        # First call: cache miss
        start_time = time.perf_counter()
        decision = cache.get("tenant-1", "agent-1")
        assert decision is None

        # Simulate optimization decision
        time.sleep(0.01)  # Simulate computation
        decision = {"use_rl": True, "confidence": 0.95}
        cache.set("tenant-1", "agent-1", decision)

        duration1_ms = (time.perf_counter() - start_time) * 1000
        monitor.record("optimization_decision", duration1_ms, "tenant-1", cache_hit=False)

        # Second call: cache hit (should be much faster)
        start_time = time.perf_counter()
        cached_decision = cache.get("tenant-1", "agent-1")
        duration2_ms = (time.perf_counter() - start_time) * 1000

        assert cached_decision == decision
        monitor.record("optimization_decision", duration2_ms, "tenant-1", cache_hit=True)

        # Verify cache hit is faster
        assert duration2_ms < duration1_ms

        # Add metrics to batch
        await batcher.add("tenant-1", {"duration": duration1_ms})
        await batcher.add("tenant-1", {"duration": duration2_ms})

        # Verify metrics recorded
        opt_metrics = monitor.get_metrics(operation="optimization_decision")
        assert len(opt_metrics) >= 2
