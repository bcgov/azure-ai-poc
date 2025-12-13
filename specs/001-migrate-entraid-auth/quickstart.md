# Quickstart: Entra ID + Keycloak Coexistence

**Date**: 2025-12-12  
**Branch**: `001-migrate-entraid-auth`

---

## Local Development Setup

### Prerequisites

- **Azure Subscription**: With permissions to create app registrations
- **Python 3.13**: Backend development
- **Node.js 18+**: Frontend development
- **Azure CLI**: For creating Entra resources
- **uv**: For Python dependency management (repo standard)

---

## Step 1: Create Entra ID App Registrations

Use the repo’s deterministic automation scripts (no hidden defaults):

- Docs + examples: `infra/scripts/entra/README.md`
- Scripts:
  - `infra/scripts/entra/create-entra-apps.sh`
  - `infra/scripts/entra/create-entra-groups.sh`
  - `infra/scripts/entra/assign-entra-app-roles-to-groups.sh`
  - `infra/scripts/entra/add-users-to-groups.sh`

Example (bash):

```bash
cd infra/scripts/entra

./create-entra-apps.sh \
  --tenant-id "<tenant-guid>" \
  --app-prefix "azure-ai-poc-dev" \
  --spa-app-name "azure-ai-poc-dev-spa" \
  --api-app-name "azure-ai-poc-dev-api" \
  --s2s-app-name "azure-ai-poc-dev-s2s" \
  --spa-redirect-uri "http://localhost:5173/"
```

---

## Step 2: Backend Configuration

### 1. Update Environment Variables

**File**: `api-ms-agent/.env`

```bash
# Entra ID Configuration
ENTRA_ENABLED=true
ENTRA_TENANT_ID=11111111-1111-1111-1111-111111111111
# Use Application ID URI format (api:// prefix) - matches token aud claim
ENTRA_CLIENT_ID=api://22222222-2222-2222-2222-222222222222
ENTRA_ISSUER=https://login.microsoftonline.com/11111111-1111-1111-1111-111111111111/v2.0
ENTRA_JWKS_URI=https://login.microsoftonline.com/11111111-1111-1111-1111-111111111111/discovery/v2.0/keys

# Keycloak Configuration (for coexistence testing)
KEYCLOAK_ENABLED=true
KEYCLOAK_URL=https://dev.loginproxy.gov.bc.ca/auth
KEYCLOAK_REALM=standard
KEYCLOAK_CLIENT_ID=azure-poc-6086
```

### 2. Auth Service

The unified auth implementation (Keycloak + Entra) is already in place.

- Code: `api-ms-agent/app/auth/service.py`
- Backend flags: `KEYCLOAK_ENABLED` and `ENTRA_ENABLED`
- Entra issuer/JWKS: `ENTRA_ISSUER` and `ENTRA_JWKS_URI` (derived automatically from `ENTRA_TENANT_ID` if omitted)

### 3. Roles & Authorization Model

For Entra, prefer **application roles** emitted in the `roles` claim.

Operationally, you can still manage user access via **groups** by assigning **app roles to groups** and adding users to those groups (see the automation scripts in `infra/scripts/entra/`).

### 4. Authorization in Endpoints

Role enforcement is implemented as a FastAPI dependency.

- Dependency: `require_role("ai-poc-participant")` in `api-ms-agent/app/auth/dependencies.py`
- Middleware: `api-ms-agent/app/middleware/auth_middleware.py` stores the authenticated user on `request.state.current_user`

Example pattern:

```python
from typing import Annotated

from fastapi import Depends

from app.auth.dependencies import require_role
from app.auth.models import AuthenticatedUser

CurrentUser = Annotated[AuthenticatedUser, Depends(require_role("ai-poc-participant"))]
```
```

---

## Step 3: Frontend Configuration

### 1. Update Environment

**File**: `frontend/.env`

```bash
VITE_ENTRA_TENANT_ID=11111111-1111-1111-1111-111111111111
VITE_ENTRA_CLIENT_ID=33333333-3333-3333-3333-333333333333
VITE_ENTRA_AUTHORITY=https://login.microsoftonline.com/11111111-1111-1111-1111-111111111111/v2.0
VITE_API_SCOPES=["api://localhost-api/access_as_user"]
VITE_REDIRECT_URI=http://localhost:5173/
```

### 2. Install MSAL.js

```bash
cd frontend
npm install @azure/msal-browser @azure/msal-react
```

### 3. Create Auth Service

**File**: `frontend/src/service/auth-service.ts`

```typescript
import { PublicClientApplication, AuthenticationResult } from "@azure/msal-browser";

