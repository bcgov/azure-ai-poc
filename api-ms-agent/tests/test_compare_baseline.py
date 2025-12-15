from scripts.compare_baseline import compare_runs, render_report


def test_compare_baseline_report_format_snapshot():
    baseline = {
        "base_url": "http://a",
        "repetitions": 1,
        "summary": {"steps": {"health": {"p50_ms": 10.0, "p95_ms": 20.0}}},
    }
    current = {
        "base_url": "http://a",
        "repetitions": 1,
        "summary": {"steps": {"health": {"p50_ms": 12.5, "p95_ms": 30.0}}},
    }

    comp = compare_runs(baseline, current)
    report = render_report(comp)

    assert report == (
        "Workload Comparison (ms)\n"
        "======================\n"
        "\n"
        "- health: p50 10.0 -> 12.5 (Δ 2.5), p95 20.0 -> 30.0 (Δ 10.0)\n"
    )
