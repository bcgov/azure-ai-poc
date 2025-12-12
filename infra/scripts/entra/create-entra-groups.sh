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
  ./create-entra-groups.sh \
    --app-prefix <prefix> \
    --role-values-csv <csv>

Example:
  ./create-entra-groups.sh --app-prefix azure-ai-poc --role-values-csv "ai-poc-participant,api.access"

Notes:
  - No defaults are assumed; all parameters must be provided.
  - Creates Entra security groups named: <app-prefix>-<role-value>
USAGE
}

app_prefix=""
role_values_csv=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-prefix)
      app_prefix="${2:-}"; shift 2 ;;
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
[[ -n "$role_values_csv" ]] || { usage; die "--role-values-csv is required"; }

APP_PREFIX="$app_prefix"
ROLE_VALUES_CSV="$role_values_csv"

IFS=',' read -r -a role_values <<< "$ROLE_VALUES_CSV"

for role_value in "${role_values[@]}"; do
  role_value="$(echo "$role_value" | xargs)"
  [[ -z "$role_value" ]] && continue

  group_name="${APP_PREFIX}-${role_value}"
  group_id=$(az ad group list --filter "displayName eq '$group_name'" --query "[0].id" -o tsv --only-show-errors || true)
  if [[ -z "$group_id" ]]; then
    mail_nickname="$(sanitize_mail_nickname "$group_name")"
    group_id=$(az ad group create --display-name "$group_name" --mail-nickname "$mail_nickname" --security-enabled true --query id -o tsv --only-show-errors)
    echo "created group: $group_name ($group_id)" >&2
  else
    echo "found group: $group_name ($group_id)" >&2
  fi

  echo "$role_value=$group_id"
done
