# Entra ID automation scripts

These scripts automate Microsoft Entra ID (Azure AD) setup for this repo.

They do not run automatically as part of Terraform or app startup. Nothing changes in your tenant unless you run them.

## Prereqs

- Azure CLI installed (`az`)
- Logged in (`az login`)
- `jq` installed (for JSON manipulation)
- Sufficient Entra permissions to create app registrations

Notes:
- These scripts operate on the tenant currently selected in your Azure CLI login context.
- If you work with multiple tenants, prefer logging in explicitly to the target tenant first:
	```bash
	az login --tenant "6fdb5200-3d0d-4a8a-b036-d3685e359adc" --use-device-code \
		--scope "https://graph.microsoft.com//.default"
	```
- For enterprise tenants with Conditional Access, you may need to re-login periodically.

## Quick start (roles-only, no groups)

This workflow assigns app roles **directly to users** without needing to create security groups.

### Step 1: Create app registrations

```bash
cd infra/scripts/entra

# Ensure scripts are executable and have LF line endings
chmod +x *.sh
sed -i 's/\r$//' *.sh  # or: dos2unix *.sh

# Create app registrations (SPA + API + service-to-service)
# Default roles: ai-poc-participant (users), api.access (services)
./create-entra-apps.sh \
	--tenant-id "<tenant-guid>" \
	--app-prefix "azure-ai-poc" \
	--spa-app-name "azure-ai-poc-spa" \
	--api-app-name "azure-ai-poc-api" \
	--s2s-app-name "azure-ai-poc-s2s" \
	--spa-redirect-uri "http://localhost:5173/"

# Or with custom roles for fine-grained access control:
./create-entra-apps.sh \
	--tenant-id "<tenant-guid>" \
	--app-prefix "azure-ai-poc" \
	--spa-app-name "azure-ai-poc-spa" \
	--api-app-name "azure-ai-poc-api" \
	--s2s-app-name "azure-ai-poc-s2s" \
	--spa-redirect-uri "http://localhost:5173/" \
	--user-roles-csv "reader:Data Reader,writer:Data Writer,admin:Administrator"
```

**Save the output!** You'll need `ENTRA_SPA_CLIENT_ID` and `ENTRA_API_CLIENT_ID` for your frontend config.

### Step 2: Assign users to the API

Users get assigned to roles on the **API app**, not the SPA. The SPA is just the client that requests tokens.

```bash
# Assign yourself (or other users) to the API
./assign-roles-to-users.sh \
	--api-app-name "azure-ai-poc-api" \
	--role-value "ai-poc-participant" \
	--users-csv "your.email@domain.com"
```

### Step 2b: Assign service clients (client credentials) to the API

Service-to-service clients (daemon apps) don’t use delegated scopes (`scp`) for authorization.
Instead, Entra issues **application roles** in the `roles` claim when you use the client credentials flow.

This repo’s default service role is `api.access` (created by `create-entra-apps.sh`).

```bash
# Assign the s2s client app to the API role (client credentials)
./assign-roles-to-service-clients.sh \
  --api-app-name "azure-ai-poc-api" \
  --role-value "api.access" \
  --clients-csv "azure-ai-poc-s2s"
```

### Step 3: Configure your frontend

Update your frontend's environment config with the values from Step 1:

```env
VITE_ENTRA_CLIENT_ID=<ENTRA_SPA_CLIENT_ID from step 1>
VITE_ENTRA_AUTHORITY=https://login.microsoftonline.com/<tenant-id>
VITE_API_SCOPES=api://<ENTRA_API_CLIENT_ID>/access_as_user
```

### Step 4: Configure your backend

Update your backend's environment config:

```env
ENTRA_TENANT_ID=<tenant-id>
# Use the Application ID URI format (api:// prefix) - this matches the token's aud claim
ENTRA_CLIENT_ID=api://<ENTRA_API_CLIENT_ID from step 1>
ENTRA_ENABLED=true
```

> **Important**: The backend `ENTRA_CLIENT_ID` must use the `api://` prefix (Application ID URI format)
> because Entra access tokens for custom APIs have `aud` set to `api://<client-id>`, not the raw GUID.

### How it works

