# Rollback Procedure: Microsoft Entra ID → Keycloak

This procedure rolls back authentication acceptance from Microsoft Entra ID tokens to Keycloak tokens in the MAF backend (`api-ms-agent`).

The backend supports coexistence and cutover via feature flags:
- `ENTRA_ENABLED`
- `KEYCLOAK_ENABLED`

## Rollback trigger criteria (examples)

- Entra sign-in is failing at elevated rates.
- Access tokens are missing expected `roles` claims (role-based authorization failing).
- JWKS/issuer configuration issues cannot be resolved quickly.

## Immediate rollback (backend)

1. Update the backend configuration:
   - Set `ENTRA_ENABLED=false`
   - Set `KEYCLOAK_ENABLED=true`
2. Redeploy/restart the backend.
3. Validate behavior:
   - Keycloak token against protected endpoint → `200`
   - Entra token against protected endpoint → `401`

## Frontend considerations

- If the frontend has been switched to Entra-only login, users may still be signed in via Entra but calls will fail once `ENTRA_ENABLED=false`.
- Options:
  - Temporarily restore Keycloak login in the frontend, or
  - Re-enable coexistence (`ENTRA_ENABLED=true` and `KEYCLOAK_ENABLED=true`) while you coordinate a frontend rollback.

## Recovery

- Once the root cause is addressed, return to coexistence first:
  - `ENTRA_ENABLED=true`, `KEYCLOAK_ENABLED=true`
- Repeat cutover steps after validation.
