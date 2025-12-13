"""Authentication service for JWT validation (Keycloak + Entra ID)."""

from __future__ import annotations

import time
from typing import Any

from fastapi import status
from jose import JWTError, jwt

from app.auth.errors import AuthError
from app.auth.models import AuthenticatedUser, EntraUser, KeycloakUser
from app.auth.role_mapping import normalize_entra_roles, normalize_keycloak_roles
from app.config import settings
from app.http_client import get_http_client
from app.logger import get_logger

logger = get_logger(__name__)


class JWTAuthService:
    """JWT authentication service supporting multiple issuers."""

    def __init__(self):
        self.keycloak_enabled = settings.keycloak_enabled
        self.keycloak_url = settings.keycloak_url
        self.keycloak_realm = settings.keycloak_realm
        self.keycloak_client_id = settings.keycloak_client_id

        self.entra_enabled = settings.entra_enabled
        self.entra_tenant_id = settings.entra_tenant_id
        self.entra_client_id = settings.entra_client_id
        self.entra_issuer = settings.entra_issuer
        self.entra_jwks_uri = settings.entra_jwks_uri

        self.jwks_cache_ttl_seconds = settings.jwks_cache_ttl_seconds

        self.keycloak_issuer = (
            f"{self.keycloak_url}/realms/{self.keycloak_realm}"
            if self.keycloak_url and self.keycloak_realm
            else ""
        )
        self.keycloak_jwks_uri = (
            f"{self.keycloak_issuer}/protocol/openid-connect/certs" if self.keycloak_issuer else ""
        )

        if not self.entra_issuer and self.entra_tenant_id:
            self.entra_issuer = f"https://login.microsoftonline.com/{self.entra_tenant_id}/v2.0"
        if not self.entra_jwks_uri and self.entra_tenant_id:
            self.entra_jwks_uri = (
                f"https://login.microsoftonline.com/{self.entra_tenant_id}/discovery/v2.0/keys"
            )

        # v1.0 issuer for access tokens (used when audience is a custom API)
        self.entra_issuer_v1 = (
            f"https://sts.windows.net/{self.entra_tenant_id}/" if self.entra_tenant_id else ""
        )

        # jwks_uri -> {"jwks": <dict>, "fetched_at": <epoch_seconds>}
        self._jwks_cache: dict[str, dict[str, Any]] = {}

    def _get_unverified_claims_for_logging(self, token: str) -> dict[str, Any]:
        try:
            return dict(jwt.get_unverified_claims(token))
        except Exception:
            return {}

    async def validate_token(self, token: str) -> AuthenticatedUser:
        """Validate JWT token and return normalized user information."""
        unverified = self._get_unverified_claims_for_logging(token)
        issuer = str(unverified.get("iss") or "")
        subject = str(unverified.get("oid") or unverified.get("sub") or "")
        exp = unverified.get("exp")

        try:
            if not issuer:
                issuer = self._get_unverified_issuer(token)

            # Accept both v1.0 (sts.windows.net) and v2.0 (login.microsoftonline.com) issuers
            if issuer and self.entra_enabled and self.entra_issuer:
                if issuer == self.entra_issuer or issuer == self.entra_issuer_v1:
                    return await self._validate_entra_token(token, issuer)

            if (
                issuer
                and self.keycloak_enabled
                and self.keycloak_issuer
                and issuer == self.keycloak_issuer
            ):
                return await self._validate_keycloak_token(token)

            # Deny-by-default for unknown issuers or disabled providers
            logger.warning(
                "auth_unknown_or_disabled_issuer",
                issuer=issuer,
                entra_enabled=self.entra_enabled,
                keycloak_enabled=self.keycloak_enabled,
            )
            raise AuthError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token issuer is not accepted",
                code="auth.issuer_not_accepted",
                headers={"WWW-Authenticate": "Bearer"},
            )

        except AuthError as exc:
            logger.warning(
                "auth_failed",
                code=exc.code,
                issuer=issuer,
                subject=subject or None,
                exp=exp,
                status_code=exc.status_code,
            )
            raise
        except Exception as exc:
            logger.error("token_validation_error", error=str(exc))
            logger.warning(
                "auth_failed",
                code="auth.validation_failed",
                issuer=issuer,
                subject=subject or None,
                exp=exp,
            )
            raise AuthError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token validation failed",
                code="auth.validation_failed",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

    async def _validate_entra_token(self, token: str, token_issuer: str | None = None) -> EntraUser:
        if not self.entra_enabled:
            raise AuthError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Entra auth disabled",
                code="auth.provider_disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not self.entra_jwks_uri or not self.entra_client_id or not self.entra_issuer:
            raise AuthError(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Entra auth is enabled but not configured",
                code="auth.provider_misconfigured",
            )

        # Use the actual issuer from the token for validation (v1.0 or v2.0)
        expected_issuer = token_issuer or self.entra_issuer

        payload = await self._verify_and_decode(
            token=token,
            jwks_uri=self.entra_jwks_uri,
            expected_issuer=expected_issuer,
            expected_audience=self.entra_client_id,
        )

        roles = normalize_entra_roles(payload)

        # Prefer oid (stable object id) for user identity when present
        sub = str(payload.get("oid") or payload.get("sub") or "")
        if not sub:
            raise AuthError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject",
                code="auth.missing_subject",
                headers={"WWW-Authenticate": "Bearer"},
            )

        email = payload.get("preferred_username") or payload.get("upn") or payload.get("email")
        user = EntraUser(
            sub=sub,
            oid=payload.get("oid"),
            email=email,
            preferred_username=payload.get("preferred_username") or payload.get("upn"),
            name=payload.get("name"),
            roles=roles,
            aud=payload.get("aud"),
            iss=payload.get("iss"),
        )

        logger.info(
            "auth_success",
            provider="entra",
            issuer=self.entra_issuer,
            subject=sub,
            roles_count=len(roles),
        )
        return user

    async def _validate_keycloak_token(self, token: str) -> KeycloakUser:
        if not self.keycloak_enabled:
            raise AuthError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Keycloak auth disabled",
                code="auth.provider_disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not self.keycloak_jwks_uri or not self.keycloak_client_id or not self.keycloak_issuer:
            raise AuthError(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Keycloak auth is enabled but not configured",
                code="auth.provider_misconfigured",
            )

        payload = await self._verify_and_decode(
            token=token,
            jwks_uri=self.keycloak_jwks_uri,
            expected_issuer=self.keycloak_issuer,
            expected_audience=self.keycloak_client_id,
        )

        roles = normalize_keycloak_roles(payload, client_id=self.keycloak_client_id)
        sub = str(payload.get("sub") or "")
        if not sub:
            raise AuthError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject",
                code="auth.missing_subject",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = KeycloakUser(
            sub=sub,
            email=payload.get("email"),
            preferred_username=payload.get("preferred_username"),
            given_name=payload.get("given_name"),
            family_name=payload.get("family_name"),
            client_roles=payload.get("client_roles"),
            roles=roles,
            aud=payload.get("aud"),
            iss=payload.get("iss"),
        )

        logger.info(
            "auth_success",
            provider="keycloak",
            issuer=self.keycloak_issuer,
            subject=sub,
            roles_count=len(roles),
        )
        return user

    def has_role(self, user: AuthenticatedUser, role: str) -> bool:
        """Check if user has the specified role."""
        return role in (user.roles or [])

    def _get_unverified_issuer(self, token: str) -> str:
        try:
            claims = jwt.get_unverified_claims(token)
        except JWTError as exc:
            raise AuthError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format",
                code="auth.invalid_format",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        return str(claims.get("iss") or "")

    async def _verify_and_decode(
        self,
        *,
        token: str,
        jwks_uri: str,
        expected_issuer: str,
        expected_audience: str,
    ) -> dict[str, Any]:
        try:
            unverified_header = jwt.get_unverified_header(token)
        except JWTError as exc:
            raise AuthError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format",
                code="auth.invalid_format",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        kid = unverified_header.get("kid")
        if not kid:
            raise AuthError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing key ID",
                code="auth.missing_kid",
                headers={"WWW-Authenticate": "Bearer"},
            )

        public_key = await self._get_signing_key(jwks_uri=jwks_uri, kid=str(kid))

        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=expected_audience,
                issuer=expected_issuer,
                options={"verify_exp": True},
            )
        except JWTError as exc:
            # Log the actual token claims for debugging
            try:
                unverified_claims = jwt.get_unverified_claims(token)
                logger.warning(
                    "jwt_decode_failed",
                    error=str(exc),
                    token_aud=unverified_claims.get("aud"),
                    token_iss=unverified_claims.get("iss"),
                    expected_aud=expected_audience,
                    expected_iss=expected_issuer,
                )
            except Exception:
                pass
            raise AuthError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                code="auth.invalid_or_expired",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        return payload

    async def _get_signing_key(self, *, jwks_uri: str, kid: str) -> str:
        try:
            jwks = await self._get_jwks(jwks_uri)
            for key_data in jwks.get("keys", []):
                if key_data.get("kid") == kid:
                    from jose.backends import RSAKey

                    rsa_key = RSAKey(key_data, algorithm="RS256")
                    pem = rsa_key.to_pem()
                    return pem.decode("utf-8") if isinstance(pem, bytes) else pem

            # Key not found - force refresh once in case of rotation
            logger.info("jwks_key_not_found_refreshing", jwks_uri=jwks_uri, kid=kid)
            self._jwks_cache.pop(jwks_uri, None)
            jwks = await self._get_jwks(jwks_uri)
            for key_data in jwks.get("keys", []):
                if key_data.get("kid") == kid:
                    from jose.backends import RSAKey

                    rsa_key = RSAKey(key_data, algorithm="RS256")
                    pem = rsa_key.to_pem()
                    return pem.decode("utf-8") if isinstance(pem, bytes) else pem

            raise AuthError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find signing key",
                code="auth.signing_key_not_found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        except AuthError:
            raise
        except Exception as exc:
            logger.error("error_getting_signing_key", jwks_uri=jwks_uri, kid=kid, error=str(exc))
            raise AuthError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to verify token signature",
                code="auth.signature_verification_failed",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

    async def _get_jwks(self, jwks_uri: str) -> dict[str, Any]:
        now = time.time()
        cached = self._jwks_cache.get(jwks_uri)
        if cached:
            fetched_at = float(cached.get("fetched_at") or 0)
            if now - fetched_at <= self.jwks_cache_ttl_seconds:
                return cached["jwks"]

        client = await get_http_client()
        response = await client.get(jwks_uri)
        response.raise_for_status()
        jwks = response.json()

        self._jwks_cache[jwks_uri] = {"jwks": jwks, "fetched_at": now}
        logger.debug(
            "jwks_cache_refreshed",
            jwks_uri=jwks_uri,
            keys_count=len(jwks.get("keys", [])),
            ttl_seconds=self.jwks_cache_ttl_seconds,
        )

        return jwks


# Global auth service instance
_auth_service: JWTAuthService | None = None


def get_auth_service() -> JWTAuthService:
    """Get the global auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = JWTAuthService()
    return _auth_service
