# US1 Manual Test Guide: Entra ID Auth (Admin)

**User story**: Admin can configure and test Entra authentication via curl/Postman.

This guide validates:
- Valid Entra token + correct role → `200`
- Invalid/expired token → `401`
- Missing role → `403`
- Auth failures return a structured JSON payload: `{ "detail", "code", "timestamp" }`

## Prerequisites

- `api-ms-agent` running locally (default: `http://localhost:4000`).
- Entra API app registration has an **app role** named `ai-poc-participant`.
- Your test user (or group) is assigned that app role.
- You have configured `api-ms-agent/.env` (or exported env vars) based on `api-ms-agent/.env.example`.

## Required backend environment variables

At minimum:

- `KEYCLOAK_ENABLED` (set to `false` if you want Entra-only testing)
- `ENTRA_ENABLED=true`
- `ENTRA_TENANT_ID=<tenant-guid>`
- `ENTRA_CLIENT_ID=<api-app-client-id>`

Optional (usually derived automatically if omitted):

- `ENTRA_ISSUER=https://login.microsoftonline.com/<tenant-guid>/v2.0`
- `ENTRA_JWKS_URI=https://login.microsoftonline.com/<tenant-guid>/discovery/v2.0/keys`

## Get an Entra access token

### Option A: Postman (recommended for interactive user auth)

1. In Postman, create a new request.
2. Authorization → OAuth 2.0.
3. Use your tenant’s authorization/token endpoints.
4. Request an access token for the API.
5. Ensure the resulting access token contains a `roles` claim including `ai-poc-participant`.

### Option B: Azure CLI (works when CLI can request the API scope)

If your org allows it, you can attempt:

- `az login --tenant <ENTRA_TENANT_ID>`
- `az account get-access-token --tenant <ENTRA_TENANT_ID> --scope api://<ENTRA_CLIENT_ID>/.default --query accessToken -o tsv`

If the CLI cannot acquire the right token for your API, use Postman.

## Test endpoints

### 1) Success: valid token + role (200)

`GET /api/v1/models/`

- `curl -H "Authorization: Bearer <ACCESS_TOKEN>" http://localhost:4000/api/v1/models/`

Expected:
- `200 OK`
- JSON body contains `models: [...]`

### 2) Missing role (403)

Use a token that does **not** have the `ai-poc-participant` role.

- `curl -H "Authorization: Bearer <ACCESS_TOKEN_WITHOUT_ROLE>" http://localhost:4000/api/v1/models/`

Expected:
- `403 Forbidden`
- JSON payload:
  - `code: "auth.missing_role"`
  - `detail: ...`
  - `timestamp: ...`

### 3) Missing Authorization header (401)

- `curl http://localhost:4000/api/v1/models/`

Expected:
- `401 Unauthorized`
- JSON payload:
  - `code: "auth.missing_authorization_header"`

### 4) Invalid token (401)

- `curl -H "Authorization: Bearer not-a-real-jwt" http://localhost:4000/api/v1/models/`

Expected:
- `401 Unauthorized`
- JSON payload:
  - `code: "auth.invalid_or_expired"` (or another auth.* code)

## Notes

- The backend enforces auth globally via middleware; route-level role checks are applied via `require_role("ai-poc-participant")`.
- Entra roles are sourced from the access token’s `roles` claim (app roles). If `roles` is empty/missing, role checks will deny access.
