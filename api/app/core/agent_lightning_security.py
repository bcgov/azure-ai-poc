"""Security utilities for Agent Lightning.

This module provides security controls for Agent Lightning operations:
- Input validation and sanitization
- Rate limiting
- Audit logging
- Cost limits per tenant
"""

import re
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SecurityViolation:
    """Security violation details."""

    violation_type: str
    tenant_id: str
    details: str
    timestamp: float


class InputValidator:
    """Validates and sanitizes Agent Lightning inputs."""

    # Agent name must be alphanumeric, hyphens, underscores (3-50 chars)
    AGENT_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,50}$")

    # Tenant ID must be alphanumeric, hyphens (3-100 chars)
    TENANT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9-]{3,100}$")

    @staticmethod
    def validate_agent_name(agent_name: str) -> str:
        """Validate and sanitize agent name.

        Args:
            agent_name: Agent name to validate

        Returns:
            Sanitized agent name

        Raises:
            ValueError: If agent name is invalid
        """
        if not agent_name:
            raise ValueError("Agent name cannot be empty")

        if not isinstance(agent_name, str):
            raise ValueError(f"Agent name must be string, got {type(agent_name)}")

        # Remove leading/trailing whitespace
        agent_name = agent_name.strip()

        if not InputValidator.AGENT_NAME_PATTERN.match(agent_name):
            raise ValueError(
                f"Invalid agent name: {agent_name}. "
                "Must be 3-50 characters, alphanumeric with hyphens/underscores only"
            )

        return agent_name

    @staticmethod
    def validate_tenant_id(tenant_id: str) -> str:
        """Validate and sanitize tenant ID.

        Args:
            tenant_id: Tenant ID to validate

        Returns:
            Sanitized tenant ID

        Raises:
            ValueError: If tenant ID is invalid
        """
        if not tenant_id:
            raise ValueError("Tenant ID cannot be empty")

        if not isinstance(tenant_id, str):
            raise ValueError(f"Tenant ID must be string, got {type(tenant_id)}")

        # Remove leading/trailing whitespace
        tenant_id = tenant_id.strip()

        if not InputValidator.TENANT_ID_PATTERN.match(tenant_id):
            raise ValueError(
                f"Invalid tenant ID: {tenant_id}. "
                "Must be 3-100 characters, alphanumeric with hyphens only"
            )

        return tenant_id

    @staticmethod
    def validate_metrics_count(count: int) -> int:
        """Validate metrics count.

        Args:
            count: Number of metrics

        Returns:
            Validated count

        Raises:
            ValueError: If count is invalid
        """
        if not isinstance(count, int):
            raise ValueError(f"Metrics count must be integer, got {type(count)}")

        if count < 0:
            raise ValueError("Metrics count cannot be negative")

        if count > 10000:
            raise ValueError("Metrics count cannot exceed 10000 per request")

        return count

    @staticmethod
    def validate_cost_limit(cost_usd: float) -> float:
        """Validate cost limit.

        Args:
            cost_usd: Cost in USD

        Returns:
            Validated cost

        Raises:
            ValueError: If cost is invalid
        """
        if not isinstance(cost_usd, (int, float)):
            raise ValueError(f"Cost must be numeric, got {type(cost_usd)}")

        if cost_usd < 0:
            raise ValueError("Cost cannot be negative")

        if cost_usd > 100000:
            raise ValueError("Cost cannot exceed $100,000 per request")

        return float(cost_usd)