```
┌─────────┐     ┌─────────────┐     ┌──────────┐     ┌──────────┐
│  User   │────▶│  SPA App    │────▶│  Entra   │────▶│ Your API │
│(browser)│     │  (client)   │     │   ID     │     │(resource)│
└─────────┘     └─────────────┘     └──────────┘     └──────────┘
                      │                   │                │
                      │ 1. User signs in  │                │
                      │───────────────────▶                │
                      │                   │                │
                      │ 2. Token issued   │                │
                      │   aud=API         │                │
                      │   roles=[...]     │                │
                      │◀───────────────────                │
                      │                                    │
                      │ 3. Call API with Bearer token      │
                      │────────────────────────────────────▶
```

- **SPA** = the client app (frontend) - users sign in here
- **API** = the resource app (backend) - has roles defined
- **Roles** are assigned to users on the **API's Enterprise Application**
- When a user signs in via the SPA and requests a token for the API, the token includes their roles

---

## Role-Based Endpoint Security

App Roles replace security groups for access control. Instead of checking "is user in group X?", you check "does user have role X?".

### Understanding App Roles

| Concept | Description |
|---------|-------------|
| **App Role** | A permission defined on your API (e.g., `reader`, `writer`, `admin`) |
| **Role assignment** | Granting a user (or service) a specific role |
| **Roles claim** | Array of role values in the JWT token |

**Key insight**: Roles are binary — a user either has a role or doesn't. For granular permissions, create multiple roles.

### Example: Multiple Roles for Different Access Levels

```
API App Registration: azure-ai-poc-api
└── App Roles:
    ├── reader          → Can view data
    ├── writer          → Can view and modify data
    ├── admin           → Full access including user management
    └── api.access      → For service-to-service (client credentials)
```

### Adding Custom Roles

#### Option 1: Azure Portal

1. Go to **App registrations** → your API app → **App roles**
2. Click **Create app role**
3. Fill in:
   - **Display name**: `Data Reader`
   - **Value**: `reader` (this appears in the token)
   - **Allowed member types**: `Users/Groups`
   - **Description**: `Can read data from the API`
4. Click **Apply**

Repeat for each role you need.

#### Option 2: Azure CLI / Graph API

```bash
# Get the current app manifest
api_app_id="<your-api-client-id>"
api_object_id=$(az ad app show --id "$api_app_id" --query id -o tsv)

# Add a new role (must include ALL existing roles + new one)
az rest --method PATCH \
  --uri "https://graph.microsoft.com/v1.0/applications/$api_object_id" \
  --headers "Content-Type=application/json" \
  --body '{
    "appRoles": [
      {
        "allowedMemberTypes": ["User"],
        "description": "Can read data from the API",
        "displayName": "Data Reader",
        "id": "'$(uuidgen)'",
        "isEnabled": true,
        "value": "reader"
      },
      {
        "allowedMemberTypes": ["User"],
        "description": "Can read and modify data",
        "displayName": "Data Writer",
        "id": "'$(uuidgen)'",
        "isEnabled": true,
        "value": "writer"
      },
      {
        "allowedMemberTypes": ["User"],
        "description": "Full administrative access",
        "displayName": "Administrator",
        "id": "'$(uuidgen)'",
        "isEnabled": true,
        "value": "admin"
      },
      {
        "allowedMemberTypes": ["Application"],
        "description": "Service-to-service access",
        "displayName": "API Access",
        "id": "'$(uuidgen)'",
        "isEnabled": true,
        "value": "api.access"
      }
    ]
  }'
```

### Assigning Roles to Users

```bash
# Assign multiple roles to a user
./assign-roles-to-users.sh \
  --api-app-name "azure-ai-poc-api" \
  --role-value "reader" \
  --users-csv "alice@contoso.com"

./assign-roles-to-users.sh \
  --api-app-name "azure-ai-poc-api" \
  --role-value "writer" \
  --users-csv "bob@contoso.com"

./assign-roles-to-users.sh \
  --api-app-name "azure-ai-poc-api" \
  --role-value "admin" \
  --users-csv "charlie@contoso.com"
```

A user can have **multiple roles**. Run the script once per role.

### Protecting Endpoints in FastAPI

The JWT token includes a `roles` claim:

```json
{
  "aud": "api://your-api-client-id",
  "iss": "https://login.microsoftonline.com/your-tenant-id/v2.0",
  "sub": "user-object-id",
  "roles": ["reader", "writer"],
  "...": "..."
}
```

#### Basic Role Check

