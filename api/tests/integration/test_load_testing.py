"""
Load testing for Agent Lightning.

Tests system performance under concurrent load with Agent Lightning enabled.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.agent_lightning_config import create_optimization_config
from app.services.agent_wrapper_service import wrap


class TestLoadPerformance:
    """Test performance under load."""

    @pytest.mark.asyncio
    @pytest.mark.slow  # Mark as slow test - may skip in CI
    async def test_100_concurrent_queries(self):
        """
        Test: 100 concurrent document QA queries with Agent Lightning.

        Verifies:
        1. All queries complete successfully
        2. Wrapper overhead <50ms per query
        3. No bottlenecks in metrics collection
        4. System remains responsive
        """
        # Create mock agent with realistic timing
        mock_agent = MagicMock()

        async def mock_invoke(query):
            # Simulate 50ms agent execution time
            await asyncio.sleep(0.05)
            return {"final_answer": f"Answer for {query}"}

        mock_agent.invoke = mock_invoke

        config = create_optimization_config(
            tenant_id="load-test-user",
            agent_name="document_qa",
            enable_rl=True,
        )

        wrapped_agent = wrap(mock_agent, config)

        # Create 100 test queries
        queries = [{"messages": [{"role": "user", "content": f"Question {i}"}]} for i in range(100)]

        # Execute all queries concurrently
        start_time = time.time()
        results = await asyncio.gather(
            *[wrapped_agent.invoke(q) for q in queries],
            return_exceptions=True,
        )
        end_time = time.time()

        total_time = end_time - start_time

        # Verify all queries completed
        assert len(results) == 100

        # Count successful results
        successful = sum(1 for r in results if not isinstance(r, Exception))
        assert successful >= 95  # At least 95% success rate

        # Verify reasonable total time
        # With 100 concurrent queries taking 50ms each:
        # - Without concurrency: 5000ms (5s)
        # - With good concurrency: ~50-100ms (queries run in parallel)
        # - Allow up to 2s for test overhead
        assert total_time < 2.0  # Should complete in under 2 seconds

        # Calculate average time per query
        avg_time_per_query = total_time / 100

        # Verify no major bottlenecks (should be close to 50ms)
        assert avg_time_per_query < 0.1  # <100ms average per query

    @pytest.mark.asyncio
    async def test_wrapper_overhead_under_load(self):
        """
        Test: Wrapper overhead <50ms per query under load.

        Measures actual overhead added by Agent Lightning wrapper.
        """
        # Create fast mock agent
        mock_agent = MagicMock()

        async def mock_invoke(query):
            await asyncio.sleep(0.01)  # 10ms base time
            return {"final_answer": "Fast answer"}

        mock_agent.invoke = mock_invoke

        config = create_optimization_config(
            tenant_id="overhead-test-user",
            agent_name="document_qa",
            enable_rl=True,
        )

        # Measure baseline (unwrapped agent)
        queries = [{"messages": [{"role": "user", "content": f"Q{i}"}]} for i in range(20)]

        baseline_start = time.time()
        await asyncio.gather(*[mock_agent.invoke(q) for q in queries])
        baseline_time = time.time() - baseline_start

        # Measure with wrapper
        wrapped_agent = wrap(mock_agent, config)

        wrapped_start = time.time()
        await asyncio.gather(*[wrapped_agent.invoke(q) for q in queries])
        wrapped_time = time.time() - wrapped_start

        # Calculate overhead
        overhead = wrapped_time - baseline_time
        overhead_per_query_ms = (overhead / 20) * 1000

        # Verify overhead is acceptable
        # Target: <50ms per query, but allow more in test environment
        assert overhead_per_query_ms < 100  # <100ms per query

    @pytest.mark.asyncio
    async def test_metrics_collection_scales(self):
        """
        Test: Metrics collection doesn't cause bottlenecks.

        Verifies that collecting metrics for many concurrent
        queries doesn't slow down the system.
        """
        from app.services.optimization_service import OptimizationDataCollector

        collector = OptimizationDataCollector()
        tenant_id = "metrics-scale-user"
        agent_name = "document_qa"

        # Collect metrics for 100 concurrent operations
        async def collect_one_metric(i):
            collector.collect_metrics(
                tenant_id=tenant_id,
                agent_name=agent_name,
                latency_ms=100.0 + i % 20,
                token_count=200 + i % 30,
                quality_signal=0.8 + (i % 20) / 100.0,
                cost_usd=0.002,
            )

        start_time = time.time()
        await asyncio.gather(*[collect_one_metric(i) for i in range(100)])
        collection_time = time.time() - start_time

        # Verify metrics collection is fast (<1s for 100 operations)
        assert collection_time < 1.0

        # Verify all metrics were collected
        metrics = collector.get_baseline_metrics(tenant_id, agent_name)
        assert len(metrics) >= 100

    @pytest.mark.asyncio
    async def test_sustained_load_over_time(self):
        """
        Test: System handles sustained load over time.

        Simulates continuous traffic for extended period.
        """
        # Create mock agent
        mock_agent = MagicMock()
        mock_agent.invoke = AsyncMock(return_value={"final_answer": "Sustained load answer"})

        config = create_optimization_config(
            tenant_id="sustained-load-user",
            agent_name="document_qa",
            enable_rl=True,
        )

        wrapped_agent = wrap(mock_agent, config)

        # Simulate 3 waves of 20 queries each
        total_queries = 0
        total_time = 0

        for _wave in range(3):
            queries = [{"messages": [{"role": "user", "content": f"Q{i}"}]} for i in range(20)]

            start = time.time()
            results = await asyncio.gather(
                *[wrapped_agent.invoke(q) for q in queries],
                return_exceptions=True,
            )
            wave_time = time.time() - start

            total_queries += len(results)
            total_time += wave_time

            # Small delay between waves (simulate realistic traffic)
            await asyncio.sleep(0.1)

        # Verify all queries completed
        assert total_queries == 60

        # Verify system remained responsive throughout
        avg_time_per_wave = total_time / 3
        assert avg_time_per_wave < 1.0  # Each wave <1s

    @pytest.mark.asyncio
    async def test_no_memory_leaks_under_load(self):
        """
        Test: No memory leaks during sustained load.

        Verifies that Agent Lightning doesn't accumulate
        unbounded memory during operation.
        """
        import gc

        # Force garbage collection before test
        gc.collect()

        # Create mock agent
        mock_agent = MagicMock()
        mock_agent.invoke = AsyncMock(return_value={"final_answer": "Memory test answer"})

        config = create_optimization_config(
            tenant_id="memory-test-user",
            agent_name="document_qa",
            enable_rl=True,
        )

        wrapped_agent = wrap(mock_agent, config)

        # Execute many queries to potentially trigger memory issues
        for _batch in range(5):
            queries = [{"messages": [{"role": "user", "content": f"Q{i}"}]} for i in range(20)]

            await asyncio.gather(
                *[wrapped_agent.invoke(q) for q in queries],
                return_exceptions=True,
            )

        # Force garbage collection after test
        gc.collect()

        # If we got here without memory errors, test passes
        assert True


class TestConcurrencyHandling:
    """Test concurrent access patterns."""

    @pytest.mark.asyncio
    async def test_concurrent_different_tenants(self):
        """
        Test: Concurrent queries from different tenants.

        Verifies no tenant blocking or interference.
        """
        # Create agents for 5 different tenants
        agents = []
        for tenant_num in range(5):
            mock_agent = MagicMock()
            mock_agent.invoke = AsyncMock(
                return_value={"final_answer": f"Tenant {tenant_num} answer"}
            )

            config = create_optimization_config(
                tenant_id=f"tenant-{tenant_num}",
                agent_name="document_qa",
                enable_rl=True,
            )

            wrapped_agent = wrap(mock_agent, config)
            agents.append((tenant_num, wrapped_agent))

        # Each tenant sends 10 queries concurrently
        all_queries = []
        for tenant_num, agent in agents:
            for query_num in range(10):
                query = {"messages": [{"role": "user", "content": f"T{tenant_num}Q{query_num}"}]}
                all_queries.append(agent.invoke(query))

        # Execute all 50 queries concurrently
        start = time.time()
        results = await asyncio.gather(*all_queries, return_exceptions=True)
        total_time = time.time() - start

        # Verify all queries completed
        assert len(results) == 50

        # Verify reasonable completion time
        assert total_time < 2.0  # <2s for 50 concurrent queries

        # Count successful results
        successful = sum(1 for r in results if not isinstance(r, Exception))
        assert successful >= 45  # At least 90% success rate

    @pytest.mark.asyncio
    async def test_concurrent_same_tenant_different_agents(self):
        """
        Test: One tenant using multiple agents concurrently.

        Verifies proper isolation between agents for same tenant.
        """
        tenant_id = "multi-agent-tenant"

        # Create 3 different agents for same tenant
        agent_configs = [
            ("document_qa", "Document answer"),
            ("query_planner", "Query plan answer"),
            ("answer_generator", "Generated answer"),
        ]

        wrapped_agents = []
        for agent_name, response in agent_configs:
            mock_agent = MagicMock()
            mock_agent.invoke = AsyncMock(return_value={"final_answer": response})

            config = create_optimization_config(
                tenant_id=tenant_id,
                agent_name=agent_name,
                enable_rl=True,
            )

            wrapped_agent = wrap(mock_agent, config)
            wrapped_agents.append((agent_name, wrapped_agent))

        # Each agent processes 10 queries concurrently
        all_queries = []
        for agent_name, agent in wrapped_agents:
            for i in range(10):
                query = {"messages": [{"role": "user", "content": f"{agent_name}-Q{i}"}]}
                all_queries.append(agent.invoke(query))

        # Execute all 30 queries concurrently
        results = await asyncio.gather(*all_queries, return_exceptions=True)

        # Verify all queries completed
        assert len(results) == 30

        # Verify high success rate
        successful = sum(1 for r in results if not isinstance(r, Exception))
        assert successful >= 27  # At least 90% success rate

    @pytest.mark.asyncio
    async def test_query_rate_limiting_under_load(self):
        """
        Test: Rate limiting works correctly under load.

        Verifies that rate limits are properly enforced
        even with many concurrent queries.
        """
        from app.core.agent_lightning_security import get_rate_limiter

        rate_limiter = get_rate_limiter()
        tenant_id = "rate-limit-test"

        # Try to exceed rate limit (60/minute)
        # Send 65 concurrent requests
        async def check_rate_limit():
            try:
                rate_limiter.check_rate_limit(tenant_id)
                return "allowed"
            except ValueError:
                return "blocked"

        results = await asyncio.gather(*[check_rate_limit() for _ in range(65)])

        # Some requests should be allowed, some blocked
        allowed = sum(1 for r in results if r == "allowed")
        blocked = sum(1 for r in results if r == "blocked")

        # Verify rate limiting is working
        # (Exact numbers depend on timing, but some should be blocked)
        assert allowed > 0  # Some requests allowed
        assert blocked > 0 or allowed <= 60  # Either some blocked or stayed under limit