class RateLimiter:
    """Rate limiter for Agent Lightning operations.

    Implements sliding window rate limiting per tenant.
    """

    def __init__(
        self,
        max_requests_per_minute: int = 60,
        max_optimization_requests_per_hour: int = 10,
    ) -> None:
        """Initialize rate limiter.

        Args:
            max_requests_per_minute: Max requests per minute per tenant
            max_optimization_requests_per_hour: Max optimization requests per hour
        """
        self._max_requests_per_minute = max_requests_per_minute
        self._max_optimization_requests_per_hour = max_optimization_requests_per_hour

        # Track request timestamps per tenant
        self._request_timestamps: dict[str, list[float]] = defaultdict(list)
        self._optimization_timestamps: dict[str, list[float]] = defaultdict(list)

    def check_rate_limit(self, tenant_id: str) -> bool:
        """Check if tenant is within rate limit.

        Args:
            tenant_id: Tenant ID

        Returns:
            True if within limit, False if rate limited

        Raises:
            ValueError: If rate limit exceeded
        """
        current_time = time.time()

        # Clean old timestamps (older than 1 minute)
        minute_ago = current_time - 60
        self._request_timestamps[tenant_id] = [
            ts for ts in self._request_timestamps[tenant_id] if ts > minute_ago
        ]

        # Check rate limit
        if len(self._request_timestamps[tenant_id]) >= self._max_requests_per_minute:
            logger.warning(
                f"Rate limit exceeded for tenant {tenant_id}",
                extra={
                    "tenant_id": tenant_id,
                    "requests_in_window": len(self._request_timestamps[tenant_id]),
                    "limit": self._max_requests_per_minute,
                },
            )
            raise ValueError(
                f"Rate limit exceeded: {self._max_requests_per_minute} requests per minute"
            )

        # Record request
        self._request_timestamps[tenant_id].append(current_time)
        return True

    def check_optimization_rate_limit(self, tenant_id: str) -> bool:
        """Check if tenant is within optimization rate limit.

        Args:
            tenant_id: Tenant ID

        Returns:
            True if within limit, False if rate limited

        Raises:
            ValueError: If rate limit exceeded
        """
        current_time = time.time()

        # Clean old timestamps (older than 1 hour)
        hour_ago = current_time - 3600
        self._optimization_timestamps[tenant_id] = [
            ts for ts in self._optimization_timestamps[tenant_id] if ts > hour_ago
        ]

        # Check rate limit
        request_count = len(self._optimization_timestamps[tenant_id])
        if request_count >= self._max_optimization_requests_per_hour:
            logger.warning(
                f"Optimization rate limit exceeded for tenant {tenant_id}",
                extra={
                    "tenant_id": tenant_id,
                    "optimizations_in_window": request_count,
                    "limit": self._max_optimization_requests_per_hour,
                },
            )
            raise ValueError(
                f"Optimization rate limit exceeded: "
                f"{self._max_optimization_requests_per_hour} optimizations per hour"
            )

        # Record optimization request
        self._optimization_timestamps[tenant_id].append(current_time)
        return True


class AuditLogger:
    """Audit logger for Agent Lightning operations.

    Logs security-relevant events for compliance and monitoring.
    """

    @staticmethod
    def log_optimization_decision(
        tenant_id: str,
        agent_name: str,
        decision: dict[str, Any],
        user_id: str | None = None,
    ) -> None:
        """Log optimization decision.

        Args:
            tenant_id: Tenant ID
            agent_name: Agent name
            decision: Optimization decision details
            user_id: Optional user ID who triggered optimization
        """
        logger.info(
            "agent_lightning_optimization_decision",
            extra={
                "event_type": "optimization_decision",
                "tenant_id": tenant_id,
                "agent_name": agent_name,
                "decision": decision,
                "user_id": user_id,
                "timestamp": time.time(),
            },
        )

    @staticmethod
    def log_security_violation(violation: SecurityViolation) -> None:
        """Log security violation.

        Args:
            violation: Security violation details
        """
        logger.warning(
            f"agent_lightning_security_violation: {violation.violation_type}",
            extra={
                "event_type": "security_violation",
                "violation_type": violation.violation_type,
                "tenant_id": violation.tenant_id,
                "details": violation.details,
                "timestamp": violation.timestamp,
            },
        )

    @staticmethod
    def log_cost_limit_exceeded(
        tenant_id: str, agent_name: str, cost_usd: float, limit_usd: float
    ) -> None:
        """Log cost limit exceeded event.

        Args:
            tenant_id: Tenant ID
            agent_name: Agent name
            cost_usd: Actual cost
            limit_usd: Cost limit
        """
        logger.warning(
            "agent_lightning_cost_limit_exceeded",
            extra={
                "event_type": "cost_limit_exceeded",
                "tenant_id": tenant_id,
                "agent_name": agent_name,
                "cost_usd": cost_usd,
                "limit_usd": limit_usd,
                "timestamp": time.time(),
            },
        )

    @staticmethod
    def log_metrics_collection(tenant_id: str, agent_name: str, metrics_count: int) -> None:
        """Log metrics collection event.

        Args:
            tenant_id: Tenant ID
            agent_name: Agent name
            metrics_count: Number of metrics collected
        """
        logger.debug(
            "agent_lightning_metrics_collection",
            extra={
                "event_type": "metrics_collection",
                "tenant_id": tenant_id,
                "agent_name": agent_name,
                "metrics_count": metrics_count,
                "timestamp": time.time(),
            },
        )


