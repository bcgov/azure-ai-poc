# Quickstart: Entra ID Authentication Development

**Date**: 2025-12-11  
**Branch**: `001-migrate-entraid-auth`

---

## Local Development Setup

### Prerequisites

- **Azure Subscription**: With permissions to create app registrations
- **Python 3.11**: Backend development
- **Node.js 18+**: Frontend development
- **Azure CLI**: For creating Entra resources
- **Terraform**: For IaC setup (optional for dev)

---

## Step 1: Create Entra ID App Registrations

### Option A: Using Azure CLI (Quickest for Dev)

```bash
#!/bin/bash

# Set variables
TENANT_ID="your-tenant-id"          # Get from Azure Portal > Azure Active Directory > Properties
SUBSCRIPTION_ID="your-subscription" # Get from Azure Portal
REDIRECT_URI="http://localhost:3000/auth/callback"
API_SCOPE_URI="api://localhost-api"

# 1. Create SPA app registration
SPA_APP_ID=$(az ad app create \
  --display-name "azure-ai-poc-spa-dev" \
  --query appId -o tsv)

echo "SPA App ID: $SPA_APP_ID"

# 2. Create API app registration
API_APP_ID=$(az ad app create \
  --display-name "azure-ai-poc-api-dev" \
  --identifier-uris "$API_SCOPE_URI" \
  --query appId -o tsv)

echo "API App ID: $API_APP_ID"

# 3. Add redirect URI to SPA
az ad app update \
  --id $SPA_APP_ID \
  --web-redirect-uris "$REDIRECT_URI"

# 4. Create service principals
az ad sp create --id $SPA_APP_ID
az ad sp create --id $API_APP_ID

# 5. Add API scope to API app
SCOPE_ID=$(uuidgen)
az ad app update --id $API_APP_ID \
  --api-add-permission "$API_APP_ID/admin" \
  --api-known-client-applications $SPA_APP_ID

echo "Setup complete. Use these IDs in your .env files:"
echo "ENTRA_TENANT_ID=$TENANT_ID"
echo "ENTRA_CLIENT_ID_SPA=$SPA_APP_ID"
echo "ENTRA_CLIENT_ID_API=$API_APP_ID"
echo "REDIRECT_URI=$REDIRECT_URI"
```

### Option B: Using Terraform (for CI/CD)

See `infra/modules/entra-id/main.tf` for full infrastructure-as-code setup.

---

## Step 2: Backend Configuration

### 1. Update Environment Variables

**File**: `api-ms-agent/.env`

```bash
# Entra ID Configuration
ENTRA_ENABLED=true
ENTRA_TENANT_ID=11111111-1111-1111-1111-111111111111
ENTRA_CLIENT_ID=22222222-2222-2222-2222-222222222222
ENTRA_AUTHORITY=https://login.microsoftonline.com/11111111-1111-1111-1111-111111111111/v2.0
ENTRA_JWKS_URI=https://login.microsoftonline.com/11111111-1111-1111-1111-111111111111/discovery/v2.0/keys

# Keycloak Configuration (for coexistence testing)
KEYCLOAK_ENABLED=true
KEYCLOAK_URL=https://dev.loginproxy.gov.bc.ca/auth
KEYCLOAK_REALM=standard
KEYCLOAK_CLIENT_ID=azure-poc-6086

# Feature flags
FEATURE_ENTRA_ID_ENABLED=true
FEATURE_KEYCLOAK_ENABLED=true
```

### 2. Update Auth Service

**File**: `api-ms-agent/app/auth/service.py`

Refactor to support multiple token issuers:

