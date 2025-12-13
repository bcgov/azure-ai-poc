#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_entra_lib.sh"

require_cmd az
require_cmd jq
az_login_check

usage() {
    cat <<'USAGE' >&2
Usage:
    ./create-entra-apps.sh \
        --tenant-id <tenant-guid> \
        --app-prefix <prefix> \
        --spa-app-name <display-name> \
        --api-app-name <display-name> \
        --s2s-app-name <display-name> \
        --spa-redirect-uri <uri> [--spa-redirect-uri <uri> ...]
        [--user-roles-csv <value:display,...>]
        [--force-new-secret]

Notes:
    - No defaults are assumed; all parameters must be provided.
    - The script is idempotent: it will reuse existing apps by display name.
    - S2S client secret is only created if none exists (use --force-new-secret to override).
    - Default user role 'ai-poc-participant' is always created.
    - Additional user roles can be added with --user-roles-csv (comma-separated)
      Example: --user-roles-csv "reader:Data Reader,writer:Data Writer,admin:Administrator"
USAGE
}

tenant_id=""
app_prefix=""
spa_app_name=""
api_app_name=""
s2s_app_name=""
spa_redirect_uris=()
user_roles_csv=""
force_new_secret=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tenant-id)
            tenant_id="${2:-}"; shift 2 ;;
        --app-prefix)
            app_prefix="${2:-}"; shift 2 ;;
        --spa-app-name)
            spa_app_name="${2:-}"; shift 2 ;;
        --api-app-name)
            api_app_name="${2:-}"; shift 2 ;;
        --s2s-app-name)
            s2s_app_name="${2:-}"; shift 2 ;;
        --spa-redirect-uri)
            spa_redirect_uris+=("${2:-}"); shift 2 ;;
        --user-roles-csv)
            user_roles_csv="${2:-}"; shift 2 ;;
        --force-new-secret)
            force_new_secret=true; shift ;;
        -h|--help)
            usage; exit 0 ;;
        *)
            echo "Unknown argument: $1" >&2
            usage
            exit 2
            ;;
    esac
done

