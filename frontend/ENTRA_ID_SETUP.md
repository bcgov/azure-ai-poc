# Microsoft Entra ID Setup (Frontend SPA)

This guide describes how to configure Microsoft Entra ID for the React SPA in `frontend/`.

## 1) Create / identify Entra app registrations

You typically need two app registrations:

- **SPA app registration** (the browser client)
- **API app registration** (the backend resource / audience)

If your environment already uses the automation under `infra/scripts/entra/`, prefer that.

## 2) SPA app registration configuration

In the Entra admin portal:

1. Create an **App registration** for the SPA.
2. Under **Authentication**:
   - Add a **Single-page application** platform.
   - Add redirect URI(s) for your environments.
     - Local dev example: `http://localhost:5173/`
     - Deployed example: your frontend base URL
   - Ensure the SPA redirect URI exactly matches what the app uses.
3. Under **API permissions**:
   - Add delegated permissions / scopes required to call your API (see section 3).

## 3) API app registration configuration (scopes + roles)

For the backend API app registration:

1. Under **Expose an API**:
   - Set the **Application ID URI** if not already set.
   - Create one or more **scopes** (delegated permissions) if your SPA will request them.
2. Under **App roles**:
   - Define app roles used by the application (example: `ai-poc-participant`, `TENANT_ADMIN`).
   - Assign these roles to users or (recommended) to groups.

Important:
- The frontend displays roles from the token `roles` claim.
- The backend expects role-based authorization via the same `roles` claim.

## 4) Configure the frontend environment

Create/update `frontend/.env` (do not commit secrets):

- `VITE_ENTRA_TENANT_ID` – your tenant ID
- `VITE_ENTRA_CLIENT_ID` – SPA app registration client ID
- `VITE_ENTRA_AUTHORITY` – authority/issuer URL (example: `https://login.microsoftonline.com/<tenant-id>`)
- `VITE_API_SCOPES` – scopes to request (string or comma/space-separated)
  - Example: `api://<api-client-id>/.default` or `api://<api-client-id>/<scopeName>`
- `VITE_REDIRECT_URI` – optional override (defaults to `window.location.origin`)

## 5) Verify the login flow

1. Start the frontend.
2. Click **Login**.
3. Complete the Entra sign-in flow.
4. Confirm that:
   - the app shows the authenticated user
   - roles (if assigned) are displayed
   - API calls include `Authorization: Bearer <access_token>`

## Troubleshooting

- If you get consent/interaction errors, confirm the requested scopes exist and the user has consent.
- If roles are missing, confirm app roles are defined on the API app and assigned to the user/group.
- Redirect URI mismatches are the most common cause of sign-in failures.
