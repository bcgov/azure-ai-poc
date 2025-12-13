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
    def __init__(self, jwks: dict):
        self.jwks = jwks
        self.get_calls: list[str] = []

    async def get(self, url: str):
        self.get_calls.append(url)
        return _FakeResponse(self.jwks)


class _RotatingJwksHttpClient:
    """Fake client that returns different JWKS payloads over time.

    Used to simulate key rotation / JWKS updates.
    """

    def __init__(self, jwks_sequence: list[dict]):
        self._jwks_sequence = jwks_sequence
        self.get_calls: list[str] = []

    async def get(self, url: str):
        self.get_calls.append(url)
        if len(self.get_calls) <= len(self._jwks_sequence):
            payload = self._jwks_sequence[len(self.get_calls) - 1]
        else:
            payload = self._jwks_sequence[-1]
        return _FakeResponse(payload)


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
async def test_validate_entra_token_and_jwks_cached(monkeypatch):
    tenant_id = "11111111-1111-1111-1111-111111111111"
    issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
    audience = "22222222-2222-2222-2222-222222222222"
    jwks_uri = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"

    monkeypatch.setattr(settings, "entra_enabled", True)
    monkeypatch.setattr(settings, "entra_tenant_id", tenant_id)
    monkeypatch.setattr(settings, "entra_client_id", audience)
    monkeypatch.setattr(settings, "entra_issuer", issuer)
    monkeypatch.setattr(settings, "entra_jwks_uri", jwks_uri)
    monkeypatch.setattr(settings, "jwks_cache_ttl_seconds", 86400)

    private_pem, jwks = _make_rsa_keys_and_jwks(kid="entra-kid")
    fake_client = _FakeHttpClient(jwks)

    monkeypatch.setattr("app.auth.service.get_http_client", AsyncMock(return_value=fake_client))

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

    service = JWTAuthService()

    user1 = await service.validate_token(token)
    assert user1.provider == "entra"
    assert user1.sub == claims["oid"]
    assert "ai-poc-participant" in user1.roles

    user2 = await service.validate_token(token)
    assert user2.provider == "entra"

    # JWKS fetched once due to TTL caching
    assert fake_client.get_calls.count(jwks_uri) == 1


@pytest.mark.asyncio
async def test_validate_entra_token_refetches_jwks_when_kid_missing(monkeypatch):
    """If a signing key isn't found in the cached JWKS, the service should refetch once.

    This simulates a key rotation where a new kid appears.
    """

    tenant_id = "11111111-1111-1111-1111-111111111111"
    issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
    audience = "22222222-2222-2222-2222-222222222222"
    jwks_uri = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"

    monkeypatch.setattr(settings, "entra_enabled", True)
    monkeypatch.setattr(settings, "entra_tenant_id", tenant_id)
    monkeypatch.setattr(settings, "entra_client_id", audience)
    monkeypatch.setattr(settings, "entra_issuer", issuer)
    monkeypatch.setattr(settings, "entra_jwks_uri", jwks_uri)
    monkeypatch.setattr(settings, "jwks_cache_ttl_seconds", 86400)

    # Token is signed with key B (kid=entra-kid-2), but the first JWKS response only has key A.
    _private_a, jwks_a = _make_rsa_keys_and_jwks(kid="entra-kid-1")
    private_b, jwks_b = _make_rsa_keys_and_jwks(kid="entra-kid-2")

    fake_client = _RotatingJwksHttpClient([jwks_a, jwks_b])
    monkeypatch.setattr("app.auth.service.get_http_client", AsyncMock(return_value=fake_client))

    claims = {
        "iss": issuer,
        "aud": audience,
        "exp": int(time.time()) + 600,
        "iat": int(time.time()) - 10,
        "oid": "550e8400-e29b-41d4-a716-446655440000",
        "roles": ["ai-poc-participant"],
    }

    token = jose_jwt.encode(claims, private_b, algorithm="RS256", headers={"kid": "entra-kid-2"})

    service = JWTAuthService()
    user = await service.validate_token(token)
    assert user.provider == "entra"
    assert "ai-poc-participant" in user.roles

    # JWKS fetched twice: once initially, once after kid not found.
    assert fake_client.get_calls.count(jwks_uri) == 2


