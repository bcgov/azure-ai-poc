# Security Checklist — Entra ID + Keycloak Coexistence

Use this checklist before enabling Entra in production, and after any auth configuration changes.

## Token Validation

- [ ] Validate access tokens using **asymmetric signing** (RS256) via issuer JWKS (never accept HS256).
- [ ] Verify the token `iss` matches the configured issuer exactly.
  - Entra: `https://login.microsoftonline.com/<tenant-id>/v2.0`
  - Keycloak: `<keycloak-url>/realms/<realm>`
- [ ] Verify the token `aud` matches the configured client/application ID.
- [ ] Verify token expiry (`exp`) is enforced.
- [ ] Consider replay protection where applicable (e.g., validate `jti` if issued and implement replay detection if required by threat model).
- [ ] Ensure `ENTRA_ENABLED` and/or `KEYCLOAK_ENABLED` are set so at least one provider is enabled.

## JWKS / Network

- [ ] JWKS endpoints are **HTTPS-only**.
- [ ] JWKS caching is enabled and TTL is reasonable (`JWKS_CACHE_TTL_SECONDS`).
- [ ] Outbound traffic to JWKS endpoints is allowed (App Service / network rules).

## Logging

- [ ] Logs do **not** include raw bearer tokens.
- [ ] Auth errors returned to clients do **not** leak secrets or stack traces.
- [ ] Auth logs include enough context for investigation (request id, issuer, provider) without sensitive data.
- [ ] Verify **no secrets** are logged (bearer tokens, client secrets, API keys, cookies, or Authorization headers).

## CORS / Browser Security

- [ ] Verify CORS allows only expected origins for the SPA.
- [ ] Verify responses do not accidentally allow wildcard origins in production.

## Authorization

- [ ] Entra app roles are defined on the API app registration and assigned to users/groups.
- [ ] The API enforces required roles on protected endpoints (e.g., `ai-poc-participant`).
- [ ] Role-denial (403) events are monitored.

## Token Lifetime

- [ ] Access token lifetime is **< 1 hour** (recommended for access tokens).
- [ ] Client apps use refresh mechanisms (MSAL) rather than long-lived access tokens.

## Cutover / Rollback

- [ ] Coexistence phase plan exists and is communicated (see [infra/MIGRATION_RUNBOOK.md](MIGRATION_RUNBOOK.md)).
- [ ] Rollback plan exists (see [infra/ROLLBACK.md](ROLLBACK.md)).
