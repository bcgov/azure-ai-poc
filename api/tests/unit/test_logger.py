"""Unit tests for logger module."""

import structlog

from app.core.logger import get_logger, setup_logging


class TestLogger:
    """Tests for logger module."""

    def test_setup_logging_configures_structlog(self):
        """Test that setup_logging configures structlog correctly."""
        # Just test that it doesn't raise an exception
        setup_logging()

        # Verify structlog is configured
        logger = structlog.get_logger("test")
        assert logger is not None

    def test_get_logger_returns_structlog_instance(self):
        """Test that get_logger returns a valid structlog logger."""
        logger = get_logger("test_logger")

        assert logger is not None
        # Test that it can log
        logger.info("test message")

    def test_get_logger_with_different_names(self):
        """Test that get_logger works with different logger names."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert logger1 is not None
        assert logger2 is not None

    def test_logger_can_log_with_context(self):
        """Test that logger can log with additional context."""
        logger = get_logger("test_context")

        # Should not raise any exceptions
        logger.info("test message", extra_field="value", count=42)

    def test_logger_bound_logger_type(self):
        """Test that logger is a BoundLogger instance."""
        logger = get_logger("test_bound")

        # Verify it has expected methods
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "warning")
