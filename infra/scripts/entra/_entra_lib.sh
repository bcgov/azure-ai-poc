#!/usr/bin/env bash
# Entra ID helper library - pure bash + jq (no Python)
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
  # First check if there's an account configured
  if ! az account show --only-show-errors >/dev/null 2>&1; then
    echo "ERROR: Not logged in. Run: az login" >&2
    exit 1
  fi

  # Now validate the token actually works by making a simple Graph API call
  # This catches expired tokens, revoked sessions, etc.
  echo "Validating Azure CLI token..." >&2
  local validation_result
  validation_result=$(az rest --method GET \
    --uri "https://graph.microsoft.com/v1.0/me" \
    --query "userPrincipalName" -o tsv 2>&1) || {
    echo "" >&2
    echo "ERROR: Azure CLI token is invalid or expired." >&2
    echo "The token may have been revoked by Conditional Access policies." >&2
    echo "" >&2
    echo "To fix, run:" >&2
    echo "  az logout" >&2
    echo "  az login --tenant <tenant-id> --use-device-code \\" >&2
    echo "    --scope \"https://graph.microsoft.com//.default\"" >&2
    echo "" >&2
    exit 1
  }
  validation_result=$(echo "$validation_result" | tr -d '\r')
  echo "Authenticated as: $validation_result" >&2
}

get_or_create_app() {
  local display_name="$1"

  local app_id
  app_id=$(az ad app list --display-name "$display_name" --query "[0].appId" -o tsv --only-show-errors 2>/dev/null | tr -d '\r' || true)
  if [[ -z "$app_id" ]]; then
    app_id=$(az ad app create --display-name "$display_name" --sign-in-audience "AzureADMyOrg" --query appId -o tsv --only-show-errors 2>&1 | tr -d '\r') || {
      echo "ERROR: Failed to create app registration: $display_name" >&2
      exit 1
    }
    if [[ -z "$app_id" ]]; then
      echo "ERROR: App creation returned empty ID. Check Azure CLI authentication." >&2
      echo "Try: az logout && az login --tenant <tenant-id>" >&2
      exit 1
    fi
    echo "created app: $display_name ($app_id)" >&2
  else
    echo "found app: $display_name ($app_id)" >&2
  fi

  printf '%s' "$app_id"
}

get_app_object_id() {
  local app_id="$1"
  az ad app show --id "$app_id" --query id -o tsv --only-show-errors 2>/dev/null | tr -d '\r'
}

get_or_create_sp_object_id() {
  local app_id="$1"

  if [[ -z "$app_id" ]]; then
    echo "ERROR: Cannot create service principal - app_id is empty" >&2
    exit 1
  fi

  local sp_id
  sp_id=$(az ad sp list --filter "appId eq '$app_id'" --query "[0].id" -o tsv --only-show-errors 2>/dev/null | tr -d '\r' || true)
  if [[ -z "$sp_id" ]]; then
    az ad sp create --id "$app_id" --only-show-errors >/dev/null 2>&1 || {
      echo "ERROR: Failed to create service principal for appId: $app_id" >&2
      exit 1
    }
    sp_id=$(az ad sp list --filter "appId eq '$app_id'" --query "[0].id" -o tsv --only-show-errors | tr -d '\r')
    if [[ -z "$sp_id" ]]; then
      echo "ERROR: Service principal creation returned empty ID for appId: $app_id" >&2
      exit 1
    fi
    echo "created service principal for appId: $app_id" >&2
  fi

  printf '%s' "$sp_id"
}

sanitize_mail_nickname() {
  local s="$1"
  # Strip non-alphanumerics using tr, then truncate to 64 chars
  local cleaned
  cleaned=$(printf '%s' "$s" | tr -cd 'A-Za-z0-9' | cut -c1-64)
  if [[ -z "$cleaned" ]]; then
    printf 'group'
  else
    printf '%s' "$cleaned"
  fi
}

generate_uuid() {
  # Generate a UUID using uuidgen if available, otherwise use /proc/sys/kernel/random/uuid
  if command -v uuidgen >/dev/null 2>&1; then
    uuidgen | tr '[:upper:]' '[:lower:]'
  elif [[ -f /proc/sys/kernel/random/uuid ]]; then
    cat /proc/sys/kernel/random/uuid
  else
    # Fallback: use od + date for pseudo-random UUID
    printf '%04x%04x-%04x-%04x-%04x-%04x%04x%04x\n' \
      $((RANDOM)) $((RANDOM)) $((RANDOM)) \
      $(((RANDOM & 0x0fff) | 0x4000)) \
      $(((RANDOM & 0x3fff) | 0x8000)) \
      $((RANDOM)) $((RANDOM)) $((RANDOM))
  fi
}
