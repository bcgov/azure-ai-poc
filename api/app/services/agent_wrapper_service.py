"""Agent wrapper service for Agent Lightning integration.

This module provides the core wrapper functionality that wraps LangGraph/LangChain
agents with Agent Lightning optimization while preserving their original API.
"""

import asyncio
import time
from typing import Any

from app.core.logger import get_logger
from app.models.optimization_models import (
    BaselineMetrics,
    OptimizationConfig,
    OptimizationMetrics,
)

logger = get_logger(__name__)


class AgentWrapper:
    """Wrapper that adds Agent Lightning optimization to any agent.

    This wrapper transparently adds optimization capabilities while preserving
    the original agent's API and behavior. Wrapper failures never break the
    underlying agent execution.
    """

    def __init__(self, agent: Any, config: OptimizationConfig) -> None:
        """Initialize the agent wrapper.

        Args:
            agent: The original LangGraph/LangChain agent to wrap
            config: Optimization configuration for this agent
        """
        self._agent = agent
        self._config = config
        self._metrics_collected = 0

        # Preserve agent attributes
        self._copy_agent_attributes(agent)

    def _copy_agent_attributes(self, agent: Any) -> None:
        """Copy custom attributes from original agent to wrapper.

        Args:
            agent: Original agent whose attributes should be preserved
        """
        # Copy all non-private attributes
        for attr_name in dir(agent):
            if not attr_name.startswith("_") and not callable(getattr(agent, attr_name)):
                try:
                    setattr(self, attr_name, getattr(agent, attr_name))
                except (AttributeError, TypeError):
                    # Some attributes may not be copyable, skip them
                    pass

    def invoke(self, query: dict[str, Any]) -> dict[str, Any]:
        """Invoke the wrapped agent (synchronous).

        Args:
            query: Input query for the agent

        Returns:
            Agent response (identical schema to original agent)
        """
        # Extract tenant_id from query if available (dynamic per-request)
        tenant_id = self._extract_tenant_id(query)

        # Log that wrapper is being invoked
        logger.info(
            "🚀 AGENT_LIGHTNING_WRAPPER_INVOKED",
            tenant_id=tenant_id,
            agent_name=self._config.agent_name,
            method="invoke",
            wrapper_active=True,
        )

        start_time = time.perf_counter()

        try:
            # Call original agent
            response = self._agent.invoke(query)

            # Collect metrics (failures don't break execution)
            # Run async collection in background task (for sync invoke)
            try:
                asyncio.create_task(self._collect_metrics(query, response, start_time, tenant_id))
            except Exception as e:
                logger.warning(
                    "agent_wrapper_metrics_collection_failed",
                    error=str(e),
                    tenant_id=tenant_id,
                    agent_name=self._config.agent_name,
                )

            return response

        except Exception:
            # Agent exceptions propagate unchanged
            raise

    async def ainvoke(self, query: dict[str, Any]) -> dict[str, Any]:
        """Invoke the wrapped agent (asynchronous).

        Args:
            query: Input query for the agent

        Returns:
            Agent response (identical schema to original agent)
        """
        # Extract tenant_id from query if available (dynamic per-request)
        tenant_id = self._extract_tenant_id(query)

        # Log that wrapper is being invoked
        logger.info(
            "🚀 AGENT_LIGHTNING_WRAPPER_INVOKED",
            tenant_id=tenant_id,
            agent_name=self._config.agent_name,
            method="ainvoke",
            wrapper_active=True,
        )

        start_time = time.perf_counter()

        try:
            # Call original agent
            response = await self._agent.ainvoke(query)

            # Collect metrics (failures don't break execution)
            try:
                await self._collect_metrics(query, response, start_time, tenant_id)
            except Exception as e:
                logger.warning(
                    "agent_wrapper_metrics_collection_failed",
                    error=str(e),
                    tenant_id=tenant_id,
                    agent_name=self._config.agent_name,
                )

            return response

        except Exception:
            # Agent exceptions propagate unchanged
            raise

    def _extract_tenant_id(self, query: dict[str, Any]) -> str:
        """Extract tenant_id from query (e.g., from AgentState).

        Args:
            query: Input query dictionary

        Returns:
            Tenant ID (user_id from state, or fallback to config default)
        """
        # Try to extract from AgentState if it's a LangGraph state object
        if hasattr(query, "user_id") and query.user_id:
            return query.user_id

        # Try dictionary access for user_id
        if isinstance(query, dict):
            if "user_id" in query and query["user_id"]:
                return query["user_id"]

        # Fallback to config tenant_id
        return self._config.tenant_id

    async def _collect_metrics(
        self, query: dict[str, Any], response: dict[str, Any], start_time: float, tenant_id: str
    ) -> None:
        """Collect execution metrics for optimization.

        Args:
            query: Input query that was sent to agent
            response: Response received from agent
            start_time: Start time of agent execution (from perf_counter)
            tenant_id: Tenant ID for this specific request (extracted from AgentState)
        """
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000

        # Extract token usage if available
        token_usage = self._get_token_usage(response)

        self._metrics_collected += 1

        logger.info(
            "agent_wrapper_metrics_collected",
            tenant_id=tenant_id,
            agent_name=self._config.agent_name,
            latency_ms=latency_ms,
            token_usage=token_usage,
            metrics_count=self._metrics_collected,
        )

        # Store metrics in Cosmos DB for performance tracking
        # This runs in addition to the metrics collection in langgraph_agent_service
        try:
            from datetime import UTC, datetime

            from app.services.cosmos_db_service import get_cosmos_db_service

            # Calculate quality signal (simple heuristic based on response)
            quality_signal = self._calculate_quality_signal(response)

            # Convert query and response to JSON-serializable format
            # AgentState objects contain LangChain messages that aren't JSON serializable
            query_data = self._serialize_for_storage(query)
            response_data = self._serialize_for_storage(response)

            # Prepare metrics document for Cosmos DB
            metrics_doc = {
                "id": f"{tenant_id}_{self._config.agent_name}_{int(time.time() * 1000)}",
                "tenant_id": tenant_id,
                "agent_name": self._config.agent_name,
                "agent_metadata": {
                    "latency_ms": latency_ms,
                    "tokens": token_usage,
                    "wrapper_invocation": True,
                },
                "quality_signal": quality_signal,
                "timestamp": datetime.now(UTC).isoformat(),
                "query": query_data,
                "response": response_data,
            }

            # Store in Cosmos DB
            cosmos_service = get_cosmos_db_service()
            await cosmos_service.create_item(metrics_doc, partition_key=tenant_id)

            logger.info(
                "agent_wrapper_stored_metrics_to_cosmos",
                tenant_id=tenant_id,
                agent_name=self._config.agent_name,
                latency_ms=latency_ms,
                tokens=token_usage,
                quality_signal=quality_signal,
            )

        except Exception as e:
            # Don't let metrics storage failures affect agent execution
            logger.warning(
                "agent_wrapper_cosmos_storage_failed",
                error=str(e),
                tenant_id=tenant_id,
                agent_name=self._config.agent_name,
            )

    def _serialize_for_storage(self, data: Any) -> dict[str, Any]:
        """Convert data to JSON-serializable format for Cosmos DB storage.

        Args:
            data: Data to serialize (can be AgentState, dict, or other)

        Returns:
            JSON-serializable dictionary
        """
        if isinstance(data, dict):
            # Already a dict, but may contain non-serializable values
            serialized = {}
            for key, value in data.items():
                try:
                    # Try to serialize common types
                    if isinstance(value, (str, int, float, bool, type(None))):
                        serialized[key] = value
                    elif isinstance(value, list):
                        serialized[key] = [str(item) for item in value]
                    elif isinstance(value, dict):
                        serialized[key] = self._serialize_for_storage(value)
                    else:
                        # For objects like messages, convert to string
                        serialized[key] = str(value)
                except Exception:
                    # If all else fails, skip the field
                    pass
            return serialized
        elif hasattr(data, "user_id"):
            # AgentState object - extract key fields
            return {
                "user_id": getattr(data, "user_id", None),
                "session_id": getattr(data, "session_id", None),
                "workflow_id": getattr(data, "workflow_id", None),
                "step_count": getattr(data, "step_count", 0),
            }
        else:
            # Fallback: convert to string
            return {"data": str(data)}

    def _calculate_quality_signal(self, response: dict[str, Any]) -> float:
        """Calculate quality signal for the response.

        Args:
            response: Agent response

        Returns:
            Quality signal between 0.0 and 1.0
        """
        # Base quality
        quality = 0.5

        # Check if response contains expected fields
        if isinstance(response, dict):
            if "final_answer" in response and response["final_answer"]:
                quality += 0.2

            if "document_sources" in response and response["document_sources"]:
                quality += 0.2  # Bonus for document-grounded responses

            if "error" not in response:
                quality += 0.1

        return min(max(quality, 0.0), 1.0)

    def _get_token_usage(self, response: dict[str, Any]) -> int:
        """Extract token usage from agent response.

        Args:
            response: Agent response

        Returns:
            Token usage (defaults to 0 if not available)
        """
        # Check common metadata locations
        if "metadata" in response:
            if isinstance(response["metadata"], dict):
                return response["metadata"].get("tokens", 0)

        if "usage" in response:
            if isinstance(response["usage"], dict):
                return response["usage"].get("total_tokens", 0)

        # Default if not found
        return 0