```python
from fastapi import Depends, HTTPException, status
from typing import List

def require_roles(required_roles: List[str]):
    """Dependency that checks if user has ANY of the required roles."""
    def check_roles(token_data: dict = Depends(get_current_user)):
        user_roles = token_data.get("roles", [])
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {required_roles}"
            )
        return token_data
    return check_roles

# Read-only endpoint - requires reader OR writer OR admin
@app.get("/api/data")
async def get_data(user: dict = Depends(require_roles(["reader", "writer", "admin"]))):
    return {"data": "..."}

# Write endpoint - requires writer OR admin
@app.post("/api/data")
async def create_data(user: dict = Depends(require_roles(["writer", "admin"]))):
    return {"created": True}

# Admin-only endpoint
@app.delete("/api/users/{user_id}")
async def delete_user(user_id: str, user: dict = Depends(require_roles(["admin"]))):
    return {"deleted": user_id}
```

#### Role Hierarchy Pattern

```python
from enum import IntEnum

class Role(IntEnum):
    """Roles ordered by privilege level."""
    READER = 1
    WRITER = 2
    ADMIN = 3

ROLE_VALUES = {
    "reader": Role.READER,
    "writer": Role.WRITER,
    "admin": Role.ADMIN,
}

def require_min_role(min_role: Role):
    """Require at least this role level (includes higher roles)."""
    def check_role(token_data: dict = Depends(get_current_user)):
        user_roles = token_data.get("roles", [])
        user_max_role = max(
            (ROLE_VALUES.get(r, Role.READER) for r in user_roles),
            default=Role.READER
        )
        if user_max_role < min_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires at least {min_role.name.lower()} role"
            )
        return token_data
    return check_role

# Any authenticated user with reader+ role
@app.get("/api/reports")
async def get_reports(user: dict = Depends(require_min_role(Role.READER))):
    return {"reports": []}

# Writer or higher
@app.post("/api/reports")
async def create_report(user: dict = Depends(require_min_role(Role.WRITER))):
    return {"created": True}

# Admin only
@app.get("/api/audit-log")
async def get_audit_log(user: dict = Depends(require_min_role(Role.ADMIN))):
    return {"logs": []}
```

### Fine-Grained Permissions Within Roles

If you need permissions more granular than roles (e.g., "can edit project X but not project Y"), you have two options:

#### Option A: More Granular Roles (Recommended for Simple Cases)

Create specific roles:
- `project-alpha-reader`
- `project-alpha-writer`
- `project-beta-reader`
- `project-beta-writer`

#### Option B: Custom Permission Layer (For Complex Cases)

Store permissions in your database, keyed by user ID from the token:

```python
@app.get("/api/projects/{project_id}")
async def get_project(
    project_id: str,
    user: dict = Depends(require_roles(["reader", "writer", "admin"]))
):
    user_id = user["sub"]  # User's object ID from token
    
    # Check your database for project-specific permissions
    if not await has_project_access(user_id, project_id, "read"):
        raise HTTPException(status_code=403, detail="No access to this project")
    
    return await get_project_data(project_id)
```

### Summary: Roles vs Groups vs Permissions

| Approach | Managed In | Best For |
|----------|-----------|----------|
| **App Roles** | Entra ID | Coarse access control (reader/writer/admin) |
| **Security Groups** | Entra ID | Not available (restricted in your tenant) |
| **Custom Permissions** | Your database | Fine-grained, resource-level access |

**Recommendation**: Start with 3-5 App Roles for major access levels, add custom permissions in your database only if needed for resource-level access control.

---

## Multiple environments (recommended)

If you manage multiple environments in the same tenant (e.g., `dev`, `test`, `prod`),
use an environment suffix in **every** name you pass in.

Recommended naming pattern:
- `--app-prefix "<base>-<env>"`
- `--spa-app-name "<base>-<env>-spa"`
- `--api-app-name "<base>-<env>-api"`
- `--s2s-app-name "<base>-<env>-s2s"`

This avoids collisions and keeps app registrations clearly attributable.

### Bash example

```bash
env="dev"
base="azure-ai-poc"
prefix="$base-$env"

cd infra/scripts/entra

./create-entra-apps.sh \
	--tenant-id "<tenant-guid>" \
	--app-prefix "$prefix" \
	--spa-app-name "$prefix-spa" \
	--api-app-name "$prefix-api" \
	--s2s-app-name "$prefix-s2s" \
	--spa-redirect-uri "http://localhost:5173/" \
	--spa-redirect-uri "https://dev.contoso.com/auth/callback"

./assign-roles-to-users.sh \
	--api-app-name "$prefix-api" \
	--role-value "ai-poc-participant" \
	--users-csv "alice@contoso.com"
```

## Configuration

