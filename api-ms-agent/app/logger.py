"""Structured logging configuration using structlog."""

import inspect
import logging
import os
import socket

import structlog

from app.config import settings

# Cache hostname and PID at module load time (they don't change)
_HOSTNAME = socket.gethostname()
_PID = os.getpid()

# Performance setting: caller info adds ~5-10μs overhead per log call
# Only enable in debug mode or via explicit config
_ENABLE_CALLER_INFO = settings.debug


def _add_caller_info(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict,
) -> dict:
    """
    Add caller information (class, method, line number) to the log event.

    This is a performance-sensitive function that walks the call stack.
    Only enabled in debug mode to avoid production overhead.
    """
    # Skip caller info in production for performance
    if not _ENABLE_CALLER_INFO:
        return event_dict

    # Walk up the stack to find the actual caller (skip structlog internals)
    frame = inspect.currentframe()
    try:
        # Skip frames: _add_caller_info -> structlog internals -> actual caller
        # Typically need to go up 6-8 frames to get past structlog
        for _ in range(10):
            if frame is None:
                break
            frame = frame.f_back
            if frame is None:
                break

            # Skip structlog and logging internals
            module = frame.f_globals.get("__name__", "")
            if module.startswith(("structlog", "logging", "app.logger")):
                continue

            # Found the actual caller
            func_name = frame.f_code.co_name
            lineno = frame.f_lineno
            filename = os.path.basename(frame.f_code.co_filename)

            # Try to get class name if inside a method
            local_vars = frame.f_locals
            class_name = None
            if "self" in local_vars:
                class_name = type(local_vars["self"]).__name__
            elif "cls" in local_vars:
                class_name = local_vars["cls"].__name__

            # Build location string
            if class_name:
                event_dict["caller"] = f"{filename}:{class_name}.{func_name}:{lineno}"
            else:
                event_dict["caller"] = f"{filename}:{func_name}:{lineno}"
            break
    finally:
        del frame

    return event_dict


def _format_log_message(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict,
) -> str:
    """
    Format log messages to match Uvicorn access log style.

    Produces output like: INFO:     [hostname:pid] [file:Class.method:line] event_name key=value
    """
    level = event_dict.pop("level", "info").upper()
    event = event_dict.pop("event", "")
    caller = event_dict.pop("caller", "")

    # Format remaining context as key=value pairs
    context_parts = [f"{k}={v}" for k, v in event_dict.items()]
    context_str = " ".join(context_parts)

    # Build the log line
    prefix = f"{level}:     [{_HOSTNAME}:{_PID}]"
    if caller:
        prefix = f"{prefix} [{caller}]"

    if context_str:
        return f"{prefix} {event} {context_str}"
    return f"{prefix} {event}"


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

    # Disable Uvicorn's default access logs (we use our own middleware)
    # This must be done here before uvicorn fully initializes
    uvicorn_access = logging.getLogger("uvicorn.access")

    # Add a targeted filter to suppress noisy access lines for root and health endpoints
    class _UvicornAccessFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - trivial
            try:
                msg = record.getMessage()
            except Exception:
                return True
            # Suppress lines like: '127.0.0.1:xxxxx - "GET /health HTTP/1.1" 200 123B'
            if (
                '"GET / ' in msg
                or '"GET /"' in msg
                or "GET /health" in msg
                or "GET /favicon.ico" in msg
            ):
                return False
            return True

    uvicorn_access.addFilter(_UvicornAccessFilter())

    # Also attach filter to the broader uvicorn logger in case access lines are routed there
    logging.getLogger("uvicorn").addFilter(_UvicornAccessFilter())

    uvicorn_access.handlers = []
    uvicorn_access.propagate = False
    uvicorn_access.disabled = True

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            _add_caller_info,
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


def _outcome_from_status(status_code: int) -> str:
    if 200 <= status_code < 400:
        return "success"
    if 400 <= status_code < 500:
        return "client_error"
    return "server_error"


def log_request_performance(
    *,
    request_id: str,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    cache_delta: dict | None = None,
) -> None:
    """Emit a structured request performance log.

    Intentionally log-only: no response mutations.
    """

    logger = get_logger("app.performance")
    payload: dict[str, object] = {
        "request_id": request_id,
        "method": method,
        "path": path,
        "status": status_code,
        "outcome": _outcome_from_status(status_code),
        "duration_ms": round(duration_ms, 3),
    }
    if cache_delta:
        payload["cache_delta"] = cache_delta

    logger.info("request_perf", **payload)
