"""Compatibility helpers for Agent Framework ChatAgent.run() calls.

Some versions of `agent-framework` accept optional keyword arguments like `user` and
`thread` on `ChatAgent.run()`, while others may not. Passing unsupported kwargs
would raise a runtime TypeError.

This module provides a small compatibility layer so we can:
- pass `user` for abuse tracking / per-user context when supported
- pass `thread` for continuity when supported
- gracefully fall back when the SDK signature does not accept these kwargs
"""

from __future__ import annotations

import inspect
from typing import Any

from app.logger import get_logger

logger = get_logger(__name__)


def _supports_kwarg(callable_obj: Any, kwarg: str) -> bool:
    """Return True if callable_obj supports kwarg by name or via **kwargs."""
    try:
        sig = inspect.signature(callable_obj)
    except (TypeError, ValueError):
        # Builtins/extension types or dynamic callables: assume it supports kwargs.
        return True

    params = sig.parameters.values()

    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params):
        return True

    return kwarg in sig.parameters


async def run_agent_compat(
    agent: Any,
    prompt: Any,
    *,
    user: str | None = None,
    thread: Any | None = None,
) -> Any:
    """Run an Agent Framework agent, only passing supported kwargs.

    Args:
        agent: An instance of agent_framework.ChatAgent (or compatible).
        prompt: Text prompt or ChatMessage (SDK type).
        user: Optional user identifier.
        thread: Optional thread object/identifier.

    Returns:
        Agent run result.
    """

    kwargs: dict[str, Any] = {}
    if user is not None and _supports_kwarg(agent.run, "user"):
        kwargs["user"] = user
    if thread is not None and _supports_kwarg(agent.run, "thread"):
        kwargs["thread"] = thread

    try:
        return await agent.run(prompt, **kwargs)
    except TypeError as exc:
        # If the SDK still rejects kwargs (e.g., dynamic signature mismatch), retry
        # without them rather than failing requests at runtime.
        msg = str(exc)
        if kwargs and ("unexpected keyword argument" in msg or "got an unexpected keyword" in msg):
            logger.warning(
                "agent_run_kwargs_not_supported",
                dropped_kwargs=sorted(kwargs.keys()),
                agent_type=type(agent).__name__,
                error=msg,
            )
            return await agent.run(prompt)
        raise
