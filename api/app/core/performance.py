"""Performance optimization utilities for Agent Lightning.

This module provides caching, batching, and async optimization to ensure
Agent Lightning operations have minimal overhead (<50ms for wrapper,
<2s for optimization decisions).
"""

import asyncio
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache, wraps
from typing import Any, TypeVar

from app.core.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class PerformanceMetrics:
    """Performance metrics for Agent Lightning operations."""

    operation: str
    duration_ms: float
    timestamp: float
    tenant_id: str
    agent_name: str | None = None
    cache_hit: bool = False


class PerformanceMonitor:
    """Monitor performance of Agent Lightning operations.

    Tracks operation durations and identifies slow operations
    that exceed target thresholds.
    """

    def __init__(self) -> None:
        """Initialize performance monitor."""
        self._metrics: list[PerformanceMetrics] = []
        self._slow_operation_threshold_ms = 50.0  # Target: <50ms wrapper overhead

    def record(
        self,
        operation: str,
        duration_ms: float,
        tenant_id: str,
        agent_name: str | None = None,
        cache_hit: bool = False,
    ) -> None:
        """Record performance metric.

        Args:
            operation: Name of operation performed
            duration_ms: Duration in milliseconds
            tenant_id: Tenant ID
            agent_name: Optional agent name
            cache_hit: Whether result came from cache
        """
        metric = PerformanceMetrics(
            operation=operation,
            duration_ms=duration_ms,
            timestamp=time.time(),
            tenant_id=tenant_id,
            agent_name=agent_name,
            cache_hit=cache_hit,
        )
        self._metrics.append(metric)

        # Log slow operations
        if duration_ms > self._slow_operation_threshold_ms and not cache_hit:
            logger.warning(
                f"Slow Agent Lightning operation: {operation}",
                extra={
                    "operation": operation,
                    "duration_ms": duration_ms,
                    "threshold_ms": self._slow_operation_threshold_ms,
                    "tenant_id": tenant_id,
                    "agent_name": agent_name,
                },
            )

    def get_metrics(
        self, operation: str | None = None, tenant_id: str | None = None
    ) -> list[PerformanceMetrics]:
        """Get performance metrics with optional filtering.

        Args:
            operation: Optional operation name filter
            tenant_id: Optional tenant ID filter

        Returns:
            List of matching performance metrics
        """
        metrics = self._metrics

        if operation:
            metrics = [m for m in metrics if m.operation == operation]

        if tenant_id:
            metrics = [m for m in metrics if m.tenant_id == tenant_id]

        return metrics

    def get_average_duration(self, operation: str, tenant_id: str | None = None) -> float | None:
        """Calculate average duration for an operation.

        Args:
            operation: Operation name
            tenant_id: Optional tenant ID filter

        Returns:
            Average duration in milliseconds, or None if no data
        """
        metrics = self.get_metrics(operation=operation, tenant_id=tenant_id)

        if not metrics:
            return None

        return sum(m.duration_ms for m in metrics) / len(metrics)


# Global performance monitor
_performance_monitor = PerformanceMonitor()


