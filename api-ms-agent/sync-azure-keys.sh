#!/bin/bash
# =============================================================================
# Azure Service Keys Sync Script for api-ms-agent
# =============================================================================
#
# This script queries Azure for API keys/endpoints and updates the .env file
# for the following services:
# - Azure OpenAI (endpoint + key)
# - Cosmos DB (endpoint + key)
# - Azure AI Search (endpoint + key)
# - Azure Document Intelligence (endpoint + key)
# - Azure Speech Services (key + region)
#
# PREREQUISITES:
# - Azure CLI installed and authenticated (az login)
# - Appropriate permissions to read service keys
# - jq installed for JSON parsing
#
# USAGE:
#   ./sync-azure-keys.sh --resource-group <rg-name> [--env-file .env]
#
# EXAMPLES:
#   ./sync-azure-keys.sh --resource-group azure-ai-poc-tools
#   ./sync-azure-keys.sh --resource-group my-rg --env-file .env.production
#
# =============================================================================

set -euo pipefail

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Default values
RESOURCE_GROUP=""
ENV_FILE=".env"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Log functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Usage information
usage() {
    cat << EOF
Usage: $0 --resource-group <rg-name> [options]

OPTIONS:
  --resource-group, -g <name>    Azure resource group containing the services (required)
  --env-file, -e <path>          Path to .env file (default: .env)
  --help, -h                     Show this help message

EXAMPLES:
  $0 --resource-group azure-ai-poc-tools
  $0 -g my-rg -e .env.production

EOF
    exit 0
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --resource-group|-g)
                RESOURCE_GROUP="$2"
                shift 2
                ;;
            --env-file|-e)
                ENV_FILE="$2"
                shift 2
                ;;
            --help|-h)
                usage
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                ;;
        esac
    done

    if [[ -z "$RESOURCE_GROUP" ]]; then
        log_error "Resource group is required"
        usage
    fi
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Azure CLI
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI not found. Please install: https://docs.microsoft.com/cli/azure/install-azure-cli"
        exit 1
    fi

    # Check jq
    if ! command -v jq &> /dev/null; then
        log_error "jq not found. Please install: https://stedolan.github.io/jq/download/"
        exit 1
    fi

    # Check Azure session
    if ! az account show &> /dev/null; then
        log_error "Not authenticated with Azure. Please run 'az login'"
        exit 1
    fi

    log_success "Prerequisites satisfied"
}

# Backup .env file
backup_env_file() {
    local env_path="${SCRIPT_DIR}/${ENV_FILE}"
    
    if [[ -f "$env_path" ]]; then
        local backup_path="${env_path}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$env_path" "$backup_path"
        log_info "Backed up existing .env to: ${backup_path}"
    else
        log_warn ".env file not found, will create new one"
        touch "$env_path"
    fi
}

# Update or add environment variable in .env file
update_env_var() {
    local key="$1"
    local value="$2"
    local env_path="${SCRIPT_DIR}/${ENV_FILE}"

    # Escape special characters in value for sed (including quotes and backslashes)
    local escaped_value=$(printf '%s\n' "$value" | sed -e 's/[\/&]/\\&/g' -e 's/\\/\\\\/g' -e 's/"/\\"/g')

    if grep -q "^${key}=" "$env_path" 2>/dev/null; then
        # Update existing key with double quotes
        sed -i.tmp "s|^${key}=.*|${key}=\"${escaped_value}\"|" "$env_path"
        rm -f "${env_path}.tmp"
        log_info "Updated: $key"
    else
        # Add new key with double quotes
        echo "${key}=\"${escaped_value}\"" >> "$env_path"
        log_info "Added: $key"
    fi
}

# Query Azure OpenAI service
sync_azure_openai() {
    log_info "Querying Azure OpenAI service..."

    # Find Azure OpenAI account in resource group
    local openai_accounts
    openai_accounts=$(az cognitiveservices account list \
        --resource-group "$RESOURCE_GROUP" \
        --query "[?kind=='OpenAI']" \
        --output json 2>/dev/null || echo "[]")

    local account_count=$(echo "$openai_accounts" | jq 'length')

    if [[ "$account_count" -eq 0 ]]; then
        log_warn "No Azure OpenAI accounts found in resource group: $RESOURCE_GROUP"
        return
    fi

    # Use first account if multiple exist
    local account_name=$(echo "$openai_accounts" | jq -r '.[0].name')
    local endpoint=$(echo "$openai_accounts" | jq -r '.[0].properties.endpoint')

    log_info "Found Azure OpenAI account: $account_name"

    # Get API key
    local api_key
    api_key=$(az cognitiveservices account keys list \
        --name "$account_name" \
        --resource-group "$RESOURCE_GROUP" \
        --query "key1" \
        --output tsv 2>/dev/null || echo "")

    if [[ -n "$api_key" ]]; then
        update_env_var "AZURE_OPENAI_API_KEY" "$api_key"
        log_success "Azure OpenAI key synced"
    else
        log_warn "Failed to retrieve Azure OpenAI key"
    fi
}

