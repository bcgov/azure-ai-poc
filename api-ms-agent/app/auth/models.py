"""Authentication models and types."""

from pydantic import BaseModel


class KeycloakUser(BaseModel):
    """Keycloak user information from JWT token."""

    sub: str
    email: str | None = None
    preferred_username: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    client_roles: list[str] | None = None
    aud: str | list[str] | None = None
