# Entra ID automation scripts

These scripts automate Microsoft Entra ID (Azure AD) setup for this repo.

They do not run automatically as part of Terraform or app startup. Nothing changes in your tenant unless you run them.

## Prereqs

- Azure CLI installed (`az`)
- Logged in (`az login`)
- Sufficient Entra permissions to create app registrations and groups

Notes:
- These scripts operate on the tenant currently selected in your Azure CLI login context.
- If you work with multiple tenants, prefer logging in explicitly to the target tenant first:
	`az login --tenant <tenant-guid>`

## Quick start

```bash
cd infra/scripts/entra

# 1) Create app registrations (SPA + API + service-to-service)
./create-entra-apps.sh \
	--tenant-id "<tenant-guid>" \
	--app-prefix "azure-ai-poc" \
	--spa-app-name "azure-ai-poc-spa" \
	--api-app-name "azure-ai-poc-api" \
	--s2s-app-name "azure-ai-poc-s2s" \
	--spa-redirect-uri "http://localhost:5173/"

# 2) Create security groups for role values
./create-entra-groups.sh \
	--app-prefix "azure-ai-poc" \
	--role-values-csv "ai-poc-participant"

# 3) Assign API app roles to those groups
./assign-entra-app-roles-to-groups.sh \
	--app-prefix "azure-ai-poc" \
	--api-app-name "azure-ai-poc-api" \
	--role-values-csv "ai-poc-participant"

# 4) Add users (by UPN) to a role group
./add-users-to-groups.sh \
	--app-prefix "azure-ai-poc" \
	--role-value "ai-poc-participant" \
	--users-csv "alice@contoso.com,bob@contoso.com"
```

## Multiple environments (recommended)

If you manage multiple environments in the same tenant (e.g., `dev`, `test`, `prod`),
use an environment suffix in **every** name you pass in.

Recommended naming pattern:
- `--app-prefix "<base>-<env>"`
- `--spa-app-name "<base>-<env>-spa"`
- `--api-app-name "<base>-<env>-api"`
- `--s2s-app-name "<base>-<env>-s2s"`

This avoids collisions and keeps groups/app registrations clearly attributable.

### PowerShell example

```powershell
$envName = "dev"
$base = "azure-ai-poc"
$prefix = "$base-$envName"

cd infra/scripts/entra

./create-entra-apps.sh `
	--tenant-id "<tenant-guid>" `
	--app-prefix $prefix `
	--spa-app-name "$prefix-spa" `
	--api-app-name "$prefix-api" `
	--s2s-app-name "$prefix-s2s" `
	--spa-redirect-uri "http://localhost:5173/" `
	--spa-redirect-uri "https://dev.contoso.com/auth/callback"

./create-entra-groups.sh `
	--app-prefix $prefix `
	--role-values-csv "ai-poc-participant,api.access"

./assign-entra-app-roles-to-groups.sh `
	--app-prefix $prefix `
	--api-app-name "$prefix-api" `
	--role-values-csv "ai-poc-participant,api.access"
```

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

### 3) Create security groups for your roles

1. Go to **Microsoft Entra admin center** → **Identity** → **Groups** → **All groups**.
2. **New group** → **Security**.
3. Create groups that map to your role values (recommended naming):
	 - `<app-prefix>-ai-poc-participant`
	 - `<app-prefix>-api.access` (only if you intend to assign roles to groups for app access patterns)

### 4) Assign groups/users to the app role (Enterprise application)

The assignment happens on the **Enterprise application** (service principal), not on App registrations.

1. Go to **Microsoft Entra admin center** → **Identity** → **Applications** → **Enterprise applications**.
2. Find and open the Enterprise application for your **API app** (same display name usually, e.g. `azure-ai-poc-dev-api`).
3. Go to **Users and groups** → **Add user/group**.
4. Select the **Group** (or User), then select the **Role** (the App Role value you created).
5. Save.

Result:
- Members of that group will receive the role in the token (typically in the `roles` claim for app roles).

### 5) Add users to groups

1. **Groups** → open the group (e.g., `<app-prefix>-ai-poc-participant`).
2. **Members** → **Add members**.
3. Select users and save.

### Notes / troubleshooting

- If you don’t see “Roles” when assigning a group/user to the Enterprise application, confirm:
	- The App Role exists on the **API App registration**.
	- The role is **Enabled**.
	- “Allowed member types” includes the thing you’re assigning (Users/Groups vs Applications).
- Group membership changes can take a short time to propagate into tokens.