# Query Cosmos DB service
sync_cosmos_db() {
    log_info "Querying Cosmos DB service..."

    # Find Cosmos DB accounts
    local cosmos_accounts
    cosmos_accounts=$(az cosmosdb list \
        --resource-group "$RESOURCE_GROUP" \
        --output json 2>/dev/null || echo "[]")

    local account_count=$(echo "$cosmos_accounts" | jq 'length')

    if [[ "$account_count" -eq 0 ]]; then
        log_warn "No Cosmos DB accounts found in resource group: $RESOURCE_GROUP"
        return
    fi

    # Use first account if multiple exist
    local account_name=$(echo "$cosmos_accounts" | jq -r '.[0].name')
    local endpoint=$(echo "$cosmos_accounts" | jq -r '.[0].documentEndpoint')

    log_info "Found Cosmos DB account: $account_name"

    # Get primary key
    local primary_key
    primary_key=$(az cosmosdb keys list \
        --name "$account_name" \
        --resource-group "$RESOURCE_GROUP" \
        --type keys \
        --query "primaryMasterKey" \
        --output tsv 2>/dev/null || echo "")

    if [[ -n "$primary_key" ]]; then
        update_env_var "COSMOS_DB_KEY" "$primary_key"
        log_success "Cosmos DB key synced"
    else
        log_warn "Failed to retrieve Cosmos DB key"
    fi
}

# Query Azure AI Search service
sync_azure_search() {
    log_info "Querying Azure AI Search service..."

    # Find Azure Search services
    local search_services
    search_services=$(az search service list \
        --resource-group "$RESOURCE_GROUP" \
        --output json 2>/dev/null || echo "[]")

    local service_count=$(echo "$search_services" | jq 'length')

    if [[ "$service_count" -eq 0 ]]; then
        log_warn "No Azure AI Search services found in resource group: $RESOURCE_GROUP"
        return
    fi

    # Use first service if multiple exist
    local service_name=$(echo "$search_services" | jq -r '.[0].name')
    local endpoint="https://${service_name}.search.windows.net"

    log_info "Found Azure AI Search service: $service_name"

    # Get admin key
    local admin_key
    admin_key=$(az search admin-key show \
        --service-name "$service_name" \
        --resource-group "$RESOURCE_GROUP" \
        --query "primaryKey" \
        --output tsv 2>/dev/null || echo "")

    if [[ -n "$admin_key" ]]; then
        update_env_var "AZURE_SEARCH_KEY" "$admin_key"
        log_success "Azure AI Search key synced"
    else
        log_warn "Failed to retrieve Azure AI Search key"
    fi
}

# Query Azure Document Intelligence service
sync_document_intelligence() {
    log_info "Querying Azure Document Intelligence service..."

    # Find Document Intelligence (Form Recognizer) accounts
    local doc_accounts
    doc_accounts=$(az cognitiveservices account list \
        --resource-group "$RESOURCE_GROUP" \
        --query "[?kind=='FormRecognizer']" \
        --output json 2>/dev/null || echo "[]")

    local account_count=$(echo "$doc_accounts" | jq 'length')

    if [[ "$account_count" -eq 0 ]]; then
        log_warn "No Document Intelligence accounts found in resource group: $RESOURCE_GROUP"
        return
    fi

    # Use first account if multiple exist
    local account_name=$(echo "$doc_accounts" | jq -r '.[0].name')
    local endpoint=$(echo "$doc_accounts" | jq -r '.[0].properties.endpoint')

    log_info "Found Document Intelligence account: $account_name"

    # Get API key
    local api_key
    api_key=$(az cognitiveservices account keys list \
        --name "$account_name" \
        --resource-group "$RESOURCE_GROUP" \
        --query "key1" \
        --output tsv 2>/dev/null || echo "")

    if [[ -n "$api_key" ]]; then
        update_env_var "AZURE_DOCUMENT_INTELLIGENCE_KEY" "$api_key"
        log_success "Document Intelligence key synced"
    else
        log_warn "Failed to retrieve Document Intelligence key"
    fi
}

# Query Azure Speech Services
sync_azure_speech() {
    log_info "Querying Azure Speech Services..."

    # Find Speech Services accounts
    local speech_accounts
    speech_accounts=$(az cognitiveservices account list \
        --resource-group "$RESOURCE_GROUP" \
        --query "[?kind=='SpeechServices']" \
        --output json 2>/dev/null || echo "[]")

    local account_count=$(echo "$speech_accounts" | jq 'length')

    if [[ "$account_count" -eq 0 ]]; then
        log_warn "No Speech Services accounts found in resource group: $RESOURCE_GROUP"
        return
    fi

    # Use first account if multiple exist
    local account_name=$(echo "$speech_accounts" | jq -r '.[0].name')
    local location=$(echo "$speech_accounts" | jq -r '.[0].location')

    log_info "Found Speech Services account: $account_name"

    # Get API key
    local api_key
    api_key=$(az cognitiveservices account keys list \
        --name "$account_name" \
        --resource-group "$RESOURCE_GROUP" \
        --query "key1" \
        --output tsv 2>/dev/null || echo "")

    if [[ -n "$api_key" ]]; then
        update_env_var "AZURE_SPEECH_KEY" "$api_key"
        update_env_var "AZURE_SPEECH_REGION" "$location"
        log_success "Speech Services key and region synced"
    else
        log_warn "Failed to retrieve Speech Services key"
    fi
}

# Main execution
main() {
    log_info "Starting Azure service keys sync..."
    log_info "Resource Group: $RESOURCE_GROUP"
    log_info "Env File: $ENV_FILE"
    echo ""

    parse_args "$@"
    check_prerequisites
    backup_env_file

    # Sync all services
    sync_azure_openai
    sync_cosmos_db
    sync_azure_search
    sync_document_intelligence
    sync_azure_speech

    echo ""
    log_success "Azure service keys sync completed!"
    log_info "Updated .env file: ${SCRIPT_DIR}/${ENV_FILE}"
    log_warn "Remember to restart your application to load the new credentials"
}

# Run main with all script arguments
main "$@"
