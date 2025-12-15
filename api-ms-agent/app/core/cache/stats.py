from __future__ import annotations

from copy import deepcopy
from threading import Lock

# Global, in-memory counters. This is intentionally simple and bounded in shape.
# Structure: {namespace: {event: count}}
_COUNTS: dict[str, dict[str, int]] = {}
_LOCK = Lock()


def increment(*, namespace: str, cache_event: str) -> None:
    """Increment a cache event counter."""
    with _LOCK:
        ns = _COUNTS.setdefault(namespace, {})
        ns[cache_event] = ns.get(cache_event, 0) + 1


def snapshot() -> dict[str, dict[str, int]]:
    """Return a deep copy snapshot of current counters."""
    with _LOCK:
        return deepcopy(_COUNTS)


def reset() -> None:
    """Reset all counters (test helper)."""
    with _LOCK:
        _COUNTS.clear()


def diff(
    before: dict[str, dict[str, int]],
    after: dict[str, dict[str, int]],
) -> dict[str, dict[str, int]]:
    """Compute a sparse diff (after - before) omitting zeros."""

    out: dict[str, dict[str, int]] = {}

    namespaces = set(before.keys()) | set(after.keys())
    for ns in sorted(namespaces):
        b = before.get(ns, {})
        a = after.get(ns, {})
        events = set(b.keys()) | set(a.keys())

        ns_delta: dict[str, int] = {}
        for ev in sorted(events):
            d = a.get(ev, 0) - b.get(ev, 0)
            if d:
                ns_delta[ev] = d

        if ns_delta:
            out[ns] = ns_delta

    return out
