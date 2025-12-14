"""Authentication service for JWT validation with Keycloak."""

import time
from typing import Any

from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.auth.models import KeycloakUser
from app.auth.role_mapping import normalize_keycloak_roles
from app.config import settings
from app.http_client import get_http_client
from app.logger import get_logger

logger = get_logger(__name__)

# JWKS cache TTL in seconds (10 minutes - balances key rotation detection with performance)
_JWKS_CACHE_TTL_SECONDS = 600


class AuthService:
    """JWT authentication service for Keycloak integration."""

    def __init__(self):
        """Initialize the auth service.

        Require explicit Keycloak configuration in non-local environments to
        avoid validating tokens against an unintended identity provider.
        """
        self.keycloak_url = settings.keycloak_url
        self.keycloak_realm = settings.keycloak_realm
        self.keycloak_client_id = settings.keycloak_client_id

        # In non-local environments require explicit configuration
        if settings.environment != "local":
            if not (self.keycloak_url and self.keycloak_realm and self.keycloak_client_id):
                raise ValueError(
                    "KEYCLOAK_URL, KEYCLOAK_REALM, and KEYCLOAK_CLIENT_ID must be configured "
                    "in non-local environments"
                )
        else:
            # Safe defaults for local development only
            self.keycloak_url = self.keycloak_url or "https://dev.loginproxy.gov.bc.ca/auth"
            self.keycloak_realm = self.keycloak_realm or "standard"
            self.keycloak_client_id = self.keycloak_client_id or "azure-poc-6086"

        self.jwks_uri = (
            f"{self.keycloak_url}/realms/{self.keycloak_realm}/protocol/openid-connect/certs"
        )
        # issuer URL used to validate 'iss' claim
        self.issuer_url = f"{self.keycloak_url}/realms/{self.keycloak_realm}"
        self._jwks_cache: dict[str, Any] | None = None
        self._jwks_cache_time: float = 0.0

    async def validate_token(self, token: str) -> KeycloakUser:
        """Validate JWT token and return user information."""
        try:
            # Decode token header to get the key ID
            try:
                unverified_header = jwt.get_unverified_header(token)
            except JWTError as e:
                logger.error("Invalid token format", error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token format",
                ) from e

            if "kid" not in unverified_header:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing key ID",
                )

            # Get the signing key from Keycloak
            kid = str(unverified_header["kid"])  # Ensure kid is a string
            public_key = await self._get_signing_key(kid)

            # Verify and decode the token, validating audience and issuer
            try:
                payload = jwt.decode(
                    token,
                    public_key,
                    algorithms=["RS256"],
                    audience=self.keycloak_client_id,
                    issuer=self.issuer_url,
                    options={"verify_exp": True},
                )
            except JWTError as e:
                logger.error("JWT verification failed", error_type=type(e).__name__)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                ) from e

            # Validate that user has client roles
            # NOTE: If the project wants to allow roleless tokens for some routes,
            # move this check into the per-route `require_roles` dependency instead.
            roles = normalize_keycloak_roles(payload, self.keycloak_client_id)
            payload["client_roles"] = roles

            if not roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Token missing required client roles",
                )

            # Create user object
            user = KeycloakUser(**payload)
            return user

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Token validation error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token validation failed",
            ) from e

    async def _get_signing_key(self, kid: str, force_refresh: bool = False) -> str:
        """Get the signing key from Keycloak JWKS endpoint with TTL-based caching.

        To avoid unbounded recursion when a requested `kid` is not found in the
        current cache, allow at most one forced refresh per call (controlled by
        the `force_refresh` flag).
        """
        try:
            # Check if cache is expired or empty
            cache_age = time.time() - self._jwks_cache_time
            cache_expired = cache_age > _JWKS_CACHE_TTL_SECONDS

            if not self._jwks_cache or cache_expired:
                client = await get_http_client()
                response = await client.get(self.jwks_uri)
                response.raise_for_status()
                self._jwks_cache = response.json()
                self._jwks_cache_time = time.time()
                logger.debug(
                    "jwks_cache_refreshed",
                    cache_was_expired=cache_expired,
                    keys_count=len(self._jwks_cache.get("keys", [])),
                )

            # Find the key with matching kid
            for key_data in self._jwks_cache.get("keys", []):
                if key_data.get("kid") == kid:
                    try:
                        # Use jose library's built-in JWK to PEM conversion
                        from jose.backends import RSAKey

                        # Convert JWK to RSA key object and get PEM
                        rsa_key = RSAKey(key_data, algorithm="RS256")
                        pem = rsa_key.to_pem()

                        # Ensure we return a string
                        if isinstance(pem, bytes):
                            return pem.decode("utf-8")
                        return pem

                    except Exception as decode_error:
                        logger.error(
                            "Error converting JWK to PEM",
                            error_type=type(decode_error).__name__,
                            kid=str(kid),
                        )
                        raise

            # Key not found - attempt ONE refresh in case of key rotation
            if not force_refresh:
                logger.info("jwks_key_not_found_refreshing", kid=kid)
                self._jwks_cache = None  # Force refresh on next call
                # Recursive call with force_refresh=True prevents unbounded loops
                return await self._get_signing_key(kid, force_refresh=True)

            # Key still not found after refresh - return 401
            logger.warning("jwks_key_not_found_after_refresh", kid=kid)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find signing key",
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error getting signing key", error_type=type(e).__name__, kid=str(kid))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to verify token signature",
            ) from e

    def has_role(self, user: KeycloakUser, role: str) -> bool:
        """Check if user has the specified role."""
        if not user.client_roles:
            logger.info("User has no client roles", sub=user.sub)
            return False

        return role in user.client_roles


# Global auth service instance
_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    """Get the global auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