These scripts do not assume any defaults. All required parameters must be provided as CLI flags.

Tip:
- If you want “defaults”, implement them in your wrapper (Makefile, PowerShell script, CI pipeline),
  not inside these scripts.

## Manual setup (Azure portal)

If you prefer (or need) to manage roles/groups manually, here’s the portal flow that matches what
these scripts automate.

### 1) Create/update App Roles on the API app registration

App Roles live on the **API app registration** (the “resource” app).

1. Go to **Microsoft Entra admin center** → **Identity** → **Applications** → **App registrations**.
2. Open your **API app registration** (example: `azure-ai-poc-dev-api`).
3. Go to **App roles** → **Create app role**.
4. Create roles that match your authorization model.

Recommended examples (aligned with the scripts):
- User role:
	- **Display name**: `AI POC Participant`
	- **Value**: `ai-poc-participant`
	- **Allowed member types**: `Users/Groups`
- Application role (client credentials):
	- **Display name**: `API Access (Client Credentials)`
	- **Value**: `api.access`
	- **Allowed member types**: `Applications`

Save the roles.

### 2) (Optional) Expose an API scope for SPA delegated access

If your SPA will call the API “on behalf of the signed-in user”, you typically add an API scope.

1. In the same **API app registration**, go to **Expose an API**.
2. Set an **Application ID URI** (commonly `api://<api-client-id>`).
3. Add a scope such as:
	 - **Scope name**: `access_as_user`
	 - Enable it, and provide user/admin consent descriptions.

### 3) Assign users directly to app roles (Enterprise application)

The assignment happens on the **Enterprise application** (service principal), not on App registrations.

1. Go to **Microsoft Entra admin center** → **Identity** → **Applications** → **Enterprise applications**.
2. Find and open the Enterprise application for your **API app** (same display name, e.g. `azure-ai-poc-dev-api`).
3. Go to **Users and groups** → **Add user/group**.
4. Select the **User**, then select the **Role** (the App Role value you created).
5. Save.

Result:
- The user will receive the role in the token (in the `roles` claim for app roles).

### Notes / troubleshooting

- If you don't see "Roles" when assigning a user to the Enterprise application, confirm:
	- The App Role exists on the **API App registration**.
	- The role is **Enabled**.
	- "Allowed member types" includes `Users/Groups`.
- Role assignments can take a short time to propagate into tokens.

---

## Security: Access Control for API Owners

This section explains how to control who can access your API when other apps (SPAs, services) want to call it.

### How It Works: Two Types of API Access

#### 1. Delegated Access (SPA/Browser → API)

User signs in to a client app, which calls your API **on behalf of the user**.

```
┌─────────┐     ┌─────────────┐     ┌──────────┐     ┌──────────┐
│  User   │────▶│  SPA App    │────▶│  Entra   │────▶│ Your API │
│(browser)│     │(frontend)   │     │   ID     │     │          │
└─────────┘     └─────────────┘     └──────────┘     └──────────┘
```

