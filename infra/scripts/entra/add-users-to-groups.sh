#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_entra_lib.sh"

require_cmd az
az_login_check

usage() {
  cat <<'USAGE' >&2
Usage:
  ./add-users-to-groups.sh \
    --app-prefix <prefix> \
    --role-value <role> \
    --users-csv <upn1,upn2,...>

Example:
  ./add-users-to-groups.sh --app-prefix azure-ai-poc --role-value ai-poc-participant --users-csv "alice@contoso.com,bob@contoso.com"

Notes:
  - No defaults are assumed; all parameters must be provided.
USAGE
}

app_prefix=""
role_value=""
users_csv=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-prefix)
      app_prefix="${2:-}"; shift 2 ;;
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

[[ -n "$app_prefix" ]] || { usage; die "--app-prefix is required"; }
[[ -n "$role_value" ]] || { usage; die "--role-value is required"; }
[[ -n "$users_csv" ]] || { usage; die "--users-csv is required"; }

APP_PREFIX="$app_prefix"
ROLE_VALUE="$role_value"
USERS_CSV="$users_csv"

group_name="${APP_PREFIX}-${ROLE_VALUE}"
group_id=$(az ad group list --filter "displayName eq '$group_name'" --query "[0].id" -o tsv --only-show-errors || true)
if [[ -z "$group_id" ]]; then
  echo "ERROR: Group not found: $group_name" >&2
  echo "Hint: run infra/scripts/create-entra-groups.sh first." >&2
  exit 1
fi

IFS=',' read -r -a users <<< "$USERS_CSV"
for upn in "${users[@]}"; do
  upn="$(echo "$upn" | xargs)"
  [[ -z "$upn" ]] && continue

  user_id=$(az ad user show --id "$upn" --query id -o tsv --only-show-errors || true)
  if [[ -z "$user_id" ]]; then
    echo "WARN: user not found: $upn" >&2
    continue
  fi

  az ad group member add --group "$group_id" --member-id "$user_id" --only-show-errors >/dev/null || true
  echo "added $upn to $group_name" >&2
done

echo "group_id=$group_id"