```python
from app.config import settings
from typing import Optional
from app.auth.models import EntraUser, KeycloakUser
import httpx
import jwt

class JWTAuthService:
    """Unified JWT auth service supporting multiple issuers."""
    
    def __init__(self):
        self.entra_config = {
            "authority": settings.entra_authority,
            "client_id": settings.entra_client_id,
            "jwks_uri": settings.entra_jwks_uri,
            "enabled": settings.feature_entra_id_enabled,
        }
        self.keycloak_config = {
            "authority": settings.keycloak_url,
            "realm": settings.keycloak_realm,
            "client_id": settings.keycloak_client_id,
            "jwks_uri": f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/certs",
            "enabled": settings.feature_keycloak_enabled,
        }
        self._jwks_cache = {}
    
    async def validate_token(self, token: str) -> Optional[EntraUser]:
        """Validate token from either Entra ID or Keycloak."""
        try:
            # Get unverified claims to determine issuer
            unverified = jwt.decode(token, options={"verify_signature": False})
            issuer = unverified.get("iss", "")
            
            if "login.microsoftonline.com" in issuer and self.entra_config["enabled"]:
                return await self._validate_entra_token(token)
            elif "dev.loginproxy.gov.bc.ca" in issuer and self.keycloak_config["enabled"]:
                return await self._validate_keycloak_token(token)
            else:
                raise ValueError(f"Unknown or disabled issuer: {issuer}")
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return None
    
    async def _validate_entra_token(self, token: str) -> EntraUser:
        """Validate Entra ID token."""
        jwks = await self._get_jwks(self.entra_config["jwks_uri"])
        # Decode and validate signature
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=self.entra_config["client_id"],
            issuer=self.entra_config["authority"],
        )
        return EntraUser(
            object_id=payload["oid"],
            email=payload.get("email"),
            display_name=payload.get("name"),
            groups=payload.get("groups", []),
        )
    
    async def _get_jwks(self, jwks_uri: str):
        """Fetch and cache JWKS."""
        if jwks_uri not in self._jwks_cache:
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_uri)
                self._jwks_cache[jwks_uri] = response.json()
        return self._jwks_cache[jwks_uri]
```

### 3. Create Role Mapping

**File**: `api-ms-agent/app/auth/role_mapping.py`

```python
from typing import Dict, List

ROLE_MAPPING: Dict[str, str] = {
    "11111111-1111-1111-1111-111111111111": "admin",        # Entra group → app role
    "22222222-2222-2222-2222-222222222222": "document_reviewer",
    "33333333-3333-3333-3333-333333333333": "guest",
}

def map_groups_to_roles(groups: List[str]) -> List[str]:
    """Map Entra security groups to application roles."""
    roles = set()
    for group_id in groups:
        if group_id in ROLE_MAPPING:
            roles.add(ROLE_MAPPING[group_id])
    return list(roles) if roles else ["guest"]  # Default: guest if no mapping
```

### 4. Update Dependency Injection

**File**: `api-ms-agent/app/auth/dependencies.py`

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from app.auth.service import JWTAuthService
from app.auth.role_mapping import map_groups_to_roles

security = HTTPBearer()
auth_service = JWTAuthService()

async def get_current_user(credentials: HTTPAuthCredentials = Depends(security)):
    """Dependency: Get current authenticated user."""
    user = await auth_service.validate_token(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    # Map groups to roles
    user.roles = map_groups_to_roles(user.groups)
    return user

def require_role(role: str):
    """Dependency: Require user to have specific role."""
    async def check_role(user = Depends(get_current_user)):
        if role not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: requires '{role}' role",
            )
        return user
    return check_role
```

### 5. Use in Endpoints

**Example**: `api-ms-agent/app/routers/documents.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from app.auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/documents", tags=["documents"])

@router.get("/")
async def list_documents(user = Depends(get_current_user)):
    """List documents visible to user."""
    # User authenticated; return their documents
    return {"user": user.email, "documents": []}

@router.post("/{doc_id}/approve")
async def approve_document(doc_id: str, user = Depends(require_role("document_reviewer"))):
    """Approve document (requires document_reviewer role)."""
    return {"approved": True, "approved_by": user.email}
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
VITE_REDIRECT_URI=http://localhost:3000/auth/callback
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
            "groups": ["11111111-1111-1111-1111-111111111111"],
        },
        "secret",
        algorithm="HS256",
    )
    
    # Validate
    user = await auth_service.validate_token(test_token)
    assert user.email == "user@bcgov.ca"
    assert "11111111-1111-1111-1111-111111111111" in user.groups
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

### Groups Not in Token

1. **Check optional claims**: Add `groups` to optional claims in app registration
2. **Check user assignment**: Verify user is assigned to security groups in Entra

### CORS Issues

Add frontend origin to API app registration redirect URIs:

```bash
az ad app update --id $API_APP_ID --web-redirect-uris "http://localhost:3000"
```

---

## Next Steps

1. Run integration tests in CI/CD
2. Migrate test users to Entra groups
3. Canary rollout: enable for 10% of users
4. Monitor auth-related errors in Application Insights
5. Gradual cutover: disable Keycloak after 30-day coexistence period

