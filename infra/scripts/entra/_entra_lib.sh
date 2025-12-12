#!/usr/bin/env bash
set -euo pipefail

die() {
  echo "ERROR: $*" >&2
  exit 1
}

require_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "ERROR: Missing required command: $cmd" >&2
    exit 1
  }
}

az_login_check() {
  az account show --only-show-errors >/dev/null 2>&1 || {
    echo "ERROR: Not logged in. Run: az login" >&2
    exit 1
  }
}


get_or_create_app() {
  local display_name="$1"

  local app_id
  app_id=$(az ad app list --display-name "$display_name" --query "[0].appId" -o tsv --only-show-errors || true)
  if [[ -z "$app_id" ]]; then
    app_id=$(az ad app create --display-name "$display_name" --sign-in-audience "AzureADMyOrg" --query appId -o tsv --only-show-errors)
    echo "created app: $display_name ($app_id)" >&2
  else
    echo "found app: $display_name ($app_id)" >&2
  fi

  echo "$app_id"
}

get_app_object_id() {
  local app_id="$1"
  az ad app show --id "$app_id" --query id -o tsv --only-show-errors
}

get_or_create_sp_object_id() {
  local app_id="$1"

  local sp_id
  sp_id=$(az ad sp list --filter "appId eq '$app_id'" --query "[0].id" -o tsv --only-show-errors || true)
  if [[ -z "$sp_id" ]]; then
    az ad sp create --id "$app_id" --only-show-errors >/dev/null
    sp_id=$(az ad sp list --filter "appId eq '$app_id'" --query "[0].id" -o tsv --only-show-errors)
    echo "created service principal for appId: $app_id" >&2
  fi

  echo "$sp_id"
}

sanitize_mail_nickname() {
  local s="$1"
  # NOTE: Entra group creation requires a mailNickname.
  # Example:
  #   displayName:  azure-ai-poc-dev-ai-poc-participant
  #   mailNickname: azureaipocdevaipocparticipant
  # We use a tiny Python snippet (instead of sed/jq edge cases) to:
  #   - strip non-alphanumerics consistently
  #   - cap length to a safe maximum
  python - <<PY
import re
s = ${s@Q}
s = re.sub(r'[^A-Za-z0-9]', '', s)
print(s[:64] or 'group')
PY
}
