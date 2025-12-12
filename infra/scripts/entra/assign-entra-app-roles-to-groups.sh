#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_entra_lib.sh"

require_cmd az
require_cmd python
az_login_check

usage() {
  cat <<'USAGE' >&2
Usage:
  ./assign-entra-app-roles-to-groups.sh \
    --app-prefix <prefix> \
    --api-app-name <display-name> \
    --role-values-csv <csv>

Example:
  ./assign-entra-app-roles-to-groups.sh --app-prefix azure-ai-poc --api-app-name azure-ai-poc-api --role-values-csv "ai-poc-participant"

Notes:
  - No defaults are assumed; all parameters must be provided.
  - The API app must already have appRoles matching the role values.
USAGE
}

app_prefix=""
api_app_name=""
role_values_csv=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-prefix)
      app_prefix="${2:-}"; shift 2 ;;
    --api-app-name)
      api_app_name="${2:-}"; shift 2 ;;
    --role-values-csv)
      role_values_csv="${2:-}"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

[[ -n "$app_prefix" ]] || { usage; die "--app-prefix is required"; }
[[ -n "$api_app_name" ]] || { usage; die "--api-app-name is required"; }
[[ -n "$role_values_csv" ]] || { usage; die "--role-values-csv is required"; }

APP_PREFIX="$app_prefix"
API_APP_NAME="$api_app_name"
ROLE_VALUES_CSV="$role_values_csv"

api_app_id=$(az ad app list --display-name "$API_APP_NAME" --query "[0].appId" -o tsv --only-show-errors || true)
if [[ -z "$api_app_id" ]]; then
  echo "ERROR: API app not found: $API_APP_NAME" >&2
  echo "Hint: run infra/scripts/create-entra-apps.sh first." >&2
  exit 1
fi

api_app_object_id=$(get_app_object_id "$api_app_id")
api_sp_object_id=$(get_or_create_sp_object_id "$api_app_id")

IFS=',' read -r -a role_values <<< "$ROLE_VALUES_CSV"

for role_value in "${role_values[@]}"; do
  role_value="$(echo "$role_value" | xargs)"
  [[ -z "$role_value" ]] && continue

  group_name="${APP_PREFIX}-${role_value}"
  group_id=$(az ad group list --filter "displayName eq '$group_name'" --query "[0].id" -o tsv --only-show-errors || true)
  if [[ -z "$group_id" ]]; then
    echo "ERROR: Group not found: $group_name" >&2
    echo "Hint: run infra/scripts/create-entra-groups.sh first." >&2
    exit 1
  fi

  role_id=$(az rest --method GET --uri "https://graph.microsoft.com/v1.0/applications/$api_app_object_id" --query "appRoles[?value=='$role_value'].id | [0]" -o tsv --only-show-errors || true)
  if [[ -z "$role_id" ]]; then
    echo "ERROR: App role not found on API app: $role_value" >&2
    echo "Hint: ensure infra/scripts/create-entra-apps.sh completed successfully." >&2
    exit 1
  fi

  # Idempotency: check existing assignment
  existing=$(az rest --method GET --uri "https://graph.microsoft.com/v1.0/groups/$group_id/appRoleAssignments" --query "value[?resourceId=='$api_sp_object_id' && appRoleId=='$role_id'] | length(@)" -o tsv --only-show-errors || true)
  if [[ "$existing" != "0" ]]; then
    echo "found role assignment: $group_name -> $role_value" >&2
    continue
  fi

  body=$(python - <<PY
import json
print(json.dumps({
  "principalId": "${group_id}",
  "resourceId": "${api_sp_object_id}",
  "appRoleId": "${role_id}"
}))
PY
)

  az rest --method POST \
    --uri "https://graph.microsoft.com/v1.0/groups/$group_id/appRoleAssignments" \
    --headers "Content-Type=application/json" \
    --body "$body" \
    --only-show-errors >/dev/null

  echo "assigned role: $group_name -> $role_value" >&2
done