def wrap(agent: Any, config: OptimizationConfig) -> Any:
    """Wrap an agent with Agent Lightning optimization.

    This is the primary integration point for adding Agent Lightning to
    existing agents. The wrapper preserves the agent's original API.

    Args:
        agent: The LangGraph/LangChain agent to wrap
        config: Optimization configuration for this agent

    Returns:
        Wrapped agent with Agent Lightning optimization (same API as original)

    Example:
        >>> from langgraph.graph import StateGraph
        >>> original_agent = StateGraph(...)
        >>> config = OptimizationConfig(tenant_id="tenant-123")
        >>> wrapped_agent = wrap(original_agent, config)
        >>> result = wrapped_agent.invoke(query)  # API unchanged
    """
    # Check if any optimizations are enabled
    any_enabled = config.enable_rl or config.enable_prompt_opt or config.enable_sft

    if not any_enabled:
        # No optimizations enabled, return original agent
        logger.debug(
            "agent_wrapper_skipped_no_optimizations",
            tenant_id=config.tenant_id,
            agent_name=config.agent_name,
        )
        return agent

    # Create and return wrapped agent
    wrapped = AgentWrapper(agent, config)

    logger.info(
        "agent_wrapper_created",
        tenant_id=config.tenant_id,
        agent_name=config.agent_name,
        enable_rl=config.enable_rl,
        enable_prompt_opt=config.enable_prompt_opt,
        enable_sft=config.enable_sft,
    )

    return wrapped


