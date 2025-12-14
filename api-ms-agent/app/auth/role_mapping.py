"""Role extraction and normalization.

This module provides a single internal role list regardless of identity provider.
"""

from __future__ import annotations

from typing import Any


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value if v is not None]
    return []


def normalize_entra_roles(payload: dict[str, Any]) -> list[str]:
    """Extract application roles from an Entra access token.

    Entra emits application roles as strings in the `roles` claim.
    """

    return _as_list(payload.get("roles"))


def normalize_keycloak_roles(payload: dict[str, Any], client_id: str | None) -> list[str]:
    """Extract roles from a Keycloak access token.

    Supports common layouts:
    - Custom mapper populating `client_roles` (current app expectation)
    - realm_access.roles
    - resource_access[client_id].roles
    """

    roles: list[str] = []

    roles.extend(_as_list(payload.get("client_roles")))

    realm_access = payload.get("realm_access")
    if isinstance(realm_access, dict):
        roles.extend(_as_list(realm_access.get("roles")))

    if client_id:
        resource_access = payload.get("resource_access")
        if isinstance(resource_access, dict):
            client_entry = resource_access.get(client_id)
            if isinstance(client_entry, dict):
                roles.extend(_as_list(client_entry.get("roles")))

    # De-dupe while preserving order
    seen: set[str] = set()
    normalized: list[str] = []
    for role in roles:
        if not role:
            continue
        if role in seen:
            continue
        seen.add(role)
        normalized.append(role)

    return normalized
