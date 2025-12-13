"""Authentication models and types."""

from typing import Literal

from pydantic import BaseModel, Field


class AuthenticatedUser(BaseModel):
    """Normalized user/principal information extracted from a validated JWT."""

    provider: Literal["keycloak", "entra"]

    # Stable subject identifier used by the app.
    # Keycloak: typically `sub`
    # Entra: prefer `oid` (object id) when available, else `sub`
    sub: str

    email: str | None = None
    preferred_username: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    name: str | None = None

    roles: list[str] = Field(default_factory=list)

    # Common JWT claims occasionally used by callers/logging.
    aud: str | list[str] | None = None
    iss: str | None = None


class KeycloakUser(AuthenticatedUser):
    """Keycloak user information from JWT token.

    Kept for backwards-compatibility with existing route type hints.
    """

    provider: Literal["keycloak"] = "keycloak"
    client_roles: list[str] | None = None


class EntraUser(AuthenticatedUser):
    """Microsoft Entra ID user information from JWT token."""

    provider: Literal["entra"] = "entra"
    oid: str | None = None