def get_baseline_metrics(agent: Any, query: dict[str, Any]) -> BaselineMetrics:
    """Get baseline performance metrics for an agent before optimization.

    Args:
        agent: The agent to measure (unwrapped)
        query: Test query to run for baseline measurement

    Returns:
        BaselineMetrics: Measured baseline performance

    Example:
        >>> baseline = get_baseline_metrics(agent, {"input": "test query"})
        >>> print(f"Baseline latency: {baseline.latency_ms}ms")
    """
    start_time = time.perf_counter()

    # Run agent to get baseline
    response = agent.invoke(query)

    end_time = time.perf_counter()
    latency_ms = (end_time - start_time) * 1000

    # Extract token usage
    token_usage = _extract_token_usage(response)

    return BaselineMetrics(
        latency_ms=latency_ms,
        token_usage=token_usage,
    )


def get_optimization_metrics(
    wrapped_agent: AgentWrapper, query: dict[str, Any], baseline: BaselineMetrics
) -> OptimizationMetrics:
    """Get optimization metrics by comparing wrapped agent to baseline.

    Args:
        wrapped_agent: The Agent Lightning wrapped agent
        query: Test query to run
        baseline: Baseline metrics for comparison

    Returns:
        OptimizationMetrics: Optimization results with improvements calculated

    Example:
        >>> wrapped = wrap(agent, config)
        >>> baseline = get_baseline_metrics(agent, query)
        >>> optimized = get_optimization_metrics(wrapped, query, baseline)
        >>> print(f"Token savings: {optimized.token_savings}")
    """
    start_time = time.perf_counter()

    # Run wrapped agent
    response = wrapped_agent.invoke(query)

    end_time = time.perf_counter()
    latency_ms = (end_time - start_time) * 1000

    # Extract token usage
    token_usage = _extract_token_usage(response)

    # Calculate improvements using factory method
    return OptimizationMetrics.from_baseline_comparison(
        baseline=baseline,
        optimized_latency_ms=latency_ms,
        optimized_token_usage=token_usage,
    )


def _extract_token_usage(response: dict[str, Any]) -> int:
    """Extract token usage from agent response.

    Args:
        response: Agent response dictionary

    Returns:
        Token usage (defaults to 0 if not available)
    """
    # Check common metadata locations
    if "metadata" in response:
        if isinstance(response["metadata"], dict):
            return response["metadata"].get("tokens", 0)

    if "usage" in response:
        if isinstance(response["usage"], dict):
            return response["usage"].get("total_tokens", 0)

    # Default if not found
    return 0
