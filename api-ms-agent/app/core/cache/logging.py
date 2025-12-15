from __future__ import annotations

import time

from app.logger import get_logger

logger = get_logger(__name__)


class CacheTimer:
    def __init__(self) -> None:
        self._start = time.perf_counter()

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000.0


def log_cache_event(
    *,
    namespace: str,
    cache_event: str,
    duration_ms: float | None = None,
    detail: str | None = None,
) -> None:
    # Never log keys or user content here.
    # NOTE: structlog uses `event` as the message positional arg.
    # Never pass `event=` as a kwarg to logger.* calls.
    payload: dict[str, object] = {"namespace": namespace, "cache_event": cache_event}
    if duration_ms is not None:
        payload["duration_ms"] = round(duration_ms, 3)
    if detail is not None:
        payload["detail"] = detail
    logger.info("cache", **payload)