const config = {
  auth: {
    clientId: import.meta.env.VITE_ENTRA_CLIENT_ID,
    authority: import.meta.env.VITE_ENTRA_AUTHORITY,
    redirectUri: import.meta.env.VITE_REDIRECT_URI,
  },
  cache: {
    cacheLocation: "sessionStorage",
  },
};

export const msalInstance = new PublicClientApplication(config);

export async function acquireToken(): Promise<string> {
  try {
    const result = await msalInstance.acquireTokenSilent({
      scopes: import.meta.env.VITE_API_SCOPES,
    });
    return result.accessToken;
  } catch {
    // Trigger interactive flow if silent fails
    const result = await msalInstance.acquireTokenPopup({
      scopes: import.meta.env.VITE_API_SCOPES,
    });
    return result.accessToken;
  }
}

export async function login() {
  await msalInstance.loginPopup({
    scopes: import.meta.env.VITE_API_SCOPES,
  });
}

export async function logout() {
  await msalInstance.logout();
}
```

### 4. Create Auth Provider

**File**: `frontend/src/components/AuthProvider.tsx`

```typescript
import { MsalProvider } from "@azure/msal-react";
import { msalInstance } from "../service/auth-service";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  return <MsalProvider instance={msalInstance}>{children}</MsalProvider>;
}
```

### 5. Update Main App

**File**: `frontend/src/main.tsx`

```typescript
import React from "react";
import ReactDOM from "react-dom/client";
import { AuthProvider } from "./components/AuthProvider";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </React.StrictMode>
);
```

---

## Step 4: Testing

### Backend Token Validation Test

**File**: `api-ms-agent/tests/test_auth_entra.py`

```python
import pytest
from app.auth.service import JWTAuthService
import jwt

@pytest.mark.asyncio
async def test_validate_entra_token():
    """Test Entra ID token validation."""
    auth_service = JWTAuthService()
    
    # Generate test token (signed with test key)
    test_token = jwt.encode(
        {
            "iss": "https://login.microsoftonline.com/test-tenant/v2.0",
            "sub": "550e8400-e29b-41d4-a716-446655440000",
            "aud": "22222222-2222-2222-2222-222222222222",
            "exp": 9999999999,
            "iat": 1000000000,
            "oid": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@bcgov.ca",
            "roles": ["ai-poc-participant"],
        },
        "secret",
        algorithm="HS256",
    )
    
    # Validate
    user = await auth_service.validate_token(test_token)
    assert user.email == "user@bcgov.ca"
    assert "ai-poc-participant" in user.roles
```

### Frontend Login Test

**File**: `frontend/src/__tests__/auth.test.ts`

```typescript
import { acquireToken } from "../service/auth-service";
import { vi } from "vitest";

describe("Auth Service", () => {
  it("should acquire token from Entra", async () => {
    const token = await acquireToken();
    expect(token).toBeDefined();
    expect(token.length > 0).toBe(true);
  });
});
```

---

## Step 5: Local Testing

### Start Backend

```bash
cd api-ms-agent
uv sync
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 4000
```

### Start Frontend

```bash
cd frontend
npm install
npm run dev
```

### Test Protected Endpoint

```bash
# 1. Login and get token (via frontend or test)
TOKEN="eyJhbGc..."

# 2. Call protected endpoint
curl -H "Authorization: Bearer $TOKEN" http://localhost:4000/api/documents
```

---

## Troubleshooting

### Token Validation Fails

1. **Check issuer**: Verify `iss` claim matches configured authority
2. **Check audience**: Verify `aud` matches API client ID
3. **Check expiry**: Ensure token is not expired (`exp` > now)
4. **Check JWKS**: Manually fetch JWKS and verify public key is present

```bash
curl https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys | jq .
```

### Roles Not in Token

1. **Confirm you’re using an access token for the API**: The token `aud` must match the API app registration.
2. **Check app role assignment**: Ensure the user (or a group the user is in) is assigned an app role on the API app.
3. **Re-authenticate**: Role changes require the user to sign out/in to refresh tokens.

### CORS Issues

Add frontend origin to API app registration redirect URIs:

```bash
az ad app update --id $API_APP_ID --web-redirect-uris "http://localhost:5173"
```

---

## Next Steps

1. Run integration tests in CI/CD
2. Assign Entra app roles to groups; add users to groups
3. Canary rollout: enable for 10% of users
4. Monitor auth-related errors in Application Insights
5. Gradual cutover: disable Keycloak after 30-day coexistence period

