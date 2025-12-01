"""Structured logging configuration using structlog."""

import logging

import structlog

from app.config import settings


def setup_logging() -> None:
    """
    Configure structlog for the application.

    Sets up structured logging with:
    - Context variable merging for request context
    - Log level filtering based on DEBUG setting
    - ISO timestamp formatting
    - Pretty console output in development
    """
    # Set log level based on debug setting
    # 0 = NOTSET (all), 10 = DEBUG, 20 = INFO
    log_level = logging.DEBUG if settings.debug else logging.INFO

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,  # Allow reconfiguration
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """
    Get a logger instance.

    Args:
        name: Optional logger name, typically __name__ of the module.

    Returns:
        A bound structlog logger instance.
    """
    return structlog.get_logger(name)
