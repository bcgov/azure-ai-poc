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
    ./create-entra-apps.sh \
        --tenant-id <tenant-guid> \
        --app-prefix <prefix> \
        --spa-app-name <display-name> \
        --api-app-name <display-name> \
        --s2s-app-name <display-name> \
        --spa-redirect-uri <uri> [--spa-redirect-uri <uri> ...]

Notes:
    - No defaults are assumed; all parameters must be provided.
    - The script is idempotent: it will reuse existing apps by display name.
USAGE
}

tenant_id=""
app_prefix=""
spa_app_name=""
api_app_name=""
s2s_app_name=""
spa_redirect_uris=()

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
az ad app update --id "$api_app_id" --identifier-uris "api://$api_app_id" --only-show-errors >/dev/null

# Ensure API has scope + app roles (via Microsoft Graph)
tmp_in="$(mktemp)"
tmp_patch="$(mktemp)"

az rest --method GET \
  --uri "https://graph.microsoft.com/v1.0/applications/$api_app_object_id" \
  --output json > "$tmp_in"

# NOTE: This embedded Python snippet exists because Azure CLI doesn't provide a clean,
# idempotent way to *merge/update nested JSON* for Entra app configuration (OAuth scopes
# and appRoles).
#
# What we do:
#   1) GET the current application object via Microsoft Graph
#   2) Use Python to add missing items (scope + roles) while preserving existing ones
#   3) PATCH only the fields we changed back via Microsoft Graph
#
# Why Python here (instead of jq/sed):
#   - We need to generate UUIDs for new scope/role IDs
#   - We must preserve existing scopes/roles on reruns (safe/idempotent)
#   - It's far less brittle than trying to quote/merge deep JSON in bash
#
# Multi-environment tip:
#   - Keep environments isolated by suffixing names in the CLI caller, e.g.
#       --app-prefix "azure-ai-poc-dev" --api-app-name "azure-ai-poc-dev-api"
#     so each env gets its own app registration and roles.
python - "$tmp_in" "$tmp_patch" <<'PY'
import json
import sys
import uuid

src_path, dst_path = sys.argv[1], sys.argv[2]

with open(src_path, 'r', encoding='utf-8') as f:
    app = json.load(f)

api = app.get('api') or {}
scopes = api.get('oauth2PermissionScopes') or []

if not any(s.get('value') == 'access_as_user' for s in scopes):
    scopes.append({
        'adminConsentDescription': 'Allow the application to access the API on behalf of the signed-in user.',
        'adminConsentDisplayName': 'Access API as signed-in user',
        'id': str(uuid.uuid4()),
        'isEnabled': True,
        'type': 'User',
        'userConsentDescription': 'Allow this app to access the API on your behalf.',
        'userConsentDisplayName': 'Access API on your behalf',
        'value': 'access_as_user',
    })

api['oauth2PermissionScopes'] = scopes

app_roles = app.get('appRoles') or []

def ensure_role(value: str, display: str, desc: str, allowed_member_types):
    if any(r.get('value') == value for r in app_roles):
        return
    app_roles.append({
        'allowedMemberTypes': allowed_member_types,
        'description': desc,
        'displayName': display,
        'id': str(uuid.uuid4()),
        'isEnabled': True,
        'value': value,
    })

ensure_role(
    value='ai-poc-participant',
    display='AI POC Participant',
    desc='Can access protected API endpoints intended for participants.',
    allowed_member_types=['User'],
)

ensure_role(
    value='api.access',
    display='API Access (Client Credentials)',
    desc='Allows an application to call the API using client credentials.',
    allowed_member_types=['Application'],
)

patch = {
    'api': api,
    'appRoles': app_roles,
}

with open(dst_path, 'w', encoding='utf-8') as f:
    json.dump(patch, f)
PY

az rest --method PATCH \
  --uri "https://graph.microsoft.com/v1.0/applications/$api_app_object_id" \
  --headers "Content-Type=application/json" \
  --body "@$tmp_patch" \
  --only-show-errors >/dev/null

# 2) SPA app (client)
spa_app_id="$(get_or_create_app "$SPA_APP_NAME")"
spa_app_object_id="$(get_app_object_id "$spa_app_id")"
get_or_create_sp_object_id "$spa_app_id" >/dev/null

# Configure SPA redirect URIs (best-effort; safe if rerun)
redirect_uris_json=$(python - <<PY
import json
import sys
uris = sys.argv[1:]
print(json.dumps(uris))
PY
"${spa_redirect_uris[@]}"
)
az ad app update --id "$spa_app_id" --set "spa.redirectUris=${redirect_uris_json}" --only-show-errors >/dev/null || true

# 3) Service-to-service (daemon) app
s2s_app_id="$(get_or_create_app "$S2S_APP_NAME")"
s2s_app_object_id="$(get_app_object_id "$s2s_app_id")"
s2s_sp_object_id="$(get_or_create_sp_object_id "$s2s_app_id")"

s2s_client_secret="$(az ad app credential reset --id "$s2s_app_id" --append --display-name "${APP_PREFIX}-s2s-secret" --years 1 --query password -o tsv --only-show-errors)"

rm -f "$tmp_in" "$tmp_patch"

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

echo "NOTE: Store ENTRA_S2S_CLIENT_SECRET securely (do not commit)." >&2
