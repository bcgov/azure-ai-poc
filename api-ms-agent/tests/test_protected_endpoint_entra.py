import json
import time
from unittest.mock import AsyncMock

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt as jose_jwt

from app.config import settings


def _use_fresh_auth_service(monkeypatch) -> None:
    """Force AuthMiddleware to use a freshly constructed JWTAuthService.

    The auth service is cached globally; tests that monkeypatch settings need a
    fresh instance so the patched values are read.
    """

    from app.auth.service import JWTAuthService

    monkeypatch.setattr(
        "app.middleware.auth_middleware.get_auth_service",
        lambda: JWTAuthService(),
    )


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _FakeHttpClient:
    def __init__(self, jwks: dict):
        self.jwks = jwks
        self.get_calls: list[str] = []

    async def get(self, url: str):
        self.get_calls.append(url)
        return _FakeResponse(self.jwks)


def _make_rsa_keys_and_jwks(*, kid: str) -> tuple[str, dict]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_key = private_key.public_key()
    jwk = json.loads(pyjwt.algorithms.RSAAlgorithm.to_jwk(public_key))
    jwk["kid"] = kid
    jwk["use"] = "sig"
    jwk["alg"] = "RS256"

    return private_pem, {"keys": [jwk]}


@pytest.mark.parametrize(
    "auth_header, expected_status, expected_code",
    [
        (None, 401, "auth.missing_authorization_header"),
        ("Bearer not-a-real-jwt", 401, "auth.invalid_format"),
    ],
)
def test_models_list_unauthorized_returns_structured_error(
    unauthenticated_client, auth_header: str | None, expected_status: int, expected_code: str
) -> None:
    headers = {}
    if auth_header is not None:
        headers["Authorization"] = auth_header

    resp = unauthenticated_client.get("/api/v1/models/", headers=headers)
    assert resp.status_code == expected_status

    payload = resp.json()
    assert payload["code"] == expected_code
    assert "detail" in payload
    assert "timestamp" in payload


def test_models_list_entra_token_role_enforced_returns_structured_403(
    unauthenticated_client, monkeypatch
) -> None:
    _use_fresh_auth_service(monkeypatch)

    tenant_id = "11111111-1111-1111-1111-111111111111"
    issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
    audience = "22222222-2222-2222-2222-222222222222"
    jwks_uri = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"

    monkeypatch.setattr(settings, "keycloak_enabled", False)
    monkeypatch.setattr(settings, "entra_enabled", True)
    monkeypatch.setattr(settings, "entra_tenant_id", tenant_id)
    monkeypatch.setattr(settings, "entra_client_id", audience)
    monkeypatch.setattr(settings, "entra_issuer", issuer)
    monkeypatch.setattr(settings, "entra_jwks_uri", jwks_uri)
    monkeypatch.setattr(settings, "jwks_cache_ttl_seconds", 86400)

    private_pem, jwks = _make_rsa_keys_and_jwks(kid="entra-kid")
    monkeypatch.setattr(
        "app.auth.service.get_http_client", AsyncMock(return_value=_FakeHttpClient(jwks))
    )

    base_claims = {
        "iss": issuer,
        "aud": audience,
        "exp": int(time.time()) + 600,
        "iat": int(time.time()) - 10,
        "oid": "550e8400-e29b-41d4-a716-446655440000",
        "sub": "pairwise-subject",
        "preferred_username": "user@example.com",
    }

    token_without_roles = jose_jwt.encode(
        {**base_claims, "roles": []}, private_pem, algorithm="RS256", headers={"kid": "entra-kid"}
    )

    resp = unauthenticated_client.get(
        "/api/v1/models/", headers={"Authorization": f"Bearer {token_without_roles}"}
    )
    assert resp.status_code == 403

    payload = resp.json()
    assert payload["code"] == "auth.missing_role"
    assert "timestamp" in payload


def test_models_list_entra_token_with_role_allows_access(
    unauthenticated_client, monkeypatch
) -> None:
    _use_fresh_auth_service(monkeypatch)

    tenant_id = "11111111-1111-1111-1111-111111111111"
    issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
    audience = "22222222-2222-2222-2222-222222222222"
    jwks_uri = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"

    monkeypatch.setattr(settings, "keycloak_enabled", False)
    monkeypatch.setattr(settings, "entra_enabled", True)
    monkeypatch.setattr(settings, "entra_tenant_id", tenant_id)
    monkeypatch.setattr(settings, "entra_client_id", audience)
    monkeypatch.setattr(settings, "entra_issuer", issuer)
    monkeypatch.setattr(settings, "entra_jwks_uri", jwks_uri)
    monkeypatch.setattr(settings, "jwks_cache_ttl_seconds", 86400)

    private_pem, jwks = _make_rsa_keys_and_jwks(kid="entra-kid")
    monkeypatch.setattr(
        "app.auth.service.get_http_client", AsyncMock(return_value=_FakeHttpClient(jwks))
    )

    claims = {
        "iss": issuer,
        "aud": audience,
        "exp": int(time.time()) + 600,
        "iat": int(time.time()) - 10,
        "oid": "550e8400-e29b-41d4-a716-446655440000",
        "sub": "pairwise-subject",
        "preferred_username": "user@example.com",
        "roles": ["ai-poc-participant"],
    }

    token = jose_jwt.encode(claims, private_pem, algorithm="RS256", headers={"kid": "entra-kid"})

    resp = unauthenticated_client.get(
        "/api/v1/models/", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200

    payload = resp.json()
    assert "models" in payload
