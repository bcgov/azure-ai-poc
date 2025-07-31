#!/bin/bash

# =============================================================================
# Azure Landing Zone GitHub Actions OIDC Setup Script
# =============================================================================
# 
# This script automates the setup of Azure managed identity and OIDC 
# authentication for GitHub Actions in Azure Landing Zone environments.
#
# Features:
# - Creates user-assigned managed identity for GitHub Actions
# - Configures OIDC federated identity credentials (no secrets needed!)
# - Sets up Azure storage account for Terraform state management
# - Optionally creates GitHub environment and secrets automatically
# - Assigns necessary Azure roles for deployment permissions
# 
# Role is managed by platform team, see this link:: https://developer.gov.bc.ca/docs/default/component/public-cloud-techdocs/azure/design-build-deploy/user-management/
# Examples:
#   # Basic setup for development environment
#   ./initial-azure-setup.sh -g "ABCD-dev-networking" -n "myapp-dev-identity" \
#     -r "myorg/myapp" -e "dev" --assign-roles "DO_PuC_Azure_Live_abc123_Contributors" --create-storage
#
#   # Production setup with auto GitHub secrets creation
#   ./initial-azure-setup.sh -g "ABCD-prod-networking" -n "myapp-prod-identity" \
#     -r "myorg/myapp" -e "prod" --assign-roles "DO_PuC_Azure_Live_abc123_Contributors" \
#     --create-storage --create-github-secrets
# 
# =============================================================================
# Prerequisites
# =============================================================================
# 
# Before running this script, ensure the following requirements are met:
#
# Azure Requirements:
# - Azure CLI installed and logged in (run: az login)
# - Appropriate permissions in Azure subscription (Contributor-Owner)
#
# GitHub Requirements (optional):
# - GitHub CLI installed (for auto secret creation with --create-github-secrets)
# - Repository admin permissions (if using --create-github-secrets)
#   Required GitHub token scopes:
#   • repo (full repository access)
#   • admin:repo_hook (if using webhooks)
#   • admin:org (if repository is in an organization)
#
# Important Post-Setup Action (If You are not a Contributor Owner in the subscription):
# After running this setup script, a project lead must manually add the newly
# created Azure User-Assigned Managed Identity to the appropriate Entra ID group
# that assigns the Contributor role for this project.
#
# Manual Steps Required After Script Completion:
#   1. Note the managed identity name from the script output
#   2. In the Entra ID admin portal, locate the appropriate project group
#   3. Add the managed identity to the group that grants Contributor access
#   4. Verify the group assignment is complete before running GitHub Actions
#
# For more information on role management, see:
# https://developer.gov.bc.ca/docs/default/component/public-cloud-techdocs/azure/design-build-deploy/user-management/
#
# =============================================================================

# catch errors and unset variables
set -euo pipefail
# =============================================================================
# Utility Functions for Script Management
# =============================================================================

# Array to track temporary files for automatic cleanup
TEMP_FILES=()

# ================================================================================
# Creates a temporary file and tracks it for cleanup
# ================================================================================
create_temp_file() {
    local temp_file
    temp_file=$(mktemp)
    TEMP_FILES+=("$temp_file")
    echo "$temp_file"
}

