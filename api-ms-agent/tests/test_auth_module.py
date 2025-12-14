import pytest
from fastapi.testclient import TestClient

import app.main as main_app


@pytest.mark.asyncio
async def test_jwks_missing_key_refresh_path(monkeypatch):
    """When the requested kid is not present in JWKS, the service should attempt
    one refresh and then return 401 if still not found."""

    from fastapi import HTTPException

    from app.auth import service as auth_service_mod

    # Make get_unverified_header return a kid that won't be in JWKS
    monkeypatch.setattr(
        auth_service_mod.jwt,
        "get_unverified_header",
        lambda token: {"kid": "missing-kid"},
    )

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            # JWKS without the requested kid
            return {"keys": [{"kid": "other-key"}]}

    class DummyClient:
        async def get(self, url):
            return DummyResponse()

    async def dummy_get_http_client():
        return DummyClient()

    monkeypatch.setattr(auth_service_mod, "get_http_client", lambda: dummy_get_http_client())

    svc = auth_service_mod.AuthService()

    with pytest.raises(HTTPException) as excinfo:
        await svc.validate_token("fake-token")

    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_token_without_client_roles_returns_403(monkeypatch):
    """If jwt.decode returns a payload without client_roles, validate_token should raise 403."""

    from fastapi import HTTPException

    from app.auth import service as auth_service_mod

    # Ensure header parsing returns a kid
    monkeypatch.setattr(auth_service_mod.jwt, "get_unverified_header", lambda token: {"kid": "k1"})

    # Stub _get_signing_key to return a dummy public key
    async def fake_get_signing_key(self, kid, force_refresh=False):
        return "-----BEGIN PUBLIC KEY-----\nMIIBIjAN...\n-----END PUBLIC KEY-----"

    monkeypatch.setattr(auth_service_mod.AuthService, "_get_signing_key", fake_get_signing_key)

    # Stub jwt.decode to return a payload without client_roles
    def fake_decode(token, key, algorithms=None, audience=None, issuer=None, options=None):
        return {"sub": "user-1", "aud": audience, "iss": issuer}

    monkeypatch.setattr(auth_service_mod.jwt, "decode", fake_decode)

    svc = auth_service_mod.AuthService()

    with pytest.raises(HTTPException) as excinfo:
        await svc.validate_token("fake-token")

    assert excinfo.value.status_code == 403


def test_missing_authorization_header_returns_401():
    """Middleware should return 401 when Authorization header is missing."""

    app = main_app.app
    client = TestClient(app)

    # POST to chat endpoint (protected by middleware). Middleware should return 401
    resp = client.post("/api/v1/chat/", json={"message": "hi"})
    assert resp.status_code == 401