**Token claims**:
- `aud` = your API's client ID
- `scp` = `access_as_user` (delegated scope)
- `roles` = `["ai-poc-participant"]` (user's assigned role)
- `sub` = user's object ID

#### 2. Application Access (Service → API)

A background service or another API authenticates with client credentials (no user).

```
┌──────────────┐     ┌──────────┐     ┌──────────┐
│ Service App  │────▶│  Entra   │────▶│ Your API │
│ (daemon/API) │     │   ID     │     │          │
└──────────────┘     └──────────┘     └──────────┘
```

**Token claims**:
- `aud` = your API's client ID
- `roles` = `["api.access"]` (application role)
- `sub` = service principal object ID
- **No user context** (no `scp`, no user info)

---

### Your API's Security Configuration

When `create-entra-apps.sh` runs, it configures your API with:

```
API App Registration: azure-ai-poc-api
├── Application ID URI: api://<api-client-id>
├── Exposed Scopes:
│   └── access_as_user (Admin consent required)
└── App Roles:
    ├── ai-poc-participant (for users)
    └── api.access (for applications)
```

---

### Access Control Gates

There are **two gates** that control API access:

| Gate | What It Controls | Who Sets It |
|------|------------------|-------------|
| **1. Consent** | Can a client app request tokens for your API? | Tenant admin grants consent |
| **2. Assignment** | Can a specific user/service get a token? | API owner assigns roles |

#### Gate 1: Admin Consent (Client App Permission)

Before a client app can get tokens for your API, an admin must **grant consent**.

The `access_as_user` scope is configured with `type: Admin`, meaning:
- Users **cannot** consent themselves
- A tenant admin must explicitly approve

**To grant consent for a client app**:
1. Go to **Enterprise applications** → find the client app
2. **Permissions** → **Grant admin consent for [tenant]**

#### Gate 2: User/Service Assignment

Even with consent, users must be **assigned to a role** on your API's Enterprise Application.

**To enable assignment requirement**:
1. Go to **Enterprise applications** → your API app (e.g., `azure-ai-poc-api`)
2. **Properties** → **Assignment required?** → **Yes**

With this enabled:
- ✅ Assigned users → get tokens with roles
- ❌ Unassigned users → token request fails

---

### Complete Access Control Matrix

| Control Point | Setting | Effect |
|---------------|---------|--------|
| **Scope type** | `Admin` | Client apps need admin consent |
| **Assignment required** | `Yes` | Users need explicit role assignment |
| **Grant admin consent** | Per client app | Allows that client to request tokens |
| **Assign user to role** | Per user | User gets `roles` claim in token |

---

### Example: New Client App Wants API Access

**Scenario**: Developer "Alice" builds a new SPA (`alice-dashboard`) that needs to call your API.

#### Step 1: Alice registers her app

```
App Registration: alice-dashboard-spa
├── Redirect URI: http://localhost:4200/
└── API Permissions: (none yet)
```

#### Step 2: Alice requests your API permission

In **alice-dashboard-spa** → **API permissions** → **Add permission**:
1. Select **"My APIs"** or **"APIs my organization uses"**
2. Find `azure-ai-poc-api`
3. Select `access_as_user`
4. Click **Add permissions**

**Status**: Permission requested but NOT granted

```
API Permissions:
│ azure-ai-poc-api / access_as_user │ ⚠️ Admin consent required │
```

#### Step 3: Alice asks you (API owner) for access

Alice contacts you to request access for her app.

#### Step 4: You (or tenant admin) grant consent

1. Go to **Enterprise applications** → `alice-dashboard-spa`
2. **Permissions** → **Grant admin consent for [tenant]**

**Status**: Consent granted

```
API Permissions:
│ azure-ai-poc-api / access_as_user │ ✅ Granted for [tenant] │
```

#### Step 5: Assign Alice's users to your API

Even with consent, users need role assignments to access your API:

```bash
./assign-roles-to-users.sh \
  --api-app-name "azure-ai-poc-api" \
  --role-value "ai-poc-participant" \
  --users-csv "alice@contoso.com,alice-team@contoso.com"
```

#### Step 6: Alice's SPA can now call your API ✅

---

### Granting Access to Service/Daemon Apps

For service-to-service (client credentials) access:

#### 1. The service app needs its own App Registration with a client secret

#### 2. Assign the `api.access` role to the service's Service Principal

```bash
# Get the service app's Service Principal ID
service_sp_id=$(az ad sp list --filter "appId eq '<SERVICE_APP_ID>'" --query "[0].id" -o tsv)

# Get your API's Service Principal ID
api_sp_id=$(az ad sp list --filter "appId eq '<API_APP_ID>'" --query "[0].id" -o tsv)

# Get the api.access role ID from your API
role_id=$(az ad app show --id "<API_APP_ID>" --query "appRoles[?value=='api.access'].id | [0]" -o tsv)

# Assign the role
az rest --method POST \
  --uri "https://graph.microsoft.com/v1.0/servicePrincipals/${service_sp_id}/appRoleAssignments" \
  --headers "Content-Type=application/json" \
  --body "$(jq -n \
    --arg principalId "$service_sp_id" \
    --arg resourceId "$api_sp_id" \
    --arg appRoleId "$role_id" \
    '{principalId: $principalId, resourceId: $resourceId, appRoleId: $appRoleId}')"
```

---

### Security Summary

Your API is protected by:

1. **Signature validation** - Tokens must be signed by Microsoft's keys
2. **Issuer validation** - Tokens must come from your tenant
3. **Audience validation** - Tokens must be issued for your API's client ID
4. **Admin consent** - Client apps need explicit admin approval
5. **Role assignment** - Users/services need explicit role assignments
6. **Role-based access control** - Your API can check roles in the token

**An attacker cannot:**
- Forge tokens (no access to Microsoft's signing keys)
- Use tokens from their own app (audience mismatch)
- Use tokens from a different tenant (issuer mismatch)
- Access without consent (admin must approve)
- Access without assignment (role assignment required)
