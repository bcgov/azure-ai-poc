"""Test the main application module."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_app_creation():
    """Test that the app can be created successfully."""
    app = create_app()
    assert app is not None
    assert app.title == "Azure AI POC API"


def test_health_endpoint():
    """Test the health endpoint is accessible."""
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_openapi_docs():
    """Test that OpenAPI docs are accessible."""
    app = create_app()
    client = TestClient(app)
    response = client.get("/docs")
    assert response.status_code == 200
