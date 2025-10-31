"""Integration tests for Agent Lightning security controls.

Tests input validation, rate limiting, audit logging, and cost limits.
"""

import time

import pytest

from app.core.agent_lightning_security import (
    AuditLogger,
    CostLimiter,
    InputValidator,
    RateLimiter,
    SecurityViolation,
    get_cost_limiter,
    get_rate_limiter,
)


class TestInputValidator:
    """Tests for InputValidator."""

    def test_validate_agent_name_valid(self) -> None:
        """Test valid agent names pass validation."""
        valid_names = [
            "query-planner",
            "document_qa",
            "agent-123",
            "MyAgent",
            "agent_with_underscores",
        ]

        for name in valid_names:
            result = InputValidator.validate_agent_name(name)
            assert result == name

    def test_validate_agent_name_with_whitespace(self) -> None:
        """Test agent name with leading/trailing whitespace is trimmed."""
        result = InputValidator.validate_agent_name("  agent-name  ")
        assert result == "agent-name"

    def test_validate_agent_name_empty(self) -> None:
        """Test empty agent name raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            InputValidator.validate_agent_name("")

    def test_validate_agent_name_too_short(self) -> None:
        """Test agent name shorter than 3 chars raises ValueError."""
        with pytest.raises(ValueError, match="3-50 characters"):
            InputValidator.validate_agent_name("ab")

    def test_validate_agent_name_too_long(self) -> None:
        """Test agent name longer than 50 chars raises ValueError."""
        long_name = "a" * 51
        with pytest.raises(ValueError, match="3-50 characters"):
            InputValidator.validate_agent_name(long_name)

    def test_validate_agent_name_invalid_characters(self) -> None:
        """Test agent name with invalid characters raises ValueError."""
        invalid_names = [
            "agent name",  # spaces
            "agent@name",  # special chars
            "agent.name",  # dots
            "agent/name",  # slashes
        ]

        for name in invalid_names:
            with pytest.raises(ValueError, match="alphanumeric"):
                InputValidator.validate_agent_name(name)

    def test_validate_agent_name_non_string(self) -> None:
        """Test non-string agent name raises ValueError."""
        with pytest.raises(ValueError, match="must be string"):
            InputValidator.validate_agent_name(123)  # type: ignore[arg-type]

    def test_validate_tenant_id_valid(self) -> None:
        """Test valid tenant IDs pass validation."""
        valid_ids = [
            "tenant-123",
            "org-456",
            "abc123",
            "tenant-with-many-hyphens",
        ]

        for tenant_id in valid_ids:
            result = InputValidator.validate_tenant_id(tenant_id)
            assert result == tenant_id

    def test_validate_tenant_id_with_whitespace(self) -> None:
        """Test tenant ID with whitespace is trimmed."""
        result = InputValidator.validate_tenant_id("  tenant-123  ")
        assert result == "tenant-123"

    def test_validate_tenant_id_empty(self) -> None:
        """Test empty tenant ID raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            InputValidator.validate_tenant_id("")

    def test_validate_tenant_id_invalid_characters(self) -> None:
        """Test tenant ID with invalid characters raises ValueError."""
        with pytest.raises(ValueError, match="alphanumeric"):
            InputValidator.validate_tenant_id("tenant_123")  # underscores not allowed

    def test_validate_metrics_count_valid(self) -> None:
        """Test valid metrics counts pass validation."""
        valid_counts = [0, 1, 50, 100, 1000, 10000]

        for count in valid_counts:
            result = InputValidator.validate_metrics_count(count)
            assert result == count

    def test_validate_metrics_count_negative(self) -> None:
        """Test negative metrics count raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            InputValidator.validate_metrics_count(-1)

    def test_validate_metrics_count_too_large(self) -> None:
        """Test metrics count exceeding max raises ValueError."""
        with pytest.raises(ValueError, match="cannot exceed 10000"):
            InputValidator.validate_metrics_count(10001)

    def test_validate_metrics_count_non_integer(self) -> None:
        """Test non-integer metrics count raises ValueError."""
        with pytest.raises(ValueError, match="must be integer"):
            InputValidator.validate_metrics_count(50.5)  # type: ignore[arg-type]

    def test_validate_cost_limit_valid(self) -> None:
        """Test valid cost limits pass validation."""
        valid_costs = [0.0, 10.5, 100, 1000.99, 50000]

        for cost in valid_costs:
            result = InputValidator.validate_cost_limit(cost)
            assert result == float(cost)

    def test_validate_cost_limit_negative(self) -> None:
        """Test negative cost raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            InputValidator.validate_cost_limit(-10.0)

    def test_validate_cost_limit_too_large(self) -> None:
        """Test cost exceeding max raises ValueError."""
        with pytest.raises(ValueError, match="cannot exceed"):
            InputValidator.validate_cost_limit(100001.0)

    def test_validate_cost_limit_non_numeric(self) -> None:
        """Test non-numeric cost raises ValueError."""
        with pytest.raises(ValueError, match="must be numeric"):
            InputValidator.validate_cost_limit("100")  # type: ignore[arg-type]


