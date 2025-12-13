# Data Model: Entra ID + Keycloak Coexistence

**Date**: 2025-12-12  
**Branch**: `001-migrate-entraid-auth`

This feature does **not** introduce a persistence layer for authentication/authorization.
The “data model” here describes the *conceptual* entities and relationships needed to reason about behavior,
configuration, and validation.

---

## Entities

### 1) AuthProvider

Represents an identity provider the backend can accept tokens from.

**Fields**:
- `name`: Human label (e.g., "entra", "keycloak")
- `enabled`: Whether tokens from this provider are accepted
- `issuer`: Expected `iss` claim value or issuer pattern
- `audiences`: Allowed `aud` values for this provider
- `jwks_uri`: Location of signing keys

**Notes**:
- Multiple `AuthProvider` entries may be enabled simultaneously during coexistence.

---

### 2) AccessToken (JWT)

A bearer token presented to protected endpoints.

**Fields (common)**:
- `iss`: Issuer
- `aud`: Audience
- `exp`: Expiration
- `iat`: Issued-at
- `sub`: Subject identifier

**Fields (authorization)**:
- `roles`: List of application roles (preferred for Entra app roles)
- Provider-specific role/group claims may exist but are normalized internally

---

### 3) AuthenticatedPrincipal

Represents the authenticated identity after token validation.

**Fields**:
- `provider`: Which provider validated the token ("entra" or "keycloak")
- `subject_id`: Stable subject identifier
- `display_name`: Optional
- `email`: Optional
- `roles`: Normalized list of application roles used for authorization decisions

---

### 4) AuthorizationRole

Represents an application-defined role value used for authorization checks.

**Fields**:
- `value`: Role string (e.g., `ai-poc-participant`, `api.access`)
- `source`: Where it came from (e.g., Entra app role claim, Keycloak role claim)

---

### 5) FeatureFlags

Represents operator-controlled toggles.

**Fields**:
- `entra_tokens_enabled`: Accept Entra-issued tokens
- `keycloak_tokens_enabled`: Accept Keycloak-issued tokens

---

## Relationships

- An `AuthProvider` validates an `AccessToken` → produces an `AuthenticatedPrincipal`.
- An `AuthenticatedPrincipal` contains zero-or-more `AuthorizationRole` values.
- `FeatureFlags` gates whether a given `AuthProvider` is allowed.

---

## State / Transitions

### Coexistence lifecycle

1. **Coexistence**: Entra enabled + Keycloak enabled
2. **Cutover**: Entra enabled + Keycloak disabled
3. **Rollback**: Entra enabled + Keycloak enabled (or Keycloak enabled only)

---

## Validation Rules

- Deny by default when:
  - token is missing/invalid
  - issuer is unknown
  - provider is disabled
  - signature/expiry/audience/issuer validation fails
- Role checks must be consistent across providers (same internal role names).