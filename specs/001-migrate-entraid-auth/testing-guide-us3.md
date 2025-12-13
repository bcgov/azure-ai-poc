# Testing Guide (US3): Coexistence & Rollback (Keycloak + Microsoft Entra ID)

This guide validates that the MAF backend (`api-ms-agent`) accepts Keycloak and Entra tokens during coexistence, and that it can be safely cut over / rolled back via feature flags.

## Prerequisites

- Backend is running.
- You can generate (or obtain) test tokens for:
  - a Keycloak user
  - an Entra user
- Both users have the required app role(s) (example: `ai-poc-participant`).

## Environment flags

The backend supports these feature flags:

- `ENTRA_ENABLED`:
  - `true` → accept Entra-issued JWTs
  - `false` → reject Entra-issued JWTs
- `KEYCLOAK_ENABLED`:
  - `true` → accept Keycloak-issued JWTs
  - `false` → reject Keycloak-issued JWTs

Safety rule:
- If both are `false`, all auth should fail (`401`).

## Test matrix

For each combination below, call the same protected endpoint with both tokens.

1) Coexistence (both enabled)
- `ENTRA_ENABLED=true`
- `KEYCLOAK_ENABLED=true`
Expected:
- Entra token → `200`
- Keycloak token → `200`

2) Cutover to Entra (Keycloak disabled)
- `ENTRA_ENABLED=true`
- `KEYCLOAK_ENABLED=false`
Expected:
- Entra token → `200`
- Keycloak token → `401`

3) Rollback to Keycloak (Entra disabled)
- `ENTRA_ENABLED=false`
- `KEYCLOAK_ENABLED=true`
Expected:
- Entra token → `401`
- Keycloak token → `200`

4) Safety check (both disabled)
- `ENTRA_ENABLED=false`
- `KEYCLOAK_ENABLED=false`
Expected:
- Entra token → `401`
- Keycloak token → `401`

## Example curl commands

Replace `<TOKEN>` and `<URL>`:

- Entra:
  - `curl -i -H "Authorization: Bearer <ENTRA_TOKEN>" <URL>`
- Keycloak:
  - `curl -i -H "Authorization: Bearer <KEYCLOAK_TOKEN>" <URL>`

If you get `403`, it usually means authentication succeeded but the token lacks the required role claim.
