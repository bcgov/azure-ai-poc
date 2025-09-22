"""
Workflow observability service for LangGraph workflows.

This service provides comprehensive monitoring, logging, and analytics for
LangGraph workflow execution including:
- Workflow execution tracking and metrics
- Node performance monitoring
- Error reporting and debugging
- Workflow analytics and insights
"""

import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from app.core.logger import get_logger


class WorkflowNodeMetrics(BaseModel):
    """Metrics for a single workflow node execution."""

    node_name: str
    execution_id: str
    start_time: datetime
    end_time: datetime | None = None
    duration_ms: float | None = None
    status: str = "running"  # running, completed, failed
    error_message: str | None = None
    input_data_size: int | None = None
    output_data_size: int | None = None
    retry_count: int = 0


class WorkflowExecution(BaseModel):
    """Complete workflow execution tracking."""

    workflow_id: str
    workflow_type: str
    user_id: str | None = None
    session_id: str | None = None
    start_time: datetime
    end_time: datetime | None = None
    total_duration_ms: float | None = None
    status: str = "running"  # running, completed, failed, timeout
    node_executions: list[WorkflowNodeMetrics] = []
    total_nodes_executed: int = 0
    successful_nodes: int = 0
    failed_nodes: int = 0
    retry_attempts: int = 0
    input_parameters: dict[str, Any] = {}
    final_output: str | None = None
    error_summary: str | None = None


class WorkflowAnalytics(BaseModel):
    """Aggregated workflow analytics and insights."""

    time_period_start: datetime
    time_period_end: datetime
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    average_duration_ms: float = 0.0
    median_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    node_performance: dict[str, dict[str, float]] = {}
    common_error_types: dict[str, int] = {}
    user_activity: dict[str, int] = {}


