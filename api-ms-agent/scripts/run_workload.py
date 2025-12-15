"""Run a repeatable workload against the API and write a JSON result.

Default behavior hits unauthenticated endpoints only. For auth-required routes,
pass `--bearer-token`.

Output JSON shape is stable to support comparisons.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


@dataclass(frozen=True, slots=True)
class WorkloadStep:
    name: str
    method: str
    path: str
    json_body: dict[str, Any] | None = None


def _default_steps() -> list[WorkloadStep]:
    return [
        WorkloadStep(name="health", method="GET", path="/health"),
        WorkloadStep(name="root", method="GET", path="/"),
    ]


async def _run_once(
    client: httpx.AsyncClient,
    step: WorkloadStep,
    *,
    headers: dict[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    start = time.perf_counter()
    status_code: int | None = None
    error: str | None = None

    try:
        resp = await client.request(
            step.method,
            step.path,
            headers=headers,
            json=step.json_body,
            timeout=timeout_seconds,
        )
        status_code = resp.status_code
        # Read body to include transfer time (but do not store the full content).
        _ = resp.text
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"

    duration_ms = (time.perf_counter() - start) * 1000.0

    return {
        "name": step.name,
        "method": step.method,
        "path": step.path,
        "status": status_code,
        "duration_ms": round(duration_ms, 3),
        "error": error,
    }


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values_sorted = sorted(values)
    k = int(round((p / 100.0) * (len(values_sorted) - 1)))
    return float(values_sorted[max(0, min(k, len(values_sorted) - 1))])


def _summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_step: dict[str, list[float]] = {}
    errors = 0

    for r in results:
        if r.get("error") is not None or r.get("status") is None:
            errors += 1
        by_step.setdefault(r["name"], []).append(float(r["duration_ms"]))

    summary_steps: dict[str, Any] = {}
    for name, durations in by_step.items():
        summary_steps[name] = {
            "count": len(durations),
            "p50_ms": round(_percentile(durations, 50), 3),
            "p95_ms": round(_percentile(durations, 95), 3),
            "max_ms": round(max(durations) if durations else 0.0, 3),
        }

    return {
        "total": len(results),
        "errors": errors,
        "steps": summary_steps,
    }


async def run_workload(
    *,
    base_url: str,
    repetitions: int,
    timeout_seconds: float,
    bearer_token: str | None,
) -> dict[str, Any]:
    headers: dict[str, str] = {
        "x-request-id": "workload",  # stable for log correlation
    }
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    steps = _default_steps()
    results: list[dict[str, Any]] = []

    async with httpx.AsyncClient(base_url=base_url) as client:
        for i in range(repetitions):
            for step in steps:
                r = await _run_once(
                    client,
                    step,
                    headers={**headers, "x-request-id": f"workload-{i}"},
                    timeout_seconds=timeout_seconds,
                )
                results.append(r)

    return {
        "version": 1,
        "base_url": base_url,
        "repetitions": repetitions,
        "timeout_seconds": timeout_seconds,
        "results": results,
        "summary": _summarize(results),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a repeatable API workload")
    parser.add_argument("--base-url", default="http://localhost:4000", help="API base URL")
    parser.add_argument("--repetitions", type=int, default=3, help="Number of repetitions")
    parser.add_argument("--timeout-seconds", type=float, default=10.0, help="Per-request timeout")
    parser.add_argument("--bearer-token", default=None, help="Optional JWT bearer token")
    parser.add_argument(
        "--out",
        default="workload.json",
        help="Output JSON file path",
    )

    args = parser.parse_args()

    out_path = Path(args.out)
    data = asyncio.run(
        run_workload(
            base_url=args.base_url,
            repetitions=args.repetitions,
            timeout_seconds=args.timeout_seconds,
            bearer_token=args.bearer_token,
        )
    )
    out_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    print(json.dumps(data["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
