import json
import time
from unittest.mock import AsyncMock

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
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
    def __init__(self, url_to_jwks: dict[str, dict]):
        self.url_to_jwks = url_to_jwks

    async def get(self, url: str):
        return _FakeResponse(self.url_to_jwks[url])


def _make_keypair_and_jwks(*, kid: str) -> tuple[str, dict]:
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
async def test_coexistence_feature_flags(monkeypatch):
    tenant_id = "11111111-1111-1111-1111-111111111111"
    entra_issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
    entra_aud = "22222222-2222-2222-2222-222222222222"
    entra_jwks_uri = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"

    keycloak_url = "https://dev.loginproxy.gov.bc.ca/auth"
    realm = "standard"
    keycloak_issuer = f"{keycloak_url}/realms/{realm}"
    keycloak_aud = "azure-poc-6086"
    keycloak_jwks_uri = f"{keycloak_issuer}/protocol/openid-connect/certs"

    monkeypatch.setattr(settings, "entra_enabled", True)
    monkeypatch.setattr(settings, "entra_tenant_id", tenant_id)
    monkeypatch.setattr(settings, "entra_client_id", entra_aud)
    monkeypatch.setattr(settings, "entra_issuer", entra_issuer)
    monkeypatch.setattr(settings, "entra_jwks_uri", entra_jwks_uri)

    monkeypatch.setattr(settings, "keycloak_enabled", True)
    monkeypatch.setattr(settings, "keycloak_url", keycloak_url)
    monkeypatch.setattr(settings, "keycloak_realm", realm)
    monkeypatch.setattr(settings, "keycloak_client_id", keycloak_aud)

    entra_private, entra_jwks = _make_keypair_and_jwks(kid="entra-kid")
    keycloak_private, keycloak_jwks = _make_keypair_and_jwks(kid="kc-kid")

    url_to_jwks = {
        entra_jwks_uri: entra_jwks,
        keycloak_jwks_uri: keycloak_jwks,
    }
    monkeypatch.setattr(
        "app.auth.service.get_http_client",
        AsyncMock(return_value=_FakeHttpClient(url_to_jwks)),
    )

    entra_token = jose_jwt.encode(
        {
            "iss": entra_issuer,
            "aud": entra_aud,
            "exp": int(time.time()) + 600,
            "iat": int(time.time()) - 10,
            "oid": "550e8400-e29b-41d4-a716-446655440000",
            "roles": ["ai-poc-participant"],
        },
        entra_private,
        algorithm="RS256",
        headers={"kid": "entra-kid"},
    )

    keycloak_token = jose_jwt.encode(
        {
            "iss": keycloak_issuer,
            "aud": keycloak_aud,
            "exp": int(time.time()) + 600,
            "iat": int(time.time()) - 10,
            "sub": "test-user-123",
            "client_roles": ["ai-poc-participant"],
        },
        keycloak_private,
        algorithm="RS256",
        headers={"kid": "kc-kid"},
    )

    service = JWTAuthService()

    user1 = await service.validate_token(entra_token)
    assert user1.provider == "entra"

    user2 = await service.validate_token(keycloak_token)
    assert user2.provider == "keycloak"

    # Disable Entra and ensure Entra token rejected
    monkeypatch.setattr(settings, "entra_enabled", False)
    service_disabled_entra = JWTAuthService()

    with pytest.raises(HTTPException) as excinfo:
        await service_disabled_entra.validate_token(entra_token)
    assert excinfo.value.status_code == 401

    # Disable Keycloak and ensure Keycloak token rejected
    monkeypatch.setattr(settings, "entra_enabled", True)
    monkeypatch.setattr(settings, "keycloak_enabled", False)
    service_disabled_keycloak = JWTAuthService()

    with pytest.raises(HTTPException) as excinfo2:
        await service_disabled_keycloak.validate_token(keycloak_token)
    assert excinfo2.value.status_code == 401
