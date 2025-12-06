"""Authentication service for JWT validation with Keycloak."""

from typing import Any

import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.auth.models import KeycloakUser
from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


class AuthService:
    """JWT authentication service for Keycloak integration."""

    def __init__(self):
        """Initialize the auth service."""
        self.keycloak_url = getattr(
            settings, "KEYCLOAK_URL", "https://dev.loginproxy.gov.bc.ca/auth"
        )
        self.keycloak_realm = getattr(settings, "KEYCLOAK_REALM", "standard")
        self.keycloak_client_id = getattr(settings, "KEYCLOAK_CLIENT_ID", "azure-poc-6086")

        if not self.keycloak_url or not self.keycloak_realm:
            raise ValueError("KEYCLOAK_URL and KEYCLOAK_REALM must be configured")

        self.jwks_uri = (
            f"{self.keycloak_url}/realms/{self.keycloak_realm}/protocol/openid-connect/certs"
        )
        self._jwks_cache: dict[str, Any] | None = None

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

            # Verify and decode the token
            try:
                payload = jwt.decode(
                    token,
                    public_key,
                    algorithms=["RS256"],
                    audience=self.keycloak_client_id,
                    options={"verify_exp": True},
                )
                logger.info("Token decoded successfully", sub=payload.get("sub"))
            except JWTError as e:
                logger.error("JWT verification failed", error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                ) from e

            # Validate audience claim
            await self._validate_audience(payload)

            # Validate that user has client roles
            if not payload.get("client_roles"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Token missing client roles",
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

    async def _get_signing_key(self, kid: str) -> str:
        """Get the signing key from Keycloak JWKS endpoint."""
        try:
            if not self._jwks_cache:
                async with httpx.AsyncClient() as client:
                    response = await client.get(self.jwks_uri, timeout=30.0)
                    response.raise_for_status()
                    self._jwks_cache = response.json()

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
                            error=str(decode_error),
                            kid=str(kid),
                        )
                        raise

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find signing key",
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error getting signing key", error=str(e), kid=str(kid))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to verify token signature",
            ) from e

    async def _validate_audience(self, payload: dict[str, Any]) -> None:
        """Validate the audience claim in the token."""
        if not self.keycloak_client_id:
            raise ValueError("KEYCLOAK_CLIENT_ID must be configured")

        aud = payload.get("aud")
        if not aud:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing audience claim",
            )

        # Handle both string and array audience values
        audiences = [aud] if isinstance(aud, str) else aud

        if self.keycloak_client_id not in audiences:
            logger.error(
                "Audience validation failed",
                expected=self.keycloak_client_id,
                received=audiences,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token audience does not match expected client",
            )

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