class CostLimiter:
    """Enforces cost limits per tenant.

    Tracks cumulative costs and prevents exceeding limits.
    """

    def __init__(self, default_monthly_limit_usd: float = 1000.0) -> None:
        """Initialize cost limiter.

        Args:
            default_monthly_limit_usd: Default monthly cost limit per tenant
        """
        self._default_monthly_limit = default_monthly_limit_usd
        self._tenant_costs: dict[str, float] = defaultdict(float)
        self._tenant_limits: dict[str, float] = {}

    def set_tenant_limit(self, tenant_id: str, limit_usd: float) -> None:
        """Set custom cost limit for tenant.

        Args:
            tenant_id: Tenant ID
            limit_usd: Cost limit in USD
        """
        InputValidator.validate_tenant_id(tenant_id)
        InputValidator.validate_cost_limit(limit_usd)
        self._tenant_limits[tenant_id] = limit_usd

    def get_tenant_limit(self, tenant_id: str) -> float:
        """Get cost limit for tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            Cost limit in USD
        """
        return self._tenant_limits.get(tenant_id, self._default_monthly_limit)

    def record_cost(self, tenant_id: str, cost_usd: float, agent_name: str) -> None:
        """Record cost for tenant.

        Args:
            tenant_id: Tenant ID
            cost_usd: Cost in USD
            agent_name: Agent name

        Raises:
            ValueError: If cost limit would be exceeded
        """
        InputValidator.validate_tenant_id(tenant_id)
        InputValidator.validate_cost_limit(cost_usd)

        limit = self.get_tenant_limit(tenant_id)
        current_cost = self._tenant_costs[tenant_id]
        new_total = current_cost + cost_usd

        if new_total > limit:
            AuditLogger.log_cost_limit_exceeded(tenant_id, agent_name, new_total, limit)
            raise ValueError(f"Cost limit exceeded: ${new_total:.2f} exceeds limit of ${limit:.2f}")

        self._tenant_costs[tenant_id] = new_total

    def get_tenant_cost(self, tenant_id: str) -> float:
        """Get current cost for tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            Current cost in USD
        """
        return self._tenant_costs.get(tenant_id, 0.0)

    def reset_tenant_cost(self, tenant_id: str) -> None:
        """Reset cost tracking for tenant (e.g., monthly reset).

        Args:
            tenant_id: Tenant ID
        """
        self._tenant_costs[tenant_id] = 0.0


# Global instances
_rate_limiter = RateLimiter()
_cost_limiter = CostLimiter()


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance.

    Returns:
        Global rate limiter
    """
    return _rate_limiter


def get_cost_limiter() -> CostLimiter:
    """Get global cost limiter instance.

    Returns:
        Global cost limiter
    """
    return _cost_limiter