[[ -n "$tenant_id" ]] || { usage; die "--tenant-id is required"; }
[[ -n "$app_prefix" ]] || { usage; die "--app-prefix is required"; }
[[ -n "$spa_app_name" ]] || { usage; die "--spa-app-name is required"; }
[[ -n "$api_app_name" ]] || { usage; die "--api-app-name is required"; }
[[ -n "$s2s_app_name" ]] || { usage; die "--s2s-app-name is required"; }
[[ ${#spa_redirect_uris[@]} -gt 0 ]] || { usage; die "At least one --spa-redirect-uri is required"; }

APP_PREFIX="$app_prefix"
SPA_APP_NAME="$spa_app_name"
API_APP_NAME="$api_app_name"
S2S_APP_NAME="$s2s_app_name"

echo "Using tenant: $tenant_id" >&2

# 1) API app (resource)
api_app_id="$(get_or_create_app "$API_APP_NAME")"
api_app_object_id="$(get_app_object_id "$api_app_id")"
api_sp_object_id="$(get_or_create_sp_object_id "$api_app_id")"

# Identifier URI (idempotent)
az ad app update --id "$api_app_object_id" --identifier-uris "api://$api_app_id" --only-show-errors >/dev/null

# Ensure API has scope + app roles (via Microsoft Graph + jq)
tmp_in="$(mktemp)"
tmp_patch="$(mktemp)"
trap 'rm -f "$tmp_in" "$tmp_patch"' EXIT

az rest --method GET \
  --uri "https://graph.microsoft.com/v1.0/applications/$api_app_object_id" \
  --output json > "$tmp_in"

# Build the patch JSON using jq (pure bash, no Python)
# 1. Add access_as_user scope if missing
# 2. Add ai-poc-participant role if missing
# 3. Add api.access role if missing
# 4. Add any custom user roles from --user-roles-csv
scope_uuid="$(generate_uuid)"
role1_uuid="$(generate_uuid)"
role2_uuid="$(generate_uuid)"

# Build custom roles JSON array from CSV
custom_roles_json="[]"
if [[ -n "$user_roles_csv" ]]; then
  IFS=',' read -ra role_specs <<< "$user_roles_csv"
  for role_spec in "${role_specs[@]}"; do
    # Trim whitespace
    role_spec="$(echo "$role_spec" | xargs)"
    if [[ -n "$role_spec" ]]; then
      role_value="${role_spec%%:*}"
      role_display="${role_spec#*:}"
      if [[ -z "$role_display" || "$role_display" == "$role_value" ]]; then
        role_display="$role_value"
      fi
      role_uuid="$(generate_uuid)"
      custom_roles_json=$(echo "$custom_roles_json" | jq \
        --arg value "$role_value" \
        --arg display "$role_display" \
        --arg id "$role_uuid" \
        '. += [{
          "allowedMemberTypes": ["User"],
          "description": ("Custom role: " + $display),
          "displayName": $display,
          "id": $id,
          "isEnabled": true,
          "value": $value
        }]')
    fi
  done
fi

jq --arg scope_id "$scope_uuid" \
   --arg role1_id "$role1_uuid" \
   --arg role2_id "$role2_uuid" \
   --argjson custom_roles "$custom_roles_json" '
  # Ensure api.oauth2PermissionScopes exists
  .api.oauth2PermissionScopes //= [] |
  
  # Add access_as_user scope if not present
  (if (.api.oauth2PermissionScopes | map(select(.value == "access_as_user")) | length) == 0
   then .api.oauth2PermissionScopes += [{
     "adminConsentDescription": "Allow the application to access the API on behalf of the signed-in user.",
     "adminConsentDisplayName": "Access API as signed-in user",
     "id": $scope_id,
     "isEnabled": true,
     "type": "User",
     "userConsentDescription": "Allow this app to access the API on your behalf.",
     "userConsentDisplayName": "Access API on your behalf",
     "value": "access_as_user"
   }]
   else . end) |

  # Ensure appRoles exists
  .appRoles //= [] |

  # Add ai-poc-participant role if not present
  (if (.appRoles | map(select(.value == "ai-poc-participant")) | length) == 0
   then .appRoles += [{
     "allowedMemberTypes": ["User"],
     "description": "Can access protected API endpoints intended for participants.",
     "displayName": "AI POC Participant",
     "id": $role1_id,
     "isEnabled": true,
     "value": "ai-poc-participant"
   }]
   else . end) |

  # Add api.access role if not present
  (if (.appRoles | map(select(.value == "api.access")) | length) == 0
   then .appRoles += [{
     "allowedMemberTypes": ["Application"],
     "description": "Allows an application to call the API using client credentials.",
     "displayName": "API Access (Client Credentials)",
     "id": $role2_id,
     "isEnabled": true,
     "value": "api.access"
   }]
   else . end) |

  # Add custom user roles (from --user-role flags) if not present
  reduce $custom_roles[] as $role (.;
    if (.appRoles | map(select(.value == $role.value)) | length) == 0
    then .appRoles += [$role]
    else .
    end
  ) |

  # Output only the fields we want to PATCH
  { api: .api, appRoles: .appRoles }
' "$tmp_in" > "$tmp_patch"

az rest --method PATCH \
  --uri "https://graph.microsoft.com/v1.0/applications/$api_app_object_id" \
  --headers "Content-Type=application/json" \
  --body "@$tmp_patch" \
  --only-show-errors >/dev/null

# Report which roles were configured
configured_roles="ai-poc-participant, api.access"
if [[ -n "$user_roles_csv" ]]; then
  IFS=',' read -ra role_specs <<< "$user_roles_csv"
  for role_spec in "${role_specs[@]}"; do
    role_spec="$(echo "$role_spec" | xargs)"
    if [[ -n "$role_spec" ]]; then
      role_value="${role_spec%%:*}"
      configured_roles="$configured_roles, $role_value"
    fi
  done
fi
echo "configured API app scopes and roles: $configured_roles" >&2

# 2) SPA app (client)
spa_app_id="$(get_or_create_app "$SPA_APP_NAME")"
spa_app_object_id="$(get_app_object_id "$spa_app_id")"
get_or_create_sp_object_id "$spa_app_id" >/dev/null

# Configure SPA redirect URIs using Graph API (az ad app update --set doesn't work reliably)
redirect_uris_json=$(printf '%s\n' "${spa_redirect_uris[@]}" | jq -R . | jq -s .)
spa_patch=$(jq -n --argjson uris "$redirect_uris_json" '{ spa: { redirectUris: $uris } }')
az rest --method PATCH \
  --uri "https://graph.microsoft.com/v1.0/applications/$spa_app_object_id" \
  --headers "Content-Type=application/json" \
  --body "$spa_patch" \
  --only-show-errors >/dev/null

echo "configured SPA redirect URIs" >&2

# 3) Service-to-service (daemon) app
s2s_app_id="$(get_or_create_app "$S2S_APP_NAME")"
s2s_app_object_id="$(get_app_object_id "$s2s_app_id")"
s2s_sp_object_id="$(get_or_create_sp_object_id "$s2s_app_id")"

# Check if S2S app already has credentials (idempotent: only create if none exist)
existing_creds=$(az ad app credential list --id "$s2s_app_id" --query "length(@)" -o tsv --only-show-errors 2>/dev/null | tr -d '\r' || echo "0")
if [[ "$existing_creds" == "0" ]] || [[ "$force_new_secret" == "true" ]]; then
  s2s_client_secret="$(az ad app credential reset --id "$s2s_app_id" --display-name "${APP_PREFIX}-s2s-secret" --years 1 --query password -o tsv --only-show-errors | tr -d '\r')"
  if [[ "$force_new_secret" == "true" ]]; then
    echo "created new S2S client secret (--force-new-secret)" >&2
  else
    echo "created new S2S client secret" >&2
  fi
else
  s2s_client_secret="<existing-secret-not-shown>"
  echo "S2S app already has $existing_creds credential(s); skipping secret creation." >&2
  echo "To generate a new secret, use --force-new-secret or: az ad app credential reset --id $s2s_app_id" >&2
fi

cat <<OUT
ENTRA_TENANT_ID=$tenant_id

# SPA
ENTRA_SPA_CLIENT_ID=$spa_app_id

# API
ENTRA_API_CLIENT_ID=$api_app_id
ENTRA_API_AUDIENCE=$api_app_id
ENTRA_API_APP_ID_URI=api://$api_app_id

# Service-to-service (client credentials)
ENTRA_S2S_CLIENT_ID=$s2s_app_id
ENTRA_S2S_CLIENT_SECRET=$s2s_client_secret

# Resource IDs used for role assignments
ENTRA_API_SERVICE_PRINCIPAL_OBJECT_ID=$api_sp_object_id
ENTRA_S2S_SERVICE_PRINCIPAL_OBJECT_ID=$s2s_sp_object_id
OUT

if [[ "$s2s_client_secret" == "<existing-secret-not-shown>" ]]; then
  echo "NOTE: S2S secret was not regenerated. Use your previously stored secret." >&2
else
  echo "NOTE: Store ENTRA_S2S_CLIENT_SECRET securely (do not commit)." >&2
fi