# ================================================================================
# Cleanup function that removes temporary files on script exit
# ================================================================================
cleanup() {
    local exit_code=$?
    if [[ ${#TEMP_FILES[@]} -gt 0 ]]; then
        rm -f "${TEMP_FILES[@]}" 2>/dev/null || true
    fi
    exit $exit_code
}

# Set trap to ensure cleanup runs on script exit, interrupt, or termination
trap cleanup EXIT INT TERM

# =============================================================================
# Logging Functions with Color Output
# =============================================================================
# Color codes for terminal output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color - resets formatting

# ================================================================================
# Logging functions for consistent output formatting
# ================================================================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# ================================================================================
# Log success messages with green formatting
# ================================================================================
log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# ================================================================================
# Log warning messages with yellow formatting
# ================================================================================
log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# ================================================================================
# Log error messages with red formatting
# ================================================================================
log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ================================================================================
# Display comprehensive help and usage information
# ================================================================================
usage() {
    cat << EOF
=============================================================================
Azure Landing Zone GitHub Actions OIDC Setup Script
=============================================================================

This script configures managed identity and OIDC authentication for GitHub 
Actions to deploy to Azure Landing Zone environments securely.

USAGE:
    $0 [OPTIONS]

REQUIRED OPTIONS:
    -g, --resource-group        Azure resource group name (typically Landing Zone networking RG)
    -n, --identity-name         Name for the user-assigned managed identity
    -r, --github-repo           GitHub repository in format: owner/repository
    -e, --environment           GitHub environment name (dev, test, prod, etc.)

OPTIONAL OPTIONS:
    -ar, --assign-roles         Azure roles to assign (comma-separated)
                               Example: "Contributor,Storage Account Contributor"
                               If not specified, no roles will be assigned
    
    --contributor-scope         Scope for role assignment (default: subscription level)
                               Example: "/subscriptions/xxx/resourceGroups/yyy"
    
    --storage-account           Storage account name for Terraform state
                               (auto-generated based on repo/env if not specified)
    
    --storage-container         Storage container name (default: "tfstate")
    
    --create-storage            Create Azure storage account for Terraform state
    
    --create-github-secrets     Automatically create GitHub environment and secrets
                               (requires GitHub CLI with repo admin access)
    
    --dry-run                   Preview all actions without making any changes
    
    -h, --help                  Show this help message

EXAMPLES:

    # Basic development environment setup
    $0 -g "ABCD-dev-networking" -n "myapp-dev-identity" \
       -r "myorg/myapp" -e "dev" \
       --assign-roles "Contributor" \
       --create-storage

    # Production setup with auto GitHub integration
    $0 -g "ABCD-prod-networking" -n "myapp-prod-identity" \
       -r "myorg/myapp" -e "prod" \
       --assign-roles "Contributor,Storage Account Contributor" \
       --create-storage --create-github-secrets

    # Preview changes without execution (recommended first run)
    $0 -g "ABCD-dev-networking" -n "myapp-dev-identity" \
       -r "myorg/myapp" -e "dev" \
       --assign-roles "Contributor" \
       --create-storage --dry-run

    # Custom storage account with specific scope
    $0 -g "ABCD-test-networking" -n "myapp-test-identity" \
       -r "myorg/myapp" -e "test" \
       --assign-roles "Contributor" \
       --contributor-scope "/subscriptions/xxx/resourceGroups/ABCD-test-rg" \
       --create-storage --storage-account "myapptesttfstate"

NOTES:
    • Resource group should be your Azure Landing Zone networking resource group
    • GitHub repository format must be: owner/repository (e.g., bcgov/myapp)
    • Environment names are case-sensitive and should match your GitHub environments
    • Storage account names are auto-generated as: tfstate{repo}{env} (sanitized)
    • Use --dry-run first to preview what will be created
    • Requires Azure CLI logged in and GitHub CLI (optional) for auto-secrets

=============================================================================
EOF
}

# =============================================================================
# Script Configuration and Default Values
# =============================================================================

# Default values for optional parameters
GITHUB_ENVIRONMENT=""              # Will be set by user input
CONTRIBUTOR_SCOPE=""               # Defaults to subscription level if not specified
ADDITIONAL_ROLES=""               # Additional roles beyond the main ones
STORAGE_ACCOUNT=""                # Auto-generated based on repo name if not specified
STORAGE_CONTAINER="tfstate"       # Standard container name for Terraform state
CREATE_STORAGE=false             # Whether to create storage account
DRY_RUN=false                   # Whether to preview changes only
CREATE_GITHUB_SECRETS=false     # Whether to auto-create GitHub secrets
ASSIGN_ROLES=""                 # Roles to assign to the managed identity

# =============================================================================
# Command Line Argument Parsing
# =============================================================================
while [[ $# -gt 0 ]]; do
    case $1 in
        -g|--resource-group)
            RESOURCE_GROUP="$2"
            shift 2
            ;;
        -n|--identity-name)
            IDENTITY_NAME="$2"
            shift 2
            ;;
        -r|--github-repo)
            GITHUB_REPO="$2"
            shift 2
            ;;
        -e|--environment)
            GITHUB_ENVIRONMENT="$2"
            shift 2
            ;;
        -ar|--assign-roles)
            ASSIGN_ROLES="$2"
            shift 2
            ;;
        --contributor-scope)
            CONTRIBUTOR_SCOPE="$2"
            shift 2
            ;;
        --additional-roles)
            ADDITIONAL_ROLES="$2"
            shift 2
            ;;
        --storage-account)
            STORAGE_ACCOUNT="$2"
            shift 2
            ;;
        --storage-container)
            STORAGE_CONTAINER="$2"
            shift 2
            ;;
        --create-storage)
            CREATE_STORAGE=true
            shift
            ;;
        --create-github-secrets)
            CREATE_GITHUB_SECRETS=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate that all required parameters are provided
