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


def _configure_test_issuers(monkeypatch):
    tenant_id = "11111111-1111-1111-1111-111111111111"
    entra_issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
    entra_aud = "22222222-2222-2222-2222-222222222222"
    entra_jwks_uri = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"

    keycloak_url = "https://dev.loginproxy.gov.bc.ca/auth"
    realm = "standard"
    keycloak_issuer = f"{keycloak_url}/realms/{realm}"
    keycloak_aud = "azure-poc-6086"
    keycloak_jwks_uri = f"{keycloak_issuer}/protocol/openid-connect/certs"

    monkeypatch.setattr(settings, "entra_tenant_id", tenant_id)
    monkeypatch.setattr(settings, "entra_client_id", entra_aud)
    monkeypatch.setattr(settings, "entra_issuer", entra_issuer)
    monkeypatch.setattr(settings, "entra_jwks_uri", entra_jwks_uri)

    monkeypatch.setattr(settings, "keycloak_url", keycloak_url)
    monkeypatch.setattr(settings, "keycloak_realm", realm)
    monkeypatch.setattr(settings, "keycloak_client_id", keycloak_aud)

    return {
        "entra_issuer": entra_issuer,
        "entra_aud": entra_aud,
        "entra_jwks_uri": entra_jwks_uri,
        "keycloak_issuer": keycloak_issuer,
        "keycloak_aud": keycloak_aud,
        "keycloak_jwks_uri": keycloak_jwks_uri,
    }


def _make_tokens(monkeypatch, cfg: dict) -> tuple[str, str]:
    entra_private, entra_jwks = _make_keypair_and_jwks(kid="entra-kid")
    keycloak_private, keycloak_jwks = _make_keypair_and_jwks(kid="kc-kid")

    url_to_jwks = {
        cfg["entra_jwks_uri"]: entra_jwks,
        cfg["keycloak_jwks_uri"]: keycloak_jwks,
    }
    monkeypatch.setattr(
        "app.auth.service.get_http_client",
        AsyncMock(return_value=_FakeHttpClient(url_to_jwks)),
    )

    entra_token = jose_jwt.encode(
        {
            "iss": cfg["entra_issuer"],
            "aud": cfg["entra_aud"],
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
            "iss": cfg["keycloak_issuer"],
            "aud": cfg["keycloak_aud"],
            "exp": int(time.time()) + 600,
            "iat": int(time.time()) - 10,
            "sub": "test-user-123",
            "client_roles": ["ai-poc-participant"],
        },
        keycloak_private,
        algorithm="RS256",
        headers={"kid": "kc-kid"},
    )

    return entra_token, keycloak_token


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "entra_enabled,keycloak_enabled,entra_ok,keycloak_ok",
    [
        (True, True, True, True),
        (False, True, False, True),
        (True, False, True, False),
        (False, False, False, False),
    ],
)
async def test_provider_feature_flags(monkeypatch, entra_enabled, keycloak_enabled, entra_ok, keycloak_ok):
    cfg = _configure_test_issuers(monkeypatch)
    entra_token, keycloak_token = _make_tokens(monkeypatch, cfg)

    monkeypatch.setattr(settings, "entra_enabled", entra_enabled)
    monkeypatch.setattr(settings, "keycloak_enabled", keycloak_enabled)

    service = JWTAuthService()

    if entra_ok:
        user = await service.validate_token(entra_token)
        assert user.provider == "entra"
    else:
        with pytest.raises(HTTPException) as excinfo:
            await service.validate_token(entra_token)
        assert excinfo.value.status_code == 401

    if keycloak_ok:
        user = await service.validate_token(keycloak_token)
        assert user.provider == "keycloak"
    else:
        with pytest.raises(HTTPException) as excinfo:
            await service.validate_token(keycloak_token)
        assert excinfo.value.status_code == 401