def track_performance(operation: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to track performance of function calls.

    Args:
        operation: Name of operation being tracked

    Returns:
        Decorated function that tracks execution time
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Extract tenant_id if available
                tenant_id = kwargs.get("tenant_id", "unknown")
                agent_name = kwargs.get("agent_name")

                _performance_monitor.record(
                    operation=operation,
                    duration_ms=duration_ms,
                    tenant_id=tenant_id,
                    agent_name=agent_name,
                )

                return result
            except Exception:
                # Record error but let it propagate
                duration_ms = (time.perf_counter() - start_time) * 1000
                _performance_monitor.record(
                    operation=f"{operation}_error",
                    duration_ms=duration_ms,
                    tenant_id=kwargs.get("tenant_id", "unknown"),
                    agent_name=kwargs.get("agent_name"),
                )
                raise

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Extract tenant_id if available
                tenant_id = kwargs.get("tenant_id", "unknown")
                agent_name = kwargs.get("agent_name")

                _performance_monitor.record(
                    operation=operation,
                    duration_ms=duration_ms,
                    tenant_id=tenant_id,
                    agent_name=agent_name,
                )

                return result
            except Exception:
                # Record error but let it propagate
                duration_ms = (time.perf_counter() - start_time) * 1000
                _performance_monitor.record(
                    operation=f"{operation}_error",
                    duration_ms=duration_ms,
                    tenant_id=kwargs.get("tenant_id", "unknown"),
                    agent_name=kwargs.get("agent_name"),
                )
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator


class OptimizationDecisionCache:
    """LRU cache for optimization decisions to avoid redundant computation.

    Caches optimization decisions per (tenant_id, agent_name) to reduce
    latency when the same agent is queried multiple times.
    """

    def __init__(self, maxsize: int = 128) -> None:
        """Initialize cache.

        Args:
            maxsize: Maximum number of cached decisions
        """
        self._cache: dict[tuple[str, str], Any] = {}
        self._maxsize = maxsize
        self._access_times: dict[tuple[str, str], float] = {}

    def get(self, tenant_id: str, agent_name: str) -> Any | None:
        """Get cached optimization decision.

        Args:
            tenant_id: Tenant ID
            agent_name: Agent name

        Returns:
            Cached decision or None if not found
        """
        key = (tenant_id, agent_name)
        if key in self._cache:
            self._access_times[key] = time.time()
            return self._cache[key]
        return None

    def set(self, tenant_id: str, agent_name: str, decision: Any) -> None:
        """Cache optimization decision.

        Args:
            tenant_id: Tenant ID
            agent_name: Agent name
            decision: Decision to cache
        """
        key = (tenant_id, agent_name)

        # Evict oldest entry if cache is full
        if len(self._cache) >= self._maxsize and key not in self._cache:
            oldest_key = min(self._access_times, key=self._access_times.get)  # type: ignore[arg-type]
            del self._cache[oldest_key]
            del self._access_times[oldest_key]

        self._cache[key] = decision
        self._access_times[key] = time.time()

    def invalidate(self, tenant_id: str, agent_name: str) -> None:
        """Invalidate cached decision.

        Args:
            tenant_id: Tenant ID
            agent_name: Agent name
        """
        key = (tenant_id, agent_name)
        if key in self._cache:
            del self._cache[key]
            del self._access_times[key]

    def clear(self) -> None:
        """Clear all cached decisions."""
        self._cache.clear()
        self._access_times.clear()


# Global optimization decision cache
_optimization_cache = OptimizationDecisionCache(maxsize=128)


class MetricsBatcher:
    """Batch metrics collection to reduce overhead.

    Collects metrics in batches and flushes periodically or when batch
    size is reached, reducing per-request overhead.
    """

    def __init__(self, batch_size: int = 50, flush_interval_seconds: float = 5.0) -> None:
        """Initialize metrics batcher.

        Args:
            batch_size: Number of metrics to collect before flushing
            flush_interval_seconds: Max seconds between flushes
        """
        self._batch_size = batch_size
        self._flush_interval = flush_interval_seconds
        self._batches: dict[str, list[Any]] = defaultdict(list)
        self._last_flush_time: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def add(self, tenant_id: str, metric: Any) -> None:
        """Add metric to batch.

        Args:
            tenant_id: Tenant ID
            metric: Metric to batch
        """
        async with self._lock:
            # Check if batch should be flushed BEFORE adding new metric
            should_flush = False

            if len(self._batches[tenant_id]) >= self._batch_size:
                should_flush = True

            last_flush = self._last_flush_time.get(tenant_id, 0)
            time_since_flush = time.time() - last_flush
            if len(self._batches[tenant_id]) > 0 and time_since_flush >= self._flush_interval:
                should_flush = True

            if should_flush:
                await self._flush(tenant_id)

            # Add metric after potential flush
            self._batches[tenant_id].append(metric)

    async def _flush(self, tenant_id: str) -> None:
        """Flush metrics batch to storage.

        Args:
            tenant_id: Tenant ID to flush
        """
        if tenant_id not in self._batches or not self._batches[tenant_id]:
            return

        batch = self._batches[tenant_id]
        self._batches[tenant_id] = []
        self._last_flush_time[tenant_id] = time.time()

        logger.debug(
            f"Flushing metrics batch for tenant {tenant_id}",
            extra={
                "tenant_id": tenant_id,
                "batch_size": len(batch),
            },
        )

        # TODO: Implement actual storage write
        # For now, just log
        pass

    async def flush_all(self) -> None:
        """Flush all pending metrics batches."""
        async with self._lock:
            for tenant_id in list(self._batches.keys()):
                await self._flush(tenant_id)


# Global metrics batcher
_metrics_batcher = MetricsBatcher(batch_size=50, flush_interval_seconds=5.0)


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance.

    Returns:
        Global performance monitor
    """
    return _performance_monitor


def get_optimization_cache() -> OptimizationDecisionCache:
    """Get global optimization decision cache instance.

    Returns:
        Global optimization decision cache
    """
    return _optimization_cache


def get_metrics_batcher() -> MetricsBatcher:
    """Get global metrics batcher instance.

    Returns:
        Global metrics batcher
    """
    return _metrics_batcher


@lru_cache(maxsize=256)
def cached_agent_config(tenant_id: str, agent_name: str) -> str:
    """Cache agent configuration lookups.

    Args:
        tenant_id: Tenant ID
        agent_name: Agent name

    Returns:
        Cache key for agent config
    """
    return f"{tenant_id}:{agent_name}"
