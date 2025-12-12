# Entra ID automation scripts

These scripts automate Microsoft Entra ID (Azure AD) setup for this repo.

They do not run automatically as part of Terraform or app startup. Nothing changes in your tenant unless you run them.

## Prereqs

- Azure CLI installed (`az`)
- Logged in (`az login`)
- Sufficient Entra permissions to create app registrations and groups

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

## Configuration

These scripts do not assume any defaults. All required parameters must be provided as CLI flags.
