import json
import time
from unittest.mock import AsyncMock

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt as jose_jwt

from app.auth.service import JWTAuthService
from app.config import settings


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

    async def get(self, _url: str):
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


@pytest.mark.asyncio
async def test_validate_keycloak_token_roles_from_client_roles(monkeypatch):
    keycloak_url = "https://dev.loginproxy.gov.bc.ca/auth"
    realm = "standard"
    issuer = f"{keycloak_url}/realms/{realm}"
    audience = "azure-poc-6086"
    jwks_uri = f"{issuer}/protocol/openid-connect/certs"

    monkeypatch.setattr(settings, "keycloak_enabled", True)
    monkeypatch.setattr(settings, "keycloak_url", keycloak_url)
    monkeypatch.setattr(settings, "keycloak_realm", realm)
    monkeypatch.setattr(settings, "keycloak_client_id", audience)

    private_pem, jwks = _make_rsa_keys_and_jwks(kid="kc-kid")
    monkeypatch.setattr(
        "app.auth.service.get_http_client", AsyncMock(return_value=_FakeHttpClient(jwks))
    )

    claims = {
        "iss": issuer,
        "aud": audience,
        "exp": int(time.time()) + 600,
        "iat": int(time.time()) - 10,
        "sub": "test-user-123",
        "preferred_username": "testuser",
        "email": "test@example.com",
        "client_roles": ["ai-poc-participant"],
    }

    token = jose_jwt.encode(claims, private_pem, algorithm="RS256", headers={"kid": "kc-kid"})

    service = JWTAuthService()
    user = await service.validate_token(token)

    assert user.provider == "keycloak"
    assert user.sub == "test-user-123"
    assert "ai-poc-participant" in user.roles
    assert user.iss == issuer
    assert user.aud == audience
