from fastapi.testclient import TestClient


def test_auth_metrics_endpoint_is_public(unauthenticated_client: TestClient):
    resp = unauthenticated_client.get("/api/v1/auth/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert "auth_success_total" in resp.text
    assert "auth_failure_total" in resp.text
    assert "auth_role_denied_total" in resp.text
    assert "auth_validation_duration_ms" in resp.text
    assert "auth_authorization_duration_ms" in resp.text
