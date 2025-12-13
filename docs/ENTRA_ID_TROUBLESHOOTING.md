# Entra ID Troubleshooting

This guide focuses on common failures when running the Keycloak + Entra coexistence model.

## Token validation fails (401)

Symptoms:
- API returns `401` with `code` like `auth.validation_failed`, `auth.issuer_not_accepted`, or `auth.invalid_or_expired`.

Checks:
- Verify the token `iss` matches the expected issuer.
  - Entra v2 issuer typically: `https://login.microsoftonline.com/<tenant-id>/v2.0`
- Verify the token `aud` matches the API app registration.
  - For Entra, access tokens for custom APIs use the **Application ID URI** format: `api://<client-id>`
  - Backend `ENTRA_CLIENT_ID` must use the `api://` prefix to match (e.g., `api://2dfe43c4-...`)
  - For Keycloak, `aud` typically matches `KEYCLOAK_CLIENT_ID` directly.
- Verify token expiry (`exp`) and system clock skew.
  - Check server time is correct (UTC). If system time is off by minutes, `exp`/`nbf` validation can fail.
- Verify the backend can reach the JWKS URI over HTTPS.
  - Entra JWKS: `https://login.microsoftonline.com/<tenant-id>/discovery/v2.0/keys`
  - From the backend host/network, test connectivity with `curl` (or equivalent).
- Verify feature flags:
  - `ENTRA_ENABLED=true` to accept Entra tokens
  - `KEYCLOAK_ENABLED=true` to accept Keycloak tokens

Debug tip (non-production): inspect JWT claims to confirm `iss`, `aud`, `exp`, and `roles`:

- Copy the middle JWT segment (payload) and decode it.
- Use a JWT debugger (do not paste real production tokens into third-party tools).

## User locked out after cutover

Symptoms:
- User can log in, but all protected API calls return 403.

Checks:
- Confirm the user (or group) is assigned an **app role** on the **API enterprise application**.
- Confirm the Entra access token includes a `roles` claim.
- Confirm the API endpoints require the expected role (commonly `ai-poc-participant`).

## Roles claim missing (Entra)

Symptoms:
- Token validates (401 does not occur), but role checks fail (403) because roles are empty.

Checks:
- Ensure roles are configured as **App roles** on the API app registration.
- Ensure the user/group is assigned those roles on the enterprise application.
- Ensure the frontend requests an access token for the API scope configured for your environment.

## Metrics endpoint

- Auth metrics are exposed at `GET /api/v1/auth/metrics` in Prometheus text format.
- If the endpoint is missing, verify the backend is running the updated code and routers are included.
