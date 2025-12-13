#!/usr/bin/env bash
# Assign app roles directly to users (no groups required)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_entra_lib.sh"

require_cmd az
require_cmd jq
az_login_check

usage() {
  cat <<'USAGE' >&2
Usage:
  ./assign-roles-to-users.sh \
    --api-app-name <display-name> \
    --role-value <role> \
    --users-csv <upn1,upn2,...>

Example:
  ./assign-roles-to-users.sh \
    --api-app-name azure-ai-poc-tools-api \
    --role-value ai-poc-participant \
    --users-csv "alice@gov.bc.ca,bob@gov.bc.ca"

Notes:
  - Assigns users directly to app roles on the API's Enterprise Application.
  - No security groups required.
  - The API app must already have the appRole defined.
USAGE
}

api_app_name=""
role_value=""
users_csv=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-app-name)
      api_app_name="${2:-}"; shift 2 ;;
    --role-value)
      role_value="${2:-}"; shift 2 ;;
    --users-csv)
      users_csv="${2:-}"; shift 2 ;;
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
[[ -n "$users_csv" ]] || { usage; die "--users-csv is required"; }

# Get API app info
api_app_id=$(az ad app list --display-name "$api_app_name" --query "[0].appId" -o tsv --only-show-errors 2>/dev/null | tr -d '\r' || true)
if [[ -z "$api_app_id" ]]; then
  echo "ERROR: API app not found: $api_app_name" >&2
  echo "Hint: run ./create-entra-apps.sh first." >&2
  exit 1
fi

api_app_object_id=$(get_app_object_id "$api_app_id")
api_sp_object_id=$(get_or_create_sp_object_id "$api_app_id")

# Get the app role ID
role_id=$(az rest --method GET \
  --uri "https://graph.microsoft.com/v1.0/applications/$api_app_object_id" \
  --query "appRoles[?value=='$role_value'].id | [0]" -o tsv --only-show-errors 2>/dev/null | tr -d '\r' || true)

if [[ -z "$role_id" ]]; then
  echo "ERROR: App role not found: $role_value" >&2
  echo "Hint: ensure ./create-entra-apps.sh completed successfully." >&2
  exit 1
fi

echo "Assigning role '$role_value' to users on $api_app_name..." >&2

IFS=',' read -r -a users <<< "$users_csv"
for upn in "${users[@]}"; do
  upn="$(echo "$upn" | xargs | tr -d '\r')"
  [[ -z "$upn" ]] && continue

  # Get user object ID
  user_id=$(az ad user show --id "$upn" --query id -o tsv --only-show-errors 2>/dev/null | tr -d '\r' || true)
  if [[ -z "$user_id" ]]; then
    echo "WARN: user not found: $upn" >&2
    continue
  fi

  # Check if assignment already exists
  existing=$(az rest --method GET \
    --uri "https://graph.microsoft.com/v1.0/users/$user_id/appRoleAssignments" \
    --query "value[?resourceId=='$api_sp_object_id' && appRoleId=='$role_id'] | length(@)" \
    -o tsv --only-show-errors 2>/dev/null | tr -d '\r' || echo "0")

  if [[ "$existing" != "0" ]]; then
    echo "found existing assignment: $upn -> $role_value" >&2
    continue
  fi

  # Create the app role assignment
  body=$(jq -n \
    --arg principalId "$user_id" \
    --arg resourceId "$api_sp_object_id" \
    --arg appRoleId "$role_id" \
    '{ principalId: $principalId, resourceId: $resourceId, appRoleId: $appRoleId }')

  az rest --method POST \
    --uri "https://graph.microsoft.com/v1.0/users/$user_id/appRoleAssignments" \
    --headers "Content-Type=application/json" \
    --body "$body" \
    --only-show-errors >/dev/null

  echo "assigned: $upn -> $role_value" >&2
done

echo "Done." >&2