@pytest.mark.asyncio
async def test_validate_entra_token_rejects_expired(monkeypatch):
    tenant_id = "11111111-1111-1111-1111-111111111111"
    issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
    audience = "22222222-2222-2222-2222-222222222222"
    jwks_uri = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"

    monkeypatch.setattr(settings, "entra_enabled", True)
    monkeypatch.setattr(settings, "entra_tenant_id", tenant_id)
    monkeypatch.setattr(settings, "entra_client_id", audience)
    monkeypatch.setattr(settings, "entra_issuer", issuer)
    monkeypatch.setattr(settings, "entra_jwks_uri", jwks_uri)

    private_pem, jwks = _make_rsa_keys_and_jwks(kid="entra-kid")
    monkeypatch.setattr(
        "app.auth.service.get_http_client", AsyncMock(return_value=_FakeHttpClient(jwks))
    )

    expired_claims = {
        "iss": issuer,
        "aud": audience,
        "exp": int(time.time()) - 10,
        "iat": int(time.time()) - 600,
        "oid": "550e8400-e29b-41d4-a716-446655440000",
        "roles": ["ai-poc-participant"],
    }
    token = jose_jwt.encode(
        expired_claims, private_pem, algorithm="RS256", headers={"kid": "entra-kid"}
    )

    service = JWTAuthService()
    with pytest.raises(HTTPException) as excinfo:
        await service.validate_token(token)
    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_validate_entra_token_rejects_invalid_signature(monkeypatch):
    tenant_id = "11111111-1111-1111-1111-111111111111"
    issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
    audience = "22222222-2222-2222-2222-222222222222"
    jwks_uri = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"

    monkeypatch.setattr(settings, "entra_enabled", True)
    monkeypatch.setattr(settings, "entra_tenant_id", tenant_id)
    monkeypatch.setattr(settings, "entra_client_id", audience)
    monkeypatch.setattr(settings, "entra_issuer", issuer)
    monkeypatch.setattr(settings, "entra_jwks_uri", jwks_uri)

    # JWKS contains key A
    _private_a, jwks_a = _make_rsa_keys_and_jwks(kid="entra-kid")
    # Token is signed with key B but uses same kid so it won't match
    private_b, _jwks_b = _make_rsa_keys_and_jwks(kid="entra-kid")

    monkeypatch.setattr(
        "app.auth.service.get_http_client", AsyncMock(return_value=_FakeHttpClient(jwks_a))
    )

    claims = {
        "iss": issuer,
        "aud": audience,
        "exp": int(time.time()) + 600,
        "iat": int(time.time()) - 10,
        "oid": "550e8400-e29b-41d4-a716-446655440000",
        "roles": ["ai-poc-participant"],
    }
    token = jose_jwt.encode(claims, private_b, algorithm="RS256", headers={"kid": "entra-kid"})

    service = JWTAuthService()
    with pytest.raises(HTTPException) as excinfo:
        await service.validate_token(token)
    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_validate_entra_token_rejects_missing_issuer(monkeypatch):
    tenant_id = "11111111-1111-1111-1111-111111111111"
    audience = "22222222-2222-2222-2222-222222222222"
    jwks_uri = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"

    monkeypatch.setattr(settings, "entra_enabled", True)
    monkeypatch.setattr(settings, "entra_tenant_id", tenant_id)
    monkeypatch.setattr(settings, "entra_client_id", audience)
    monkeypatch.setattr(
        settings, "entra_issuer", f"https://login.microsoftonline.com/{tenant_id}/v2.0"
    )
    monkeypatch.setattr(settings, "entra_jwks_uri", jwks_uri)

    private_pem, jwks = _make_rsa_keys_and_jwks(kid="entra-kid")
    monkeypatch.setattr(
        "app.auth.service.get_http_client", AsyncMock(return_value=_FakeHttpClient(jwks))
    )

    # No `iss` claim -> issuer detection fails -> denied
    claims = {
        "aud": audience,
        "exp": int(time.time()) + 600,
        "iat": int(time.time()) - 10,
        "oid": "550e8400-e29b-41d4-a716-446655440000",
        "roles": ["ai-poc-participant"],
    }
    token = jose_jwt.encode(claims, private_pem, algorithm="RS256", headers={"kid": "entra-kid"})

    service = JWTAuthService()
    with pytest.raises(HTTPException) as excinfo:
        await service.validate_token(token)
    assert excinfo.value.status_code == 401
