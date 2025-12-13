# Migration Runbook: Keycloak → Microsoft Entra ID (1-week Coexistence)

This runbook describes a conservative migration strategy where the backend accepts both Keycloak and Entra tokens during a coexistence window, followed by a cutover to Entra-only.

## Key controls

Backend feature flags:
- `ENTRA_ENABLED`
- `KEYCLOAK_ENABLED`

Recommended defaults:
- Coexistence window: `ENTRA_ENABLED=true`, `KEYCLOAK_ENABLED=true`
- Post-cutover: `ENTRA_ENABLED=true`, `KEYCLOAK_ENABLED=false`

## Timeline

### Day 0 (enable coexistence)

- Deploy backend with both providers enabled.
- Validate with both token types:
  - Entra token → `200`
  - Keycloak token → `200`
- Deploy frontend configured for Entra login (MSAL).

### Days 1–6 (monitor)

- Monitor auth failures (`401`) vs authorization failures (`403`).
- Monitor JWKS fetch errors/timeouts (issuer/JWKS configuration issues).
- Monitor user support tickets for sign-in issues.

### Day 7 (cutover)

- Disable Keycloak token acceptance:
  - Set `KEYCLOAK_ENABLED=false`
  - Keep `ENTRA_ENABLED=true`
- Validate:
  - Entra token → `200`
  - Keycloak token → `401`

## Cutover trigger criteria (examples)

Proceed with cutover only if:
- Entra login success rate is stable.
- Token roles (`roles` claim) are present for role-gated flows.
- No unresolved issuer/JWKS misconfiguration.

## User communication template

Subject: Authentication migration to Microsoft Entra ID

Body:
- We are migrating login to Microsoft Entra ID.
- During the migration window, both login systems will work.
- On <DATE>, Keycloak-based login will be disabled.
- If you encounter issues, contact <SUPPORT_CHANNEL>.

## Rollback

If issues arise after cutover:
- Set `ENTRA_ENABLED=false`, `KEYCLOAK_ENABLED=true`.
- See `infra/ROLLBACK.md` for details.
