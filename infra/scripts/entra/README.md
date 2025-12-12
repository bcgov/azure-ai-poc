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
