#!/usr/bin/env bash
# Assign app roles directly to service principals (client applications)
# Intended for service-to-service (client credentials) callers.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_entra_lib.sh"

require_cmd az
require_cmd jq
az_login_check

usage() {
  cat <<'USAGE' >&2
Usage:
  ./assign-roles-to-service-clients.sh \
    --api-app-name <display-name> \
    --role-value <role> \
    --clients-csv <client1,client2,...>

Where --clients-csv entries may be either:
  - Client app display names (preferred), or
  - Client app application (client) IDs (GUID)

Example (by display name):
  ./assign-roles-to-service-clients.sh \
    --api-app-name azure-ai-poc-api \
    --role-value api.access \
    --clients-csv "azure-ai-poc-s2s"

Example (by appId GUID):
  ./assign-roles-to-service-clients.sh \
    --api-app-name azure-ai-poc-api \
    --role-value api.access \
    --clients-csv "00000000-0000-0000-0000-000000000000"

Notes:
  - Assigns application roles to the *client application's* service principal.
  - The API app must already define the appRole (e.g., api.access).
  - The client application must have a service principal in the tenant; this script will create it if missing.
USAGE
}

api_app_name=""
role_value=""
clients_csv=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-app-name)
      api_app_name="${2:-}"; shift 2 ;;
    --role-value)
      role_value="${2:-}"; shift 2 ;;
    --clients-csv)
      clients_csv="${2:-}"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

[[ -n "$api_app_name" ]] || { usage; die "--api-app-name is required"; }
[[ -n "$role_value" ]] || { usage; die "--role-value is required"; }
[[ -n "$clients_csv" ]] || { usage; die "--clients-csv is required"; }

# Get API app info
api_app_id=$(az ad app list --display-name "$api_app_name" --query "[0].appId" -o tsv --only-show-errors 2>/dev/null | tr -d '\r' || true)
if [[ -z "$api_app_id" ]]; then
  echo "ERROR: API app not found: $api_app_name" >&2
  echo "Hint: run ./create-entra-apps.sh first." >&2
  exit 1
fi

api_app_object_id=$(get_app_object_id "$api_app_id")
api_sp_object_id=$(get_or_create_sp_object_id "$api_app_id")

# Get the app role ID from the API app registration
role_id=$(az rest --method GET \
  --uri "https://graph.microsoft.com/v1.0/applications/$api_app_object_id" \
  --query "appRoles[?value=='$role_value'].id | [0]" -o tsv --only-show-errors 2>/dev/null | tr -d '\r' || true)

if [[ -z "$role_id" ]]; then
  echo "ERROR: App role not found on API app: $role_value" >&2
  echo "Hint: ensure ./create-entra-apps.sh completed successfully (it creates 'api.access' by default)." >&2
  exit 1
fi

echo "Assigning role '$role_value' to service clients on $api_app_name..." >&2

is_guid() {
  # Rough GUID check: 8-4-4-4-12 hex
  [[ "$1" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]
}

IFS=',' read -r -a clients <<< "$clients_csv"
for client in "${clients[@]}"; do
  client="$(echo "$client" | xargs | tr -d '\r')"
  [[ -z "$client" ]] && continue

  client_app_id=""
  if is_guid "$client"; then
    client_app_id="$client"
  else
    client_app_id=$(az ad app list --display-name "$client" --query "[0].appId" -o tsv --only-show-errors 2>/dev/null | tr -d '\r' || true)
  fi

  if [[ -z "$client_app_id" ]]; then
    echo "WARN: client app not found: $client" >&2
    continue
  fi

  client_sp_object_id=$(get_or_create_sp_object_id "$client_app_id")

  # Check if assignment already exists
  existing=$(az rest --method GET \
    --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$client_sp_object_id/appRoleAssignments" \
    --query "value[?resourceId=='$api_sp_object_id' && appRoleId=='$role_id'] | length(@)" \
    -o tsv --only-show-errors 2>/dev/null | tr -d '\r' || echo "0")

  if [[ "$existing" != "0" ]]; then
    echo "found existing assignment: $client -> $role_value" >&2
    continue
  fi

  body=$(jq -n \
    --arg principalId "$client_sp_object_id" \
    --arg resourceId "$api_sp_object_id" \
    --arg appRoleId "$role_id" \
    '{ principalId: $principalId, resourceId: $resourceId, appRoleId: $appRoleId }')

  az rest --method POST \
    --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$client_sp_object_id/appRoleAssignments" \
    --headers "Content-Type=application/json" \
    --body "$body" \
    --only-show-errors >/dev/null

  echo "assigned: $client -> $role_value" >&2
done

echo "Done." >&2