class WorkflowObservabilityService:
    """
    Comprehensive observability service for LangGraph workflows.

    This service provides monitoring, logging, and analytics capabilities
    for tracking workflow execution, performance, and debugging issues.
    """

    def __init__(self):
        """Initialize the observability service."""
        self.logger = get_logger(__name__)
        self.active_workflows: dict[str, WorkflowExecution] = {}
        self.completed_workflows: dict[str, WorkflowExecution] = {}
        self.node_metrics: dict[str, list[WorkflowNodeMetrics]] = defaultdict(list)

        # Performance thresholds for alerting (in milliseconds)
        self.slow_workflow_threshold = 30000  # 30 seconds
        self.slow_node_threshold = 5000  # 5 seconds

        self.logger.info("WorkflowObservabilityService initialized")

    def start_workflow_tracking(
        self,
        workflow_id: str,
        workflow_type: str,
        user_id: str | None = None,
        session_id: str | None = None,
        input_parameters: dict[str, Any] | None = None,
    ) -> WorkflowExecution:
        """
        Start tracking a new workflow execution.

        Args:
            workflow_id: Unique identifier for the workflow execution
            workflow_type: Type of workflow (e.g., "document_qa", "agent_chat")
            user_id: User identifier
            session_id: Session identifier
            input_parameters: Input parameters for the workflow

        Returns:
            WorkflowExecution object for tracking
        """
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            user_id=user_id,
            session_id=session_id,
            start_time=datetime.now(timezone.utc),
            input_parameters=input_parameters or {},
        )

        self.active_workflows[workflow_id] = execution

        self.logger.info(
            f"Started tracking workflow: {workflow_id} (type: {workflow_type}, user: {user_id})"
        )

        return execution

    def start_node_execution(
        self,
        workflow_id: str,
        node_name: str,
        input_data: Any | None = None,
    ) -> str:
        """
        Start tracking a node execution within a workflow.

        Args:
            workflow_id: Workflow identifier
            node_name: Name of the node being executed
            input_data: Input data for the node

        Returns:
            Execution ID for the node
        """
        execution_id = str(uuid.uuid4())

        node_metrics = WorkflowNodeMetrics(
            node_name=node_name,
            execution_id=execution_id,
            start_time=datetime.now(timezone.utc),
            input_data_size=len(str(input_data)) if input_data else 0,
        )

        # Add to workflow tracking
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id].node_executions.append(node_metrics)

        # Add to node-specific tracking
        self.node_metrics[node_name].append(node_metrics)

        self.logger.debug(
            f"Started node execution: {node_name} "
            f"(workflow: {workflow_id}, execution: {execution_id})"
        )

        return execution_id

    def complete_node_execution(
        self,
        workflow_id: str,
        execution_id: str,
        output_data: Any | None = None,
        error: Exception | None = None,
    ) -> None:
        """
        Complete tracking for a node execution.

        Args:
            workflow_id: Workflow identifier
            execution_id: Node execution identifier
            output_data: Output data from the node
            error: Exception if the node failed
        """
        end_time = datetime.now(timezone.utc)

        # Find and update the node metrics
        node_metrics = None
        if workflow_id in self.active_workflows:
            for node in self.active_workflows[workflow_id].node_executions:
                if node.execution_id == execution_id:
                    node_metrics = node
                    break

        if node_metrics:
            node_metrics.end_time = end_time
            node_metrics.duration_ms = (end_time - node_metrics.start_time).total_seconds() * 1000

            if error:
                node_metrics.status = "failed"
                node_metrics.error_message = str(error)
                self.active_workflows[workflow_id].failed_nodes += 1

                self.logger.warning(
                    f"Node execution failed: {node_metrics.node_name} "
                    f"(duration: {node_metrics.duration_ms:.1f}ms, error: {error})"
                )
            else:
                node_metrics.status = "completed"
                node_metrics.output_data_size = len(str(output_data)) if output_data else 0
                self.active_workflows[workflow_id].successful_nodes += 1

                self.logger.debug(
                    f"Node execution completed: {node_metrics.node_name} "
                    f"(duration: {node_metrics.duration_ms:.1f}ms)"
                )

            # Check for slow node performance
            if node_metrics.duration_ms and node_metrics.duration_ms > self.slow_node_threshold:
                self.logger.warning(
                    f"Slow node execution detected: {node_metrics.node_name} "
                    f"took {node_metrics.duration_ms:.1f}ms "
                    f"(threshold: {self.slow_node_threshold}ms)"
                )

            self.active_workflows[workflow_id].total_nodes_executed += 1

    def complete_workflow(
        self,
        workflow_id: str,
        final_output: str | None = None,
        error: Exception | None = None,
    ) -> WorkflowExecution | None:
        """
        Complete tracking for a workflow execution.

        Args:
            workflow_id: Workflow identifier
            final_output: Final output from the workflow
            error: Exception if the workflow failed

        Returns:
            Completed WorkflowExecution object
        """
        if workflow_id not in self.active_workflows:
            self.logger.warning(f"Attempted to complete unknown workflow: {workflow_id}")
            return None

        execution = self.active_workflows[workflow_id]
        execution.end_time = datetime.now(timezone.utc)
        execution.total_duration_ms = (
            execution.end_time - execution.start_time
        ).total_seconds() * 1000

        if error:
            execution.status = "failed"
            execution.error_summary = str(error)

            self.logger.error(
                f"Workflow execution failed: {workflow_id} "
                f"(type: {execution.workflow_type}, "
                f"duration: {execution.total_duration_ms:.1f}ms, error: {error})"
            )
        else:
            execution.status = "completed"
            execution.final_output = final_output

            self.logger.info(
                f"Workflow execution completed: {workflow_id} "
                f"(type: {execution.workflow_type}, "
                f"duration: {execution.total_duration_ms:.1f}ms, "
                f"nodes: {execution.total_nodes_executed})"
            )

        # Check for slow workflow performance
        if execution.total_duration_ms > self.slow_workflow_threshold:
            self.logger.warning(
                f"Slow workflow execution detected: {workflow_id} "
                f"took {execution.total_duration_ms:.1f}ms "
                f"(threshold: {self.slow_workflow_threshold}ms)"
            )

        # Move to completed workflows
        self.completed_workflows[workflow_id] = execution
        del self.active_workflows[workflow_id]

        return execution

    def record_retry_attempt(self, workflow_id: str, node_name: str, retry_count: int) -> None:
        """
        Record a retry attempt for a node.

        Args:
            workflow_id: Workflow identifier
            node_name: Name of the node being retried
            retry_count: Current retry count
        """
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id].retry_attempts += 1

        self.logger.info(
            f"Retry attempt {retry_count} for node {node_name} in workflow {workflow_id}"
        )

    def get_workflow_status(self, workflow_id: str) -> dict[str, Any] | None:
        """
        Get current status of a workflow execution.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Dictionary containing workflow status information
        """
        # Check active workflows first
        if workflow_id in self.active_workflows:
            execution = self.active_workflows[workflow_id]
            current_time = datetime.now(timezone.utc)
            elapsed_ms = (current_time - execution.start_time).total_seconds() * 1000

            return {
                "workflow_id": workflow_id,
                "status": execution.status,
                "elapsed_time_ms": elapsed_ms,
                "nodes_executed": execution.total_nodes_executed,
                "successful_nodes": execution.successful_nodes,
                "failed_nodes": execution.failed_nodes,
                "retry_attempts": execution.retry_attempts,
                "is_active": True,
            }

        # Check completed workflows
        if workflow_id in self.completed_workflows:
            execution = self.completed_workflows[workflow_id]
            return {
                "workflow_id": workflow_id,
                "status": execution.status,
                "total_duration_ms": execution.total_duration_ms,
                "nodes_executed": execution.total_nodes_executed,
                "successful_nodes": execution.successful_nodes,
                "failed_nodes": execution.failed_nodes,
                "retry_attempts": execution.retry_attempts,
                "is_active": False,
            }

        return None

    def get_workflow_analytics(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        workflow_type: str | None = None,
    ) -> WorkflowAnalytics:
        """
        Generate analytics for workflow executions within a time period.

        Args:
            start_time: Start of time period (default: last 24 hours)
            end_time: End of time period (default: now)
            workflow_type: Filter by workflow type

        Returns:
            WorkflowAnalytics object with aggregated metrics
        """
        if not end_time:
            end_time = datetime.now(timezone.utc)
        if not start_time:
            start_time = end_time.replace(hour=end_time.hour - 24)

        # Filter workflows within time period
        relevant_workflows = [
            execution
            for execution in self.completed_workflows.values()
            if (
                execution.end_time
                and start_time <= execution.end_time <= end_time
                and (not workflow_type or execution.workflow_type == workflow_type)
            )
        ]

        analytics = WorkflowAnalytics(
            time_period_start=start_time,
            time_period_end=end_time,
            total_executions=len(relevant_workflows),
        )

        if relevant_workflows:
            # Calculate success/failure rates
            analytics.successful_executions = len(
                [w for w in relevant_workflows if w.status == "completed"]
            )
            analytics.failed_executions = len(
                [w for w in relevant_workflows if w.status == "failed"]
            )

            # Calculate duration statistics
            durations = [w.total_duration_ms for w in relevant_workflows if w.total_duration_ms]
            if durations:
                analytics.average_duration_ms = sum(durations) / len(durations)
                sorted_durations = sorted(durations)
                analytics.median_duration_ms = sorted_durations[len(sorted_durations) // 2]
                analytics.p95_duration_ms = sorted_durations[int(len(sorted_durations) * 0.95)]

            # Calculate node performance
            node_performance = defaultdict(list)
            for workflow in relevant_workflows:
                for node in workflow.node_executions:
                    if node.duration_ms:
                        node_performance[node.node_name].append(node.duration_ms)

            for node_name, durations in node_performance.items():
                analytics.node_performance[node_name] = {
                    "average_duration_ms": sum(durations) / len(durations),
                    "execution_count": len(durations),
                    "success_rate": len([d for d in durations if d > 0]) / len(durations),
                }

            # Calculate common error types
            error_types = defaultdict(int)
            for workflow in relevant_workflows:
                if workflow.error_summary:
                    # Categorize errors by first word or type
                    error_type = (
                        workflow.error_summary.split(":")[0]
                        if ":" in workflow.error_summary
                        else "Unknown"
                    )
                    error_types[error_type] += 1
            analytics.common_error_types = dict(error_types)

            # Calculate user activity
            user_activity = defaultdict(int)
            for workflow in relevant_workflows:
                if workflow.user_id:
                    user_activity[workflow.user_id] += 1
            analytics.user_activity = dict(user_activity)

        return analytics

    def get_debug_info(self, workflow_id: str) -> dict[str, Any] | None:
        """
        Get detailed debug information for a workflow execution.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Dictionary containing detailed debug information
        """
        # Check both active and completed workflows
        execution = self.active_workflows.get(workflow_id) or self.completed_workflows.get(
            workflow_id
        )

        if not execution:
            return None

        return {
            "workflow_execution": execution.dict(),
            "node_details": [node.dict() for node in execution.node_executions],
            "performance_summary": {
                "total_duration_ms": execution.total_duration_ms,
                "average_node_duration_ms": (
                    sum(node.duration_ms for node in execution.node_executions if node.duration_ms)
                    / len([node for node in execution.node_executions if node.duration_ms])
                    if execution.node_executions
                    else 0
                ),
                "slowest_node": (
                    max(execution.node_executions, key=lambda n: n.duration_ms or 0).node_name
                    if execution.node_executions
                    else None
                ),
            },
        }

    def cleanup_old_data(self, retention_days: int = 7) -> int:
        """
        Clean up old workflow data beyond retention period.

        Args:
            retention_days: Number of days to retain data

        Returns:
            Number of workflows cleaned up
        """
        cutoff_time = datetime.now(timezone.utc).replace(day=datetime.now().day - retention_days)

        workflows_to_remove = [
            workflow_id
            for workflow_id, execution in self.completed_workflows.items()
            if execution.end_time and execution.end_time < cutoff_time
        ]

        for workflow_id in workflows_to_remove:
            del self.completed_workflows[workflow_id]

        # Also cleanup node metrics
        for node_name in list(self.node_metrics.keys()):
            self.node_metrics[node_name] = [
                metric
                for metric in self.node_metrics[node_name]
                if metric.end_time and metric.end_time >= cutoff_time
            ]
            if not self.node_metrics[node_name]:
                del self.node_metrics[node_name]

        self.logger.info(f"Cleaned up {len(workflows_to_remove)} old workflow executions")
        return len(workflows_to_remove)


# Global service instance
_workflow_observability_service: WorkflowObservabilityService | None = None


def get_workflow_observability_service() -> WorkflowObservabilityService:
    """Get the global workflow observability service instance."""
    global _workflow_observability_service
    if _workflow_observability_service is None:
        _workflow_observability_service = WorkflowObservabilityService()
    return _workflow_observability_service