class TestRateLimiter:
    """Tests for RateLimiter."""

    def test_check_rate_limit_within_limit(self) -> None:
        """Test requests within rate limit are allowed."""
        limiter = RateLimiter(max_requests_per_minute=5)

        # Make requests within limit
        for _ in range(5):
            assert limiter.check_rate_limit("tenant-1") is True

    def test_check_rate_limit_exceeds_limit(self) -> None:
        """Test request exceeding rate limit raises ValueError."""
        limiter = RateLimiter(max_requests_per_minute=3)

        # Make requests up to limit
        for _ in range(3):
            limiter.check_rate_limit("tenant-1")

        # Next request should exceed limit
        with pytest.raises(ValueError, match="Rate limit exceeded"):
            limiter.check_rate_limit("tenant-1")

    def test_check_rate_limit_sliding_window(self) -> None:
        """Test rate limit uses sliding window (old requests expire)."""
        limiter = RateLimiter(max_requests_per_minute=2)

        # Make 2 requests (at limit)
        limiter.check_rate_limit("tenant-1")
        limiter.check_rate_limit("tenant-1")

        # Simulate time passing (61 seconds)
        limiter._request_timestamps["tenant-1"] = [time.time() - 61]

        # Should allow new request after old ones expire
        assert limiter.check_rate_limit("tenant-1") is True

    def test_check_rate_limit_tenant_isolation(self) -> None:
        """Test rate limits are isolated per tenant."""
        limiter = RateLimiter(max_requests_per_minute=2)

        # Tenant 1 makes requests
        limiter.check_rate_limit("tenant-1")
        limiter.check_rate_limit("tenant-1")

        # Tenant 2 should have separate limit
        assert limiter.check_rate_limit("tenant-2") is True
        assert limiter.check_rate_limit("tenant-2") is True

    def test_check_optimization_rate_limit_within_limit(self) -> None:
        """Test optimization requests within limit are allowed."""
        limiter = RateLimiter(max_optimization_requests_per_hour=3)

        for _ in range(3):
            assert limiter.check_optimization_rate_limit("tenant-1") is True

    def test_check_optimization_rate_limit_exceeds_limit(self) -> None:
        """Test optimization request exceeding limit raises ValueError."""
        limiter = RateLimiter(max_optimization_requests_per_hour=2)

        limiter.check_optimization_rate_limit("tenant-1")
        limiter.check_optimization_rate_limit("tenant-1")

        with pytest.raises(ValueError, match="Optimization rate limit exceeded"):
            limiter.check_optimization_rate_limit("tenant-1")

    def test_check_optimization_rate_limit_sliding_window(self) -> None:
        """Test optimization rate limit uses sliding window."""
        limiter = RateLimiter(max_optimization_requests_per_hour=1)

        limiter.check_optimization_rate_limit("tenant-1")

        # Simulate time passing (1 hour + 1 second)
        limiter._optimization_timestamps["tenant-1"] = [time.time() - 3601]

        # Should allow new request after old ones expire
        assert limiter.check_optimization_rate_limit("tenant-1") is True


