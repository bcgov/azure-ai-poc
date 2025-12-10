"""Structured logging configuration using structlog."""

import logging
import os
import socket

import structlog

from app.config import settings

# Cache hostname and PID at module load time (they don't change)
_HOSTNAME = socket.gethostname()
_PID = os.getpid()


def _format_log_message(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict,
) -> str:
    """
    Format log messages to match Uvicorn access log style.

    Produces output like: INFO:     [hostname:pid] event_name key=value key2=value2
    """
    level = event_dict.pop("level", "info").upper()
    event = event_dict.pop("event", "")

    # Format remaining context as key=value pairs
    context_parts = [f"{k}={v}" for k, v in event_dict.items()]
    context_str = " ".join(context_parts)

    if context_str:
        return f"{level}:     [{_HOSTNAME}:{_PID}] {event} {context_str}"
    return f"{level}:     [{_HOSTNAME}:{_PID}] {event}"


def setup_logging() -> None:
    """
    Configure structlog for the application.

    Sets up structured logging with:
    - Context variable merging for request context
    - Log level filtering based on DEBUG setting
    - Clean output matching Uvicorn access log style
    """
    # Set log level based on debug setting
    # 0 = NOTSET (all), 10 = DEBUG, 20 = INFO
    log_level = logging.DEBUG if settings.debug else logging.INFO

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            _format_log_message,
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