if [[ -z "${RESOURCE_GROUP:-}" || -z "${IDENTITY_NAME:-}" || -z "${GITHUB_REPO:-}" || -z "${GITHUB_ENVIRONMENT:-}" ]]; then
    log_error "Required parameters missing!"
    log_error "Missing one or more of: --resource-group, --identity-name, --github-repo, --environment"
    echo ""
    log_info "Use -h or --help to see usage examples"
    exit 1
fi

# Validate GitHub repository format (must be owner/repository)
if [[ ! "$GITHUB_REPO" =~ ^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$ ]]; then
    log_error "Invalid GitHub repository format!"
    log_error "Expected format: owner/repository (e.g., 'myorg/myapp')"
    log_error "Received: '$GITHUB_REPO'"
    exit 1
fi

# ================================================================================
# Execute commands with dry-run support and proper logging
# ================================================================================
execute_command() {
    local cmd="$1"
    local description="$2"
    
    log_info "$description"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "    [DRY-RUN] Would execute: $cmd"
        return 0
    else
        echo "    Executing: $cmd"
        eval "$cmd"
        sleep 1 # Small delay for better readability and Azure propagation
        echo
        return $?
    fi
}

# ================================================================================
# Generate a compliant Azure storage account name from repo and environment
# Azure storage account names must be 3-24 chars, lowercase letters and numbers only
# ================================================================================
generate_storage_account_name() {
    # Only generate if not already specified by user
    if [[ -z "$STORAGE_ACCOUNT" ]]; then
        # Extract repository name (after the slash) and sanitize
        local repo_name=$(echo "$GITHUB_REPO" | cut -d'/' -f2 | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]//g')
        # Sanitize environment name  
        local env_name=$(echo "$GITHUB_ENVIRONMENT" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]//g')

        # Create base name: tfstate + repo + environment
        # Example: tfstate + myapp + dev = tfstatemyappdev
        local base_name="tfstate${repo_name}${env_name}"

        # Azure storage account name constraints: 3-24 characters, lowercase + numbers only
        if [[ ${#base_name} -gt 24 ]]; then
            base_name="${base_name:0:24}"  # Truncate to 24 chars max
        fi

        STORAGE_ACCOUNT="$base_name"

        # Final sanitization to ensure compliance
        STORAGE_ACCOUNT=$(echo "$STORAGE_ACCOUNT" | sed 's/[^a-z0-9]//g')

        # Ensure minimum length requirement (3 chars)
        if [[ ${#STORAGE_ACCOUNT} -lt 3 ]]; then
            STORAGE_ACCOUNT="${STORAGE_ACCOUNT}abc"
        fi

        log_info "Generated storage account name: '$STORAGE_ACCOUNT'"
        log_info "    Based on repo: '$repo_name', environment: '$env_name'"
    else
        log_info "Using provided storage account name: '$STORAGE_ACCOUNT'"
    fi
}

# ================================================================================
# Verify that required tools are installed and user is authenticated
# ================================================================================
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Verify Azure CLI is installed
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI is not installed!"
        log_error "Please install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi
    
    # Verify user is logged into Azure CLI
    if ! az account show &> /dev/null; then
        log_error "Not logged into Azure CLI!"
        log_error "Please run: 'az login' or 'az login --use-device-code'"
        exit 1
    fi

    # validate whether current logged-in user session is still valid
    if ! az account show --query "id" --output tsv &> /dev/null; then
        log_error "Current Azure session is invalid or expired!"
        log_error "Please re-authenticate using: 'az login' or 'az login --use-device-code'"
        exit 1
    fi

    
    # Display current Azure context
    local current_sub=$(az account show --query "name" --output tsv 2>/dev/null || echo "Unknown")
    local current_user=$(az account show --query "user.name" --output tsv 2>/dev/null || echo "Unknown")
    log_info "Azure CLI authenticated as: $current_user"
    log_info "Current subscription: $current_sub"
    
    log_success "Prerequisites check passed"
}

# ================================================================================
# Verify that the specified Azure resource group exists and is accessible
# ================================================================================
check_resource_group() {
    log_info "Checking if resource group '$RESOURCE_GROUP' exists..."
    
    if [[ "$DRY_RUN" == "false" ]]; then
        if ! az group show --name "$RESOURCE_GROUP" &> /dev/null; then
            log_error "Resource group '$RESOURCE_GROUP' does not exist or is not accessible!"
            log_error "Please verify:"
            log_error "  1. Resource group name is correct"
            log_error "  2. You have access to the resource group"
            log_error "  3. You're in the correct Azure subscription"
            exit 1
        fi
        
        # Display resource group location for confirmation
        local rg_location=$(az group show --name "$RESOURCE_GROUP" --query "location" --output tsv)
        log_success "Resource group '$RESOURCE_GROUP' found in $rg_location"
    else
        log_info "[DRY-RUN] Would verify resource group '$RESOURCE_GROUP' exists"
    fi
}

# ================================================================================
# Create user-assigned managed identity for GitHub Actions authentication
# ================================================================================
create_managed_identity() {
    log_info "Creating user-assigned managed identity '$IDENTITY_NAME'..."
    
    # Check if the identity already exists to make this operation idempotent
    if [[ "$DRY_RUN" == "false" ]]; then
        if az identity show --name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
            log_warning "Managed identity '$IDENTITY_NAME' already exists. Skipping creation."
            return 0
        fi
    fi
    
    execute_command "az identity create --name '$IDENTITY_NAME' --resource-group '$RESOURCE_GROUP'" \
        "Creating user-assigned managed identity"
    
    log_success "Managed identity '$IDENTITY_NAME' created successfully"
}


# ================================================================================
# Retrieve the important details from the managed identity for later use
# ================================================================================
get_identity_details() {
    log_info "Retrieving managed identity details..."
    
    if [[ "$DRY_RUN" == "false" ]]; then
        # Extract the key identifiers needed for GitHub Actions and role assignments
        CLIENT_ID=$(az identity show --name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" --query "clientId" --output tsv)
        PRINCIPAL_ID=$(az identity show --name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" --query "principalId" --output tsv)
        IDENTITY_ID=$(az identity show --name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" --query "id" --output tsv)
        
        log_info "Client ID (for GitHub Actions): $CLIENT_ID"
        log_info "Principal ID (for role assignments): $PRINCIPAL_ID"
        log_info "Full Identity Resource ID: $IDENTITY_ID"
    else
        log_info "[DRY-RUN] Would retrieve managed identity details"
        # Set placeholder values for dry-run mode
        CLIENT_ID="[DRY-RUN-CLIENT-ID]"
        PRINCIPAL_ID="[DRY-RUN-PRINCIPAL-ID]"
        IDENTITY_ID="[DRY-RUN-IDENTITY-ID]"
    fi
}

# ================================================================================
# Assign specified Azure roles to the managed identity for deployment permissions
# ================================================================================
assign_roles() {
    # Skip role assignment if no roles specified
    if [[ -z "$ASSIGN_ROLES" ]]; then
        log_info "No roles specified for assignment. Skipping role assignment."
        log_info "You can manually assign roles later or re-run with --assign-roles parameter"
        return 0
    fi
    
    log_info "Assigning Azure roles to managed identity..."
    
    # Set default scope to subscription level if not provided
    if [[ -z "$CONTRIBUTOR_SCOPE" ]]; then
        if [[ "$DRY_RUN" == "false" ]]; then
            CONTRIBUTOR_SCOPE="/subscriptions/$(az account show --query "id" --output tsv)"
        else
            CONTRIBUTOR_SCOPE="[DRY-RUN-SUBSCRIPTION-SCOPE]"
        fi
    fi

    log_info "Role assignment scope: $CONTRIBUTOR_SCOPE"
    
    # Split comma-separated roles and assign each one
    local roles_list=(${ASSIGN_ROLES//,/ })
    for role in "${roles_list[@]}"; do
        log_info "Processing role: '$role'"
        
        # Check if role is already assigned to make operation idempotent
        if [[ "$DRY_RUN" == "false" ]]; then
            local existing_count=$(az role assignment list --assignee "$CLIENT_ID" --role "$role" --scope "$CONTRIBUTOR_SCOPE" --query "length(@)" --output tsv)
            if [[ "$existing_count" -gt 0 ]]; then
                log_warning "Role '$role' already assigned to managed identity. Skipping."
                continue
            fi
        fi
        
        execute_command "az role assignment create --assignee '$CLIENT_ID' --role '$role' --scope '$CONTRIBUTOR_SCOPE'" \
            "Assigning '$role' role to managed identity"
    done
    
    log_success "Role assignments completed successfully"
}


# ================================================================================
# Create federated identity credentials for GitHub Actions OIDC authentication
# ================================================================================
create_federated_credentials() {
    log_info "Creating federated identity credentials for GitHub Actions OIDC..."
    
    # Always create subject claim for environment-specific deployments
    SUBJECT="repo:$GITHUB_REPO:environment:$GITHUB_ENVIRONMENT"
    REPO_NAME_WITHOUT_OWNER=$(echo "$GITHUB_REPO" | cut -d'/' -f2)
    CREDENTIAL_NAME="$REPO_NAME_WITHOUT_OWNER-$GITHUB_ENVIRONMENT"
    
    # GitHub Actions OIDC issuer and audience
    ISSUER="https://token.actions.githubusercontent.com"
    AUDIENCE="api://AzureADTokenExchange"
    
    log_info "Subject: $SUBJECT"
    log_info "Issuer: $ISSUER"
    log_info "Audience: $AUDIENCE"
    
    # Check if federated credential already exists
    if [[ "$DRY_RUN" == "false" ]]; then
        if az identity federated-credential show --name "$CREDENTIAL_NAME" --identity-name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
            log_warning "Federated credential '$CREDENTIAL_NAME' already exists. Updating..."
            execute_command "az identity federated-credential update --name '$CREDENTIAL_NAME' --identity-name '$IDENTITY_NAME' --resource-group '$RESOURCE_GROUP' --issuer '$ISSUER' --subject '$SUBJECT' --audience '$AUDIENCE'" \
                "Updating federated identity credential"
        else
            execute_command "az identity federated-credential create --name '$CREDENTIAL_NAME' --identity-name '$IDENTITY_NAME' --resource-group '$RESOURCE_GROUP' --issuer '$ISSUER' --subject '$SUBJECT' --audience '$AUDIENCE'" \
                "Creating federated identity credential"
        fi
    else
        execute_command "az identity federated-credential create --name '$CREDENTIAL_NAME' --identity-name '$IDENTITY_NAME' --resource-group '$RESOURCE_GROUP' --issuer '$ISSUER' --subject '$SUBJECT' --audience '$AUDIENCE'" \
            "Creating federated identity credential"
    fi
    
    log_success "Federated identity credentials created successfully"
}


# ================================================================================
# Display GitHub Actions configuration information for manual setup
# ================================================================================
display_github_actions_config() {
    log_info "GitHub Actions Configuration:"
    
    cat << EOF

Add the following secrets to your GitHub repository ($GITHUB_REPO):
Go to Settings > Secrets and variables > Actions

Repository Secrets:
- AZURE_CLIENT_ID: $CLIENT_ID
- AZURE_SUBSCRIPTION_ID: $(az account show --query "id" --output tsv 2>/dev/null || echo "[SUBSCRIPTION-ID]")
- AZURE_TENANT_ID: $(az account show --query "tenantId" --output tsv 2>/dev/null || echo "[TENANT-ID]")

Optional Terraform Environment Variables (if using Terraform):
- ARM_USE_AZUREAD: true
- ARM_SUBSCRIPTION_ID: $(az account show --query "id" --output tsv 2>/dev/null || echo "[SUBSCRIPTION-ID]")
- ARM_TENANT_ID: $(az account show --query "tenantId" --output tsv 2>/dev/null || echo "[TENANT-ID]")
- ARM_CLIENT_ID: $CLIENT_ID

Example GitHub Actions workflow step:
```
- name: Azure Login
  uses: azure/login@v1
  with:
    client-id: \${{ secrets.AZURE_CLIENT_ID }}
    tenant-id: \${{ secrets.AZURE_TENANT_ID }}
    subscription-id: \${{ secrets.AZURE_SUBSCRIPTION_ID }}
```

For environment-specific deployments, make sure to:
1. Create a GitHub environment named '$GITHUB_ENVIRONMENT' (if using environment-based auth)
2. Configure environment protection rules as needed
3. Add the secrets to the environment scope

Managed Identity Details:
- Name: $IDENTITY_NAME
- Resource Group: $RESOURCE_GROUP
- Client ID: $CLIENT_ID
- Principal ID: $PRINCIPAL_ID
- Identity ID: $IDENTITY_ID

EOF
}

# ================================================================================
# Create storage account for Terraform state management
# ================================================================================
create_terraform_storage() {
    if [[ "$CREATE_STORAGE" != "true" ]]; then
        return 0
    fi
    
    log_info "Creating storage account for Terraform state..."
    
    # Validate storage account name
    if [[ ${#STORAGE_ACCOUNT} -lt 3 || ${#STORAGE_ACCOUNT} -gt 24 ]]; then
        log_error "Storage account name must be between 3 and 24 characters long"
        exit 1
    fi
    
    if [[ ! "$STORAGE_ACCOUNT" =~ ^[a-z0-9]+$ ]]; then
        log_error "Storage account name must contain only lowercase letters and numbers"
        exit 1
    fi
    
    # Check if storage account already exists
    if [[ "$DRY_RUN" == "false" ]]; then
        if az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
            log_warning "Storage account '$STORAGE_ACCOUNT' already exists. Skipping creation."
            return 0
        fi
    fi
    
    # Create storage account with secure defaults
    execute_command "az storage account create \
        --name '$STORAGE_ACCOUNT' \
        --resource-group '$RESOURCE_GROUP' \
        --location '$(az group show --name $RESOURCE_GROUP --query location --output tsv)' \
        --sku 'Standard_LRS' \
        --kind 'StorageV2' \
        --access-tier 'Hot' \
        --min-tls-version 'TLS1_2' \
        --allow-blob-public-access true \
        --default-action 'Allow' \
        --bypass 'AzureServices' \
        --https-only true \
        --enable-local-user false" \
        "Creating storage account with public blob access for tfstate"
    
    # Enable versioning for better state management
    execute_command "az storage account blob-service-properties update \
        --account-name '$STORAGE_ACCOUNT' \
        --resource-group '$RESOURCE_GROUP' \
        --enable-versioning true" \
        "Enabling blob versioning for Terraform state"
    
    # Create container for Terraform state
    execute_command "az storage container create \
        --name '$STORAGE_CONTAINER' \
        --account-name '$STORAGE_ACCOUNT' \
        --auth-mode login" \
        "Creating storage container for Terraform state"
    
    log_success "Storage account '$STORAGE_ACCOUNT' created successfully"
}

# ================================================================================
# Assign storage-specific roles to managed identity for Terraform state access
# ================================================================================
assign_storage_roles() {
    if [[ "$CREATE_STORAGE" != "true" ]]; then
        return 0
    fi
    
    log_info "Assigning storage-specific roles to managed identity..."
    
    # Get storage account resource ID
    if [[ "$DRY_RUN" == "false" ]]; then
        STORAGE_ACCOUNT_ID=$(az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" --query "id" --output tsv)
    else
        STORAGE_ACCOUNT_ID="[DRY-RUN-STORAGE-ACCOUNT-ID]"
    fi
    
    # Required roles for Terraform state management
    STORAGE_ROLES=(
        "Storage Blob Data Contributor"
        "Storage Account Contributor"
    )
    
    for role in "${STORAGE_ROLES[@]}"; do
        # Check if role already assigned to make it idempotent
        if [[ "$DRY_RUN" == "false" ]]; then
            if az role assignment list --assignee "$CLIENT_ID" --role "$role" --scope "$STORAGE_ACCOUNT_ID" --query "length(@)" --output tsv | grep -q '0'; then
                log_info "No existing role assignment found for role '$role'"
            else
                log_warning "Role '$role' already assigned to managed identity. Skipping assignment."
                continue
            fi
        fi
        execute_command "az role assignment create \
            --assignee '$CLIENT_ID' \
            --role '$role' \
            --scope '$STORAGE_ACCOUNT_ID'" \
            "Assigning '$role' role for storage account"
    done
    
    log_success "Storage roles assigned successfully"
}


# ================================================================================
# Function to display Terraform backend configuration
# ================================================================================
display_terraform_backend_config() {
    if [[ "$CREATE_STORAGE" != "true" ]]; then
        return 0
    fi
    
    log_info "Terraform Backend Configuration:"
    cat << EOF

Add the following backend configuration to your Terraform files:

terraform {
  backend "azurerm" {
    resource_group_name  = "$RESOURCE_GROUP"
    storage_account_name = "$STORAGE_ACCOUNT"
    container_name       = "$STORAGE_CONTAINER"
    key                  = "terraform.tfstate"
    use_azuread_auth     = true
  }
}

Environment variables for Terraform (add to GitHub Actions):
- ARM_USE_AZUREAD: true
- ARM_SUBSCRIPTION_ID: $(az account show --query "id" --output tsv 2>/dev/null || echo "[SUBSCRIPTION-ID]")
- ARM_TENANT_ID: $(az account show --query "tenantId" --output tsv 2>/dev/null || echo "[TENANT-ID]")
- ARM_CLIENT_ID: $CLIENT_ID

Example GitHub Actions workflow step for Terraform:
```
- name: Setup Terraform
  uses: hashicorp/setup-terraform@v2
  with:
    terraform_version: 1.5.0

- name: Terraform Init
  run: terraform init
  env:
    ARM_USE_AZUREAD: true
    ARM_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
    ARM_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
    ARM_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}

- name: Terraform Plan
  run: terraform plan
  env:
    ARM_USE_AZUREAD: true
    ARM_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
    ARM_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
    ARM_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}

- name: Terraform Apply
  run: terraform apply -auto-approve
  env:
    ARM_USE_AZUREAD: true
    ARM_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
    ARM_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
    ARM_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
```

Storage Account Details:
- Name: $STORAGE_ACCOUNT
- Resource Group: $RESOURCE_GROUP
- Container: $STORAGE_CONTAINER
- Authentication: Azure AD (no storage keys required)

EOF
}

# ================================================================================
# Verify that all components were created successfully
# ================================================================================
verify_setup() {
    log_info "Verifying setup..."
    
    if [[ "$DRY_RUN" == "false" ]]; then
        # Check if identity exists
        if az identity show --name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
            log_success "Managed identity exists"
        else
            log_error "Managed identity not found"
            return 1
        fi
        
        # Check if federated credential exists
        if az identity federated-credential show --name "$CREDENTIAL_NAME" --identity-name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
            log_success "Federated credential exists"
        else
            log_error "Federated credential not found"
            return 1
        fi
        # Check role assignments
        ROLE_COUNT=$(az role assignment list --assignee "$CLIENT_ID" --scope "$CONTRIBUTOR_SCOPE" --query "length(@)" --output tsv)
        if [[ "$ROLE_COUNT" -gt 0 ]]; then
            log_success "Role assignments configured ($ROLE_COUNT roles)"
        else
            log_warning "! No role assignments found"
        fi
        
        # Check storage account if created
        if [[ "$CREATE_STORAGE" == "true" ]]; then
            if az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
                log_success "Storage account exists"
                
                # Check if container exists
                if az storage container show --name "$STORAGE_CONTAINER" --account-name "$STORAGE_ACCOUNT" --auth-mode login &> /dev/null; then
                    log_success "Storage container exists"
                else
                    log_error "Storage container not found"
                    return 1
                fi
            else
                log_error "Storage account not found"
                return 1
            fi
        fi
    else
        log_info "[DRY-RUN] Would verify setup"
    fi
    
    log_success "Setup verification completed"
}

# ================================================================================
# Create GitHub environment and secrets automatically using GitHub CLI
# ================================================================================
create_github_secrets(){
    # check if github cli is installed
    if ! command -v gh &> /dev/null; then
        log_error "GitHub CLI (gh) is not installed. Please install it from https://cli.github.com/"
        exit 1
    fi
    # check if admin access to specified repository is available
    if ! gh repo view "$GITHUB_REPO" &> /dev/null; then
        log_error "Invalid access to repository: $GITHUB_REPO"
        return 1
    fi
    
    log_info "Checking GitHub permissions for repository operations..."
    
    # Try to list environments to check permissions
    if ! gh api "repos/$GITHUB_REPO/environments" &> /dev/null; then
        log_warning "May not have sufficient permissions to manage environments and secrets"
        log_info "Required GitHub token scopes:"
        echo "  - repo (full repository access)"
        echo "  - admin:repo_hook (if using webhooks)"
        echo "  - admin:org (if repository is in an organization)"
        return 1
    fi
    
    # now create the environment if it does not exist and then add the secrets
    log_info "Creating GitHub environment: $GITHUB_ENVIRONMENT"

    # Check if environment already exists
    if gh api "repos/$GITHUB_REPO/environments/$GITHUB_ENVIRONMENT" &> /dev/null; then
        log_warning "Environment $GITHUB_ENVIRONMENT already exists. Will update secrets."
    else
        # Create environment with proper JSON
        local github_env_file
        github_env_file=$(create_temp_file)
        cat > "$github_env_file" << EOF
            {
                "wait_timer": 0,
                "reviewers": []
            }
EOF

        gh api "repos/$GITHUB_REPO/environments/$GITHUB_ENVIRONMENT" \
            --method PUT \
            --input "$github_env_file" \
            > /dev/null

        log_success "Environment $GITHUB_ENVIRONMENT created successfully"
    fi
    

    # Add secrets to the environment
    log_info "Adding secrets to GitHub environment '$GITHUB_ENVIRONMENT'..."
    # Add environment-specific secrets
    gh secret set AZURE_CLIENT_ID \
        --repo "$GITHUB_REPO" \
        --env "$GITHUB_ENVIRONMENT" \
        --body "$CLIENT_ID"
    gh secret set AZURE_SUBSCRIPTION_ID \
        --repo "$GITHUB_REPO" \
        --env "$GITHUB_ENVIRONMENT" \
        --body "$(az account show --query "id" --output tsv 2>/dev/null || echo "[SUBSCRIPTION-ID]")"
    gh secret set AZURE_TENANT_ID \
        --repo "$GITHUB_REPO" \
        --env "$GITHUB_ENVIRONMENT" \
        --body "$(az account show --query "tenantId" --output tsv 2>/dev/null || echo "[TENANT-ID]")"
    gh secret set VNET_NAME \
        --repo "$GITHUB_REPO" \
        --env "$GITHUB_ENVIRONMENT" \
        --body "$(echo "$RESOURCE_GROUP" | sed 's/-networking/-vwan-spoke/')"
    gh secret set VNET_RESOURCE_GROUP_NAME \
        --repo "$GITHUB_REPO" \
        --env "$GITHUB_ENVIRONMENT" \
        --body "$RESOURCE_GROUP"

    log_success "Secrets added to GitHub environment '$GITHUB_ENVIRONMENT'."
    return 0

}

# ================================================================================
# Main function that orchestrates the entire setup process
# ================================================================================
main() {
    log_info "Starting GitHub Actions OIDC setup for Azure Landing Zone..."
    log_info "Repository: $GITHUB_REPO"
    log_info "Environment: $GITHUB_ENVIRONMENT"
    log_info "Resource Group: $RESOURCE_GROUP"
    log_info "Identity Name: $IDENTITY_NAME"
    
    # Step 1: Validate prerequisites and environment
    check_prerequisites
    check_resource_group

    # Step 2: Generate storage account name if storage creation is requested
    if [[ "$CREATE_STORAGE" == "true" ]]; then
        generate_storage_account_name
        log_info "Will create Terraform state storage: $STORAGE_ACCOUNT"
    fi

    # Step 3: Create and configure the managed identity
    create_managed_identity
    get_identity_details

    # Step 4: Allow time for Azure AD to propagate the new identity
    # This prevents race conditions when assigning roles immediately after creation
    if [[ "$DRY_RUN" == "false" ]]; then
        log_info "Waiting 10 seconds for managed identity propagation in Azure AD..."
        sleep 10
    fi

    # Step 5: Assign Azure roles for deployment permissions
    assign_roles
    
    # Step 6: Create Terraform state storage if requested
    create_terraform_storage
    assign_storage_roles
    
    # Step 7: Configure OIDC federated identity credentials for GitHub Actions
    create_federated_credentials
    
    # Step 8: Automatically create GitHub environment and secrets if requested
    create_github_secrets
    
    # Step 9: Verify the complete setup
    verify_setup

    # Step 10: Display configuration information (only if not auto-creating secrets)
    if [[ "$DRY_RUN" == "false" ]]; then
        if [[ "$CREATE_GITHUB_SECRETS" == "false" ]]; then
            display_github_actions_config
            display_terraform_backend_config
        fi
    fi

    # Final success message
    log_success "GitHub Actions OIDC setup completed successfully!"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "This was a dry run. No actual changes were made."
        log_info "Run the script without --dry-run to apply the changes."
    else
        log_info "Your GitHub Actions workflows can now authenticate to Azure using OIDC!"
        if [[ "$CREATE_GITHUB_SECRETS" == "true" ]]; then
            log_info "GitHub environment '$GITHUB_ENVIRONMENT' and secrets have been configured automatically."
        else
            log_info "Copy the displayed configuration to your GitHub repository secrets."
        fi
    fi
}

# Execute the main function with all provided arguments
main "$@"