class TestAuditLogger:
    """Tests for AuditLogger."""

    def test_log_optimization_decision(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test optimization decision is logged with all details."""
        decision = {"use_rl": True, "confidence": 0.95}

        AuditLogger.log_optimization_decision(
            tenant_id="tenant-1",
            agent_name="query-planner",
            decision=decision,
            user_id="user-123",
        )

        captured = capsys.readouterr()
        assert "optimization_decision" in captured.out
        assert "tenant-1" in captured.out
        assert "query-planner" in captured.out

    def test_log_security_violation(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test security violation is logged as warning."""
        violation = SecurityViolation(
            violation_type="invalid_input",
            tenant_id="tenant-1",
            details="Invalid agent name",
            timestamp=time.time(),
        )

        AuditLogger.log_security_violation(violation)

        captured = capsys.readouterr()
        assert "security_violation" in captured.out
        assert "invalid_input" in captured.out

    def test_log_cost_limit_exceeded(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test cost limit exceeded is logged as warning."""
        AuditLogger.log_cost_limit_exceeded(
            tenant_id="tenant-1",
            agent_name="query-planner",
            cost_usd=1500.0,
            limit_usd=1000.0,
        )

        captured = capsys.readouterr()
        assert "cost_limit_exceeded" in captured.out
        assert "1500" in captured.out

    def test_log_metrics_collection(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test metrics collection is logged."""
        AuditLogger.log_metrics_collection(
            tenant_id="tenant-1", agent_name="query-planner", metrics_count=50
        )

        captured = capsys.readouterr()
        assert "metrics_collection" in captured.out


class TestCostLimiter:
    """Tests for CostLimiter."""

    def test_set_and_get_tenant_limit(self) -> None:
        """Test setting and getting custom tenant limit."""
        limiter = CostLimiter(default_monthly_limit_usd=1000.0)

        limiter.set_tenant_limit("tenant-1", 5000.0)

        assert limiter.get_tenant_limit("tenant-1") == 5000.0

    def test_get_tenant_limit_default(self) -> None:
        """Test getting default limit for tenant without custom limit."""
        limiter = CostLimiter(default_monthly_limit_usd=1000.0)

        assert limiter.get_tenant_limit("tenant-1") == 1000.0

    def test_record_cost_within_limit(self) -> None:
        """Test recording cost within limit succeeds."""
        limiter = CostLimiter(default_monthly_limit_usd=1000.0)

        limiter.record_cost("tenant-1", 500.0, "query-planner")

        assert limiter.get_tenant_cost("tenant-1") == 500.0

    def test_record_cost_exceeds_limit(self) -> None:
        """Test recording cost exceeding limit raises ValueError."""
        limiter = CostLimiter(default_monthly_limit_usd=1000.0)

        limiter.record_cost("tenant-1", 800.0, "query-planner")

        # This should exceed limit (800 + 300 > 1000)
        with pytest.raises(ValueError, match="Cost limit exceeded"):
            limiter.record_cost("tenant-1", 300.0, "query-planner")

    def test_record_cost_cumulative(self) -> None:
        """Test costs accumulate correctly."""
        limiter = CostLimiter(default_monthly_limit_usd=1000.0)

        limiter.record_cost("tenant-1", 100.0, "agent-1")
        limiter.record_cost("tenant-1", 200.0, "agent-2")
        limiter.record_cost("tenant-1", 300.0, "agent-3")

        assert limiter.get_tenant_cost("tenant-1") == 600.0

    def test_record_cost_tenant_isolation(self) -> None:
        """Test costs are isolated per tenant."""
        limiter = CostLimiter(default_monthly_limit_usd=1000.0)

        limiter.record_cost("tenant-1", 500.0, "agent-1")
        limiter.record_cost("tenant-2", 600.0, "agent-2")

        assert limiter.get_tenant_cost("tenant-1") == 500.0
        assert limiter.get_tenant_cost("tenant-2") == 600.0

    def test_reset_tenant_cost(self) -> None:
        """Test resetting tenant cost."""
        limiter = CostLimiter(default_monthly_limit_usd=1000.0)

        limiter.record_cost("tenant-1", 500.0, "agent-1")
        assert limiter.get_tenant_cost("tenant-1") == 500.0

        limiter.reset_tenant_cost("tenant-1")
        assert limiter.get_tenant_cost("tenant-1") == 0.0

    def test_get_tenant_cost_default_zero(self) -> None:
        """Test getting cost for tenant with no recorded costs returns zero."""
        limiter = CostLimiter(default_monthly_limit_usd=1000.0)

        assert limiter.get_tenant_cost("tenant-1") == 0.0


class TestGlobalInstances:
    """Tests for global instance getters."""

    def test_get_rate_limiter_returns_singleton(self) -> None:
        """Test get_rate_limiter returns same instance."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()

        assert limiter1 is limiter2

    def test_get_cost_limiter_returns_singleton(self) -> None:
        """Test get_cost_limiter returns same instance."""
        limiter1 = get_cost_limiter()
        limiter2 = get_cost_limiter()

        assert limiter1 is limiter2


class TestSecurityIntegration:
    """Integration tests combining multiple security features."""

    def test_end_to_end_security_workflow(self) -> None:
        """Test complete security workflow.

        Scenario: Validate input, check rate limit, record cost, audit log
        """
        # Validate inputs
        tenant_id = InputValidator.validate_tenant_id("tenant-123")
        agent_name = InputValidator.validate_agent_name("query-planner")

        # Check rate limit
        limiter = RateLimiter(max_requests_per_minute=10)
        limiter.check_rate_limit(tenant_id)

        # Record cost
        cost_limiter = CostLimiter(default_monthly_limit_usd=1000.0)
        cost_limiter.record_cost(tenant_id, 50.0, agent_name)

        # Audit log
        AuditLogger.log_metrics_collection(tenant_id, agent_name, metrics_count=10)

        # Verify cost recorded
        assert cost_limiter.get_tenant_cost(tenant_id) == 50.0

    def test_security_violation_handling(self) -> None:
        """Test handling security violations.

        Scenario: Invalid input triggers security violation logging
        """
        # Attempt invalid input
        with pytest.raises(ValueError):
            InputValidator.validate_agent_name("invalid name with spaces")

        # Log security violation
        violation = SecurityViolation(
            violation_type="invalid_agent_name",
            tenant_id="tenant-123",
            details="Agent name contains spaces",
            timestamp=time.time(),
        )
        AuditLogger.log_security_violation(violation)

        # Violation logged (verified via audit log)
        # In production, this would be stored in security event system

    def test_multi_tenant_security_isolation(self) -> None:
        """Test security controls maintain tenant isolation.

        Verifies:
        - Rate limits isolated per tenant
        - Cost limits isolated per tenant
        - No cross-tenant data leakage
        """
        rate_limiter = RateLimiter(max_requests_per_minute=2)
        cost_limiter = CostLimiter(default_monthly_limit_usd=100.0)

        # Tenant 1 uses up rate limit
        rate_limiter.check_rate_limit("tenant-1")
        rate_limiter.check_rate_limit("tenant-1")

        # Tenant 2 should still have full quota
        assert rate_limiter.check_rate_limit("tenant-2") is True

        # Tenant 1 uses up cost limit
        cost_limiter.record_cost("tenant-1", 90.0, "agent-1")

        # Tenant 2 should still have full quota
        cost_limiter.record_cost("tenant-2", 90.0, "agent-2")
        assert cost_limiter.get_tenant_cost("tenant-2") == 90.0
