# Migration Checklist: Keycloak → Microsoft Entra ID (Coexistence)

This checklist supports a safe migration from Keycloak-issued JWTs to Microsoft Entra ID-issued JWTs for the MAF backend (`api-ms-agent`) and the React frontend (`frontend`).

The backend supports coexistence and cutover via feature flags:
- `ENTRA_ENABLED` (accept Entra tokens)
- `KEYCLOAK_ENABLED` (accept Keycloak tokens)

## Pre-migration (coexistence readiness)

- Confirm Entra app registrations exist (SPA + API) and app roles are defined/assigned.
- Configure backend env vars for Entra (tenant/client/issuer/JWKS), plus:
  - Set `ENTRA_ENABLED=true`
  - Keep `KEYCLOAK_ENABLED=true`
- Validate both token types work against protected endpoints:
  - Entra token + required role claim → `200`
  - Keycloak token + required role claim → `200`
- Validate negative cases:
  - invalid/expired tokens → `401`
  - missing required role → `403`

## Migration (frontend cutover)

- Deploy frontend with MSAL configuration:
  - `VITE_ENTRA_TENANT_ID`, `VITE_ENTRA_CLIENT_ID`, `VITE_ENTRA_AUTHORITY`, `VITE_API_SCOPES`
- Perform a smoke test in a browser:
  - Login via Entra
  - Confirm API requests include `Authorization: Bearer <token>`
  - Confirm role-gated UI behaves as expected

## Post-migration (disable Keycloak)

- Once Entra traffic is stable, disable Keycloak validation:
  - Set `KEYCLOAK_ENABLED=false`
  - Keep `ENTRA_ENABLED=true`
- Re-test protected endpoints with both token types:
  - Entra token → `200`
  - Keycloak token → `401`

## Operational monitoring

- Monitor auth failures (`401`) vs authorization failures (`403`).
- Monitor JWKS fetch errors/timeouts (can indicate issuer/JWKS misconfiguration).
