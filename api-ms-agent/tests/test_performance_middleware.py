import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.middleware.performance_middleware import PerformanceMiddleware


def test_performance_middleware_logs_perf(monkeypatch: pytest.MonkeyPatch):
    calls = []

    def _fake_log_request_performance(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(
        "app.middleware.performance_middleware.log_request_performance",
        _fake_log_request_performance,
    )

    app = FastAPI()
    app.add_middleware(PerformanceMiddleware)

    @app.get("/ok")
    async def ok():
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/ok", headers={"x-request-id": "rid-1"})

    assert resp.status_code == 200
    assert len(calls) == 1

    payload = calls[0]
    assert payload["request_id"] == "rid-1"
    assert payload["method"] == "GET"
    assert payload["path"] == "/ok"
    assert payload["status_code"] == 200
    assert isinstance(payload["duration_ms"], float)
    assert isinstance(payload["cache_delta"], dict)


def test_performance_middleware_skips_health(monkeypatch: pytest.MonkeyPatch):
    calls = []

    def _fake_log_request_performance(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(
        "app.middleware.performance_middleware.log_request_performance",
        _fake_log_request_performance,
    )

    app = FastAPI()
    app.add_middleware(PerformanceMiddleware)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    client = TestClient(app)
    resp = client.get("/health")

    assert resp.status_code == 200
    assert calls == []
