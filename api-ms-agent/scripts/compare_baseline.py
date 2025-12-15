"""Compare two workload JSON outputs and print a stable report.

This is intentionally simple and deterministic to support CI gating later.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compare_runs(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    b_steps = baseline.get("summary", {}).get("steps", {})
    c_steps = current.get("summary", {}).get("steps", {})

    step_names = sorted(set(b_steps.keys()) | set(c_steps.keys()))

    steps_out: dict[str, Any] = {}
    for name in step_names:
        b = b_steps.get(name)
        c = c_steps.get(name)
        if not b or not c:
            steps_out[name] = {"status": "missing"}
            continue

        steps_out[name] = {
            "baseline": {"p50_ms": b.get("p50_ms"), "p95_ms": b.get("p95_ms")},
            "current": {"p50_ms": c.get("p50_ms"), "p95_ms": c.get("p95_ms")},
            "delta": {
                "p50_ms": round(float(c.get("p50_ms", 0)) - float(b.get("p50_ms", 0)), 3),
                "p95_ms": round(float(c.get("p95_ms", 0)) - float(b.get("p95_ms", 0)), 3),
            },
        }

    return {
        "version": 1,
        "baseline": {
            "base_url": baseline.get("base_url"),
            "repetitions": baseline.get("repetitions"),
        },
        "current": {
            "base_url": current.get("base_url"),
            "repetitions": current.get("repetitions"),
        },
        "steps": steps_out,
    }


def render_report(comp: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("Workload Comparison (ms)")
    lines.append("======================")
    lines.append("")

    for step, data in comp.get("steps", {}).items():
        if data.get("status") == "missing":
            lines.append(f"- {step}: missing in one run")
            continue

        b50 = data["baseline"]["p50_ms"]
        c50 = data["current"]["p50_ms"]
        d50 = data["delta"]["p50_ms"]
        b95 = data["baseline"]["p95_ms"]
        c95 = data["current"]["p95_ms"]
        d95 = data["delta"]["p95_ms"]

        lines.append(f"- {step}: p50 {b50} -> {c50} (Δ {d50}), p95 {b95} -> {c95} (Δ {d95})")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare workload baselines")
    parser.add_argument("baseline", help="Path to baseline workload.json")
    parser.add_argument("current", help="Path to current workload.json")
    parser.add_argument("--out", default=None, help="Optional output path for report text")

    args = parser.parse_args()

    baseline = _load(Path(args.baseline))
    current = _load(Path(args.current))

    comp = compare_runs(baseline, current)
    report = render_report(comp)

    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")

    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
