#!/bin/bash

# =============================================================================
# Azure Container Infrastructure Deployment Script
# =============================================================================
# 
# This script provides a production-ready automation solution for building containers 
# and managing Terraform infrastructure for Azure Container Instances (ACI) and 
# Container Apps (ACA) deployments.
#
# FEATURES:
# - Parallel container building with caching support
# - Terraform operations (plan/apply/destroy)
# - Configurable tfvars files
# - Comprehensive error handling and logging
# - Production-ready security practices
# - Enhanced Azure authentication and permissions validation
#
# PREREQUISITES:
# - Docker installed and running
# - Terraform >= 1.0 installed
# - Azure CLI installed and authenticated with proper permissions
# - Git (for image tagging)
# - Bash 4.0+ (for associative arrays)
# - jq (optional, for enhanced JSON parsing)
#
# AZURE PERMISSIONS REQUIRED:
# - Reader or Contributor access to target subscription
# - Reader access to backend resource group: b9cee3-tools-networking
# - Storage Account Contributor on backend storage: tftoolsquickstartazureco
# - Storage Blob Data Contributor for Terraform state management
#
# USAGE EXAMPLES:
# ----------------
# Basic deployment with default tfvars:
#   ./deploy.sh apply
#
# Plan deployment with custom tfvars:
#   ./deploy.sh plan --tfvars=production.tfvars
#
# Build containers only:
#   ./deploy.sh build
#
# Destroy infrastructure with confirmation:
#   ./deploy.sh destroy --tfvars=staging.tfvars
#
# Build and deploy in one command:
#   ./deploy.sh apply --build --tfvars=development.tfvars
#
# Force rebuild containers (no cache):
#   ./deploy.sh build --no-cache
#
# Validate configuration only:
#   ./deploy.sh validate --tfvars=production.tfvars
#
# Override backend configuration with environment variables:
#   BACKEND_RESOURCE_GROUP="my-rg" BACKEND_STORAGE_ACCOUNT="mysa" ./deploy.sh apply
#
# CONTAINER IMAGE HANDLING:
# -------------------------
# By default, the script dynamically generates container image tags using git commit hash:
# - quickstart-azure-containers/backend:abc1234
# - quickstart-azure-containers/frontend:abc1234
# - quickstart-azure-containers/migrations:abc1234
#
# These are exported as TF_VAR_* environment variables and override static tfvars values.
# 
# To use static images from tfvars instead, use --static-images flag:
#   ./deploy.sh apply --static-images --tfvars=production.tfvars
#
# BACKEND CONFIGURATION:
# ----------------------
# The script uses Azure Storage backend for Terraform state management.
# Default configuration:
#   - Resource Group: b9cee3-tools-networking
#   - Storage Account: tftoolsquickstartazureco
#   - State Key: quick-7fed/tools/terraform.tfstate
#
# Override with environment variables:
#   export BACKEND_RESOURCE_GROUP="your-backend-rg"
#   export BACKEND_STORAGE_ACCOUNT="yourstorageaccount"
#   export BACKEND_STATE_KEY="your-project/environment/terraform.tfstate"
#
# =============================================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# =============================================================================
# GLOBAL CONFIGURATION
# =============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly INFRA_DIR="${SCRIPT_DIR}/infra"
readonly LOG_DIR="${SCRIPT_DIR}/logs"
readonly DEFAULT_TFVARS="terraform.tfvars"
readonly TIMESTAMP=$(date +%Y%m%d_%H%M%S)
readonly LOG_FILE="${LOG_DIR}/deploy_${TIMESTAMP}.log"

# Container configuration
declare -A CONTAINERS=(
  ["backend"]="${SCRIPT_DIR}/backend"
  ["frontend"]="${SCRIPT_DIR}/frontend"
  ["migrations"]="${SCRIPT_DIR}/migrations"
)

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Global variables
TERRAFORM_COMMAND=""
TFVARS_FILE=""
BUILD_CONTAINERS=false
NO_CACHE=false
VERBOSE=false
DRY_RUN=false
USE_STATIC_IMAGES=false

# Backend configuration (can be overridden by environment variables)
BACKEND_RESOURCE_GROUP="${BACKEND_RESOURCE_GROUP:-b9cee3-tools-networking}"
BACKEND_STORAGE_ACCOUNT="${BACKEND_STORAGE_ACCOUNT:-tfstateazureaipoctools}"
BACKEND_STATE_KEY="${BACKEND_STATE_KEY:-azure-ai-poc/tools/terraform.tfstate}"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

#
# Logs messages with timestamp and color coding
# Arguments:
#   $1: Log level (INFO, WARN, ERROR, SUCCESS)
#   $2: Message to log
# Outputs:
#   Formatted log message to stdout and log file
#
log() {
  local level="$1"
  local message="$2"
  local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  local color=""
  
  case "$level" in
    "INFO")  color="$BLUE" ;;
    "WARN")  color="$YELLOW" ;;
    "ERROR") color="$RED" ;;
    "SUCCESS") color="$GREEN" ;;
  esac
  
  # Create log directory if it doesn't exist
  mkdir -p "$LOG_DIR"
  
  # Log to file (without colors)
  echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
  
  # Log to stdout (with colors)
  echo -e "${color}[$timestamp] [$level] $message${NC}"
}

#
# Displays usage information and exits
# Arguments: None
# Outputs: Usage information to stdout
#
usage() {
  cat << EOF
Usage: $0 <command> [options]

COMMANDS:
  plan        Generate and show Terraform execution plan
  apply       Apply Terraform configuration to create/update infrastructure
  destroy     Destroy Terraform-managed infrastructure
  build       Build container images only
  validate    Validate Terraform configuration

OPTIONS:
  --tfvars=FILE        Specify Terraform variables file (default: terraform.tfvars)
  --build              Also build containers before Terraform operations
  --no-cache           Build containers without using cache
  --static-images      Use static image values from tfvars (don't override with git tags)
  --verbose            Enable verbose output
  --dry-run            Show what would be done without executing
  --help               Show this help message

EXAMPLES:
  $0 apply                                    # Deploy with default tfvars and dynamic images
  $0 plan --tfvars=prod.tfvars               # Plan with custom tfvars
  $0 build --no-cache                        # Force rebuild all containers
  $0 apply --build --tfvars=dev.tfvars       # Build and deploy with dynamic images
  $0 apply --static-images                   # Deploy using static images from tfvars
  $0 destroy --tfvars=staging.tfvars         # Destroy staging environment

EOF
  exit 0
}

#
# Validates Azure CLI session and permissions
# Arguments: None
# Returns: 0 if Azure session is valid, 1 otherwise
#
validate_azure_session() {
  log "INFO" "Validating Azure CLI session..."
  
  # Check if Azure CLI is authenticated
  if ! az account show &> /dev/null; then
    log "ERROR" "Azure CLI is not authenticated"
    log "ERROR" "Please run 'az login' to authenticate with Azure"
    log "ERROR" "If using a service principal, ensure AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID are set"
    return 1
  fi
  
  # Test access token validity with more comprehensive error handling
  local token_test_output
  local token_test_exit_code
  
  log "INFO" "Testing Azure access token validity..."
  token_test_output=$(az account get-access-token --output json 2>&1)
  token_test_exit_code=$?
  
  if [ $token_test_exit_code -ne 0 ]; then
    log "ERROR" "Azure access token validation failed"
    
    # Check for specific error patterns
    if echo "$token_test_output" | grep -q "AADSTS70043"; then
      log "ERROR" "Azure token has expired due to conditional access policies"
      log "ERROR" "The refresh token has expired or is invalid due to sign-in frequency checks"
    elif echo "$token_test_output" | grep -q "AADSTS"; then
      log "ERROR" "Azure Active Directory authentication error detected"
    elif echo "$token_test_output" | grep -q "expired"; then
      log "ERROR" "Azure token has expired"
    else
      log "ERROR" "Unknown Azure authentication error:"
      echo "$token_test_output" | while IFS= read -r line; do
        log "ERROR" "  $line"
      done
    fi
    
    log "ERROR" "Please reauthenticate with Azure:"
    log "ERROR" "  1. Run 'az logout' to clear existing session"
    log "ERROR" "  2. Run 'az login' to authenticate interactively"
    log "ERROR" "  3. If using conditional access, you may need to authenticate more frequently"
    return 1
  fi
  
  # Get current account information
  local account_info
  if ! account_info=$(az account show --output json 2>/dev/null); then
    log "ERROR" "Failed to retrieve Azure account information"
    log "ERROR" "Your Azure session may have expired. Please run 'az login' again"
    return 1
  fi
  
  # Extract account details with proper error handling
  local subscription_id="unknown"
  local subscription_name="unknown"
  local tenant_id="unknown"
  local user_name="unknown"
  local user_type="unknown"
  local state="unknown"
  
  if command -v jq &> /dev/null; then
    subscription_id=$(echo "$account_info" | jq -r '.id // "unknown"' 2>/dev/null || echo "unknown")
    subscription_name=$(echo "$account_info" | jq -r '.name // "unknown"' 2>/dev/null || echo "unknown")
    tenant_id=$(echo "$account_info" | jq -r '.tenantId // "unknown"' 2>/dev/null || echo "unknown")
    user_name=$(echo "$account_info" | jq -r '.user.name // "unknown"' 2>/dev/null || echo "unknown")
    user_type=$(echo "$account_info" | jq -r '.user.type // "unknown"' 2>/dev/null || echo "unknown")
    state=$(echo "$account_info" | jq -r '.state // "unknown"' 2>/dev/null || echo "unknown")
  else
    log "WARN" "jq is not installed. JSON parsing will be limited"
    log "WARN" "Consider installing jq for better Azure session validation"
    # Use basic parsing without jq
    subscription_id=$(echo "$account_info" | grep -o '"id": *"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo "unknown")
    subscription_name=$(echo "$account_info" | grep -o '"name": *"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo "unknown")
    tenant_id=$(echo "$account_info" | grep -o '"tenantId": *"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo "unknown")
    state=$(echo "$account_info" | grep -o '"state": *"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo "unknown")
  fi
  
  # Validate subscription state
  if [ "$state" != "Enabled" ]; then
    log "ERROR" "Azure subscription is not enabled. Current state: $state"
    log "ERROR" "Please contact your Azure administrator to enable the subscription"
    return 1
  fi
  
  # Check token expiration timing (if jq is available)
  local token_expiry
  if command -v jq &> /dev/null; then
    # Parse the token we already fetched
    local token_info
    if token_info=$(echo "$token_test_output" | jq -r '.expiresOn // "unknown"' 2>/dev/null); then
      if [ "$token_info" != "unknown" ] && [ -n "$token_info" ]; then
        local current_time=$(date +%s)
        local expiry_time=$(date -d "$token_info" +%s 2>/dev/null || echo "0")
        local time_remaining=$((expiry_time - current_time))
        
        if [ "$time_remaining" -lt 300 ]; then  # Less than 5 minutes
          log "WARN" "Azure token expires soon (in ${time_remaining}s)"
          log "WARN" "Consider refreshing with 'az login' before long-running operations"
          if [ "$time_remaining" -lt 0 ]; then
            log "ERROR" "Azure token has expired. Please run 'az login' to reauthenticate"
            return 1
          fi
        else
          log "INFO" "Azure token valid for $(($time_remaining / 60)) minutes"
        fi
      fi
    fi
  fi
  
  # Validate backend resource access with better error handling
  log "INFO" "Validating access to backend storage resources..."
  
  # Check if backend resource group exists and is accessible
  local rg_check_output
  local rg_check_exit_code
  
  rg_check_output=$(az group show --name "$BACKEND_RESOURCE_GROUP" 2>&1)
  rg_check_exit_code=$?
  
  if [ $rg_check_exit_code -ne 0 ]; then
    log "ERROR" "Cannot access backend resource group: $BACKEND_RESOURCE_GROUP"
    
    # Check for specific error patterns
    if echo "$rg_check_output" | grep -q "ResourceGroupNotFound"; then
      log "ERROR" "Resource group does not exist"
    elif echo "$rg_check_output" | grep -q "AuthorizationFailed"; then
      log "ERROR" "Insufficient permissions to access resource group"
    elif echo "$rg_check_output" | grep -q "AADSTS"; then
      log "ERROR" "Authentication error when accessing resource group"
      log "ERROR" "Your session may have expired during validation"
    else
      log "ERROR" "Unknown error accessing resource group:"
      echo "$rg_check_output" | head -3 | while IFS= read -r line; do
        log "ERROR" "  $line"
      done
    fi
    
    log "ERROR" "Please verify:"
    log "ERROR" "  1. Resource group '$BACKEND_RESOURCE_GROUP' exists"
    log "ERROR" "  2. You have Reader permissions or higher on the resource group"
    log "ERROR" "  3. You're using the correct subscription: $subscription_name"
    log "ERROR" "  4. Your Azure session is valid (try 'az login' again)"
    return 1
  fi
  
  # Check if backend storage account exists and is accessible
  local sa_check_output
  local sa_check_exit_code
  
  sa_check_output=$(az storage account show --name "$BACKEND_STORAGE_ACCOUNT" --resource-group "$BACKEND_RESOURCE_GROUP" 2>&1)
  sa_check_exit_code=$?
  
  if [ $sa_check_exit_code -ne 0 ]; then
    log "ERROR" "Cannot access backend storage account: $BACKEND_STORAGE_ACCOUNT"
    
    # Check for specific error patterns
    if echo "$sa_check_output" | grep -q "StorageAccountNotFound"; then
      log "ERROR" "Storage account does not exist"
    elif echo "$sa_check_output" | grep -q "AuthorizationFailed"; then
      log "ERROR" "Insufficient permissions to access storage account"
    elif echo "$sa_check_output" | grep -q "AADSTS"; then
      log "ERROR" "Authentication error when accessing storage account"
      log "ERROR" "Your session may have expired during validation"
    else
      log "ERROR" "Unknown error accessing storage account:"
      echo "$sa_check_output" | head -3 | while IFS= read -r line; do
        log "ERROR" "  $line"
      done
    fi
    
    log "ERROR" "Please verify:"
    log "ERROR" "  1. Storage account exists in resource group: $BACKEND_RESOURCE_GROUP"
    log "ERROR" "  2. You have Storage Account Contributor permissions or higher"
    log "ERROR" "  3. Storage account name is correct: $BACKEND_STORAGE_ACCOUNT"
    log "ERROR" "  4. Your Azure session is valid (try 'az login' again)"
    return 1
  fi
  
  # Test storage account access by attempting to list containers (optional check)
  local container_check_output
  local container_check_exit_code
  
  container_check_output=$(az storage container list --account-name "$BACKEND_STORAGE_ACCOUNT" --auth-mode login 2>&1)
  container_check_exit_code=$?
  
  if [ $container_check_exit_code -ne 0 ]; then
    # Check if it's an authentication issue
    if echo "$container_check_output" | grep -q "AADSTS"; then
      log "ERROR" "Authentication error when accessing storage containers"
      log "ERROR" "Your session may have expired during validation"
      log "ERROR" "Please run 'az login' to reauthenticate"
      return 1
    else
      log "WARN" "Limited access to storage account containers"
      log "WARN" "Terraform state operations may fail if proper permissions are not configured"
      log "WARN" "Ensure you have 'Storage Blob Data Contributor' role or equivalent"
    fi
  fi
  
  log "SUCCESS" "Azure session validation completed"
  log "INFO" "Subscription: $subscription_name ($subscription_id)"
  log "INFO" "Tenant: $tenant_id"
  log "INFO" "User: $user_name ($user_type)"
  log "INFO" "Backend RG: $BACKEND_RESOURCE_GROUP"
  log "INFO" "Backend SA: $BACKEND_STORAGE_ACCOUNT"
  
  return 0
}

#
# Validates that all required tools are installed and accessible
# Arguments: None
# Returns: 0 if all tools are available, 1 otherwise
#
check_prerequisites() {
  log "INFO" "Checking prerequisites..."
  
  local tools=("docker" "terraform" "az" "git")
  local missing_tools=()
  
  for tool in "${tools[@]}"; do
    if ! command -v "$tool" &> /dev/null; then
      missing_tools+=("$tool")
    fi
  done
  
  if [ ${#missing_tools[@]} -ne 0 ]; then
    log "ERROR" "Missing required tools: ${missing_tools[*]}"
    log "ERROR" "Please install the missing tools and try again"
    return 1
  fi
  
  # Check Docker daemon
  if ! docker info &> /dev/null; then
    log "ERROR" "Docker daemon is not running. Please start Docker and try again"
    return 1
  fi
  
  # Comprehensive Azure session validation
  if ! validate_azure_session; then
    return 1
  fi
  
  # Check Terraform version
  local tf_version
  tf_version=$(terraform version -json | jq -r '.terraform_version' 2>/dev/null || echo "unknown")
  log "INFO" "Using Terraform version: $tf_version"
  
  log "SUCCESS" "All prerequisites are satisfied"
  return 0
}

#
# Validates the Terraform variables file exists and is readable
# Arguments:
#   $1: Path to tfvars file
# Returns: 0 if file is valid, 1 otherwise
#
validate_tfvars_file() {
  local tfvars_file="$1"
  
  if [ ! -f "$tfvars_file" ]; then
    log "ERROR" "Terraform variables file not found: $tfvars_file"
    log "INFO" "Available tfvars files in infra directory:"
    find "$INFRA_DIR" -name "*.tfvars" -exec basename {} \; 2>/dev/null || true
    return 1
  fi
  
  if [ ! -r "$tfvars_file" ]; then
    log "ERROR" "Cannot read Terraform variables file: $tfvars_file"
    return 1
  fi
  
  log "INFO" "Using Terraform variables file: $tfvars_file"
  return 0
}

# =============================================================================
# CONTAINER BUILDING FUNCTIONS
# =============================================================================

#
# Gets the current Git commit hash for container tagging
# Arguments: None
# Outputs: Git commit hash (short format)
# Returns: 0 on success, 1 if not in a git repository
#
get_git_commit() {
  if git rev-parse --git-dir > /dev/null 2>&1; then
    git rev-parse --short HEAD
  else
    echo "latest"
  fi
}

#
# Exports built container image names as environment variables for Terraform
# Arguments: None
# Outputs: Sets TF_VAR_* environment variables for container images
#
export_container_images() {
  # Skip if user wants to use static images from tfvars
  if [ "$USE_STATIC_IMAGES" = true ]; then
    log "INFO" "Using static container images from tfvars file (--static-images flag set)"
    return 0
  fi
  
  local git_commit
  git_commit=$(get_git_commit)
  
  log "INFO" "Exporting container image variables for Terraform..."
  
  # Export container images with current git commit tag
  export TF_VAR_api_image="quickstart-azure-containers/backend:${git_commit}"
  export TF_VAR_frontend_image="quickstart-azure-containers/frontend:${git_commit}"
  export TF_VAR_flyway_image="quickstart-azure-containers/migrations:${git_commit}"
  
  log "INFO" "Exported container image variables:"
  log "INFO" "  TF_VAR_api_image=${TF_VAR_api_image}"
  log "INFO" "  TF_VAR_frontend_image=${TF_VAR_frontend_image}"
  log "INFO" "  TF_VAR_flyway_image=${TF_VAR_flyway_image}"
  log "INFO" "These variables override any static values in the tfvars file"
}

#
# Builds a single container with proper tagging and caching
# Arguments:
#   $1: Container name (backend, frontend, migrations)
#   $2: Container directory path
# Returns: 0 on successful build, 1 on failure
#
build_container() {
  local container_name="$1"
  local container_dir="$2"
  local git_commit
  git_commit=$(get_git_commit)
  
  log "INFO" "Building container: $container_name"
  
  if [ ! -d "$container_dir" ]; then
    log "ERROR" "Container directory not found: $container_dir"
    return 1
  fi
  
  if [ ! -f "$container_dir/Dockerfile" ]; then
    log "ERROR" "Dockerfile not found in: $container_dir"
    return 1
  fi
  
  local image_name="quickstart-azure-containers/${container_name}"
  local cache_args=""
  
  # Build cache arguments
  if [ "$NO_CACHE" = false ]; then
    cache_args="--cache-from ${image_name}:latest"
  else
    cache_args="--no-cache"
    log "INFO" "Building without cache for $container_name"
  fi
  
  local build_args=""
  build_args+=" --tag ${image_name}:${git_commit}"
  build_args+=" --tag ${image_name}:latest"
  build_args+=" --file ${container_dir}/Dockerfile"
  build_args+=" $cache_args"
  
  if [ "$VERBOSE" = true ]; then
    build_args+=" --progress=plain"
  fi
  
  # Execute build
  if [ "$DRY_RUN" = true ]; then
    log "INFO" "[DRY RUN] Would execute: docker build $build_args $container_dir"
  else
    log "INFO" "Executing: docker build $build_args $container_dir"
    if docker build $build_args "$container_dir"; then
      log "SUCCESS" "Successfully built container: $container_name:$git_commit"
    else
      log "ERROR" "Failed to build container: $container_name"
      return 1
    fi
  fi
  
  return 0
}

#
# Builds a single container in the background for parallel execution
# Arguments:
#   $1: Container name (backend, frontend, migrations)
#   $2: Container directory path
#   $3: Log file path for this container
# Returns: 0 on successful build, 1 on failure
#
build_container_parallel() {
  local container_name="$1"
  local container_dir="$2"
  local container_log="$3"
  local git_commit
  git_commit=$(get_git_commit)
  
  # Redirect all output to container-specific log file
  exec 1>"$container_log" 2>&1
  
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] Building container: $container_name"
  
  if [ ! -d "$container_dir" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] Container directory not found: $container_dir"
    return 1
  fi
  
  if [ ! -f "$container_dir/Dockerfile" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] Dockerfile not found in: $container_dir"
    return 1
  fi
  
  local image_name="quickstart-azure-containers/${container_name}"
  local cache_args=""
  
  # Build cache arguments
  if [ "$NO_CACHE" = false ]; then
    cache_args="--cache-from ${image_name}:latest"
  else
    cache_args="--no-cache"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] Building without cache for $container_name"
  fi
  
  local build_args=""
  build_args+=" --tag ${image_name}:${git_commit}"
  build_args+=" --tag ${image_name}:latest"
  build_args+=" --file ${container_dir}/Dockerfile"
  build_args+=" $cache_args"
  
  if [ "$VERBOSE" = true ]; then
    build_args+=" --progress=plain"
  fi
  
  # Execute build
  if [ "$DRY_RUN" = true ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] [DRY RUN] Would execute: docker build $build_args $container_dir"
  else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] Executing: docker build $build_args $container_dir"
    if docker build $build_args "$container_dir"; then
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SUCCESS] Successfully built container: $container_name:$git_commit"
    else
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] Failed to build container: $container_name"
      return 1
    fi
  fi
  
  return 0
}

#
# Builds all containers defined in the CONTAINERS array in parallel
# Arguments: None
# Returns: 0 if all builds succeed, 1 if any build fails
#
build_all_containers() {
  log "INFO" "Starting parallel container build process..."
  
  # Use local associative arrays with proper declaration
  local -A local_build_pids
  local -A local_container_logs
  local failed_builds=()
  local build_start_time=$(date +%s)
  
  # Create temporary directory for container build logs
  local temp_log_dir="${LOG_DIR}/container_builds_${TIMESTAMP}"
  mkdir -p "$temp_log_dir"
  
  # Start builds in parallel
  for container_name in "${!CONTAINERS[@]}"; do
    local container_dir="${CONTAINERS[$container_name]}"
    local container_log="${temp_log_dir}/${container_name}_build.log"
    local_container_logs["$container_name"]="$container_log"
    
    log "INFO" "Starting build for container: $container_name"
    
    # Start build in background
    (
      export NO_CACHE DRY_RUN VERBOSE
      build_container_parallel "$container_name" "$container_dir" "$container_log"
    ) &
    
    local pid=$!
    local_build_pids["$container_name"]=$pid
    
    log "INFO" "Container $container_name build started with PID: $pid"
  done
  
  log "INFO" "All container builds started. Waiting for completion..."
  
  # Wait for all builds to complete and collect results
  for container_name in "${!local_build_pids[@]}"; do
    local pid="${local_build_pids[$container_name]}"
    local container_log="${local_container_logs[$container_name]}"
    
    log "INFO" "Waiting for container build: $container_name (PID: $pid)"
    
    # Wait for the specific process
    if wait "$pid"; then
      log "SUCCESS" "Container build completed: $container_name"
      
      # Show last few lines of the build log for success confirmation
      if [ "$VERBOSE" = true ] && [ -f "$container_log" ]; then
        log "INFO" "Build output for $container_name (last 10 lines):"
        tail -n 10 "$container_log" | while IFS= read -r line; do
          echo "  $line"
        done
      fi
    else
      log "ERROR" "Container build failed: $container_name"
      failed_builds+=("$container_name")
      
      # Show error output
      if [ -f "$container_log" ]; then
        log "ERROR" "Build errors for $container_name:"
        tail -n 20 "$container_log" | while IFS= read -r line; do
          echo "  $line"
        done
      fi
    fi
  done
  
  local build_end_time=$(date +%s)
  local build_duration=$((build_end_time - build_start_time))
  
  # Clean up or preserve logs based on result
  if [ ${#failed_builds[@]} -eq 0 ]; then
    log "SUCCESS" "All containers built successfully in parallel (${build_duration}s)"
    
    # Archive successful build logs
    if [ "$VERBOSE" = true ]; then
      log "INFO" "Build logs preserved in: $temp_log_dir"
    else
      # Clean up successful build logs if not verbose
      rm -rf "$temp_log_dir" 2>/dev/null || true
    fi
    
    return 0
  else
    log "ERROR" "Failed to build containers: ${failed_builds[*]} (${build_duration}s)"
    log "ERROR" "Build logs preserved for debugging in: $temp_log_dir"
    return 1
  fi
}

# =============================================================================
# TERRAFORM FUNCTIONS
# =============================================================================

#
# Initializes Terraform with backend configuration and provider downloads
# Uses Azure Storage backend for state management
# Arguments: None
# Returns: 0 on success, 1 on failure
#
terraform_init() {
  log "INFO" "Initializing Terraform with Azure Storage backend..."
  
  # Backend configuration for Azure Storage (configurable via environment variables)
  local backend_config_rg="resource_group_name=$BACKEND_RESOURCE_GROUP"
  local backend_config_sa="storage_account_name=$BACKEND_STORAGE_ACCOUNT"
  local backend_config_key="key=$BACKEND_STATE_KEY"
  
  local init_args="-upgrade -reconfigure"
  init_args+=" -backend-config=$backend_config_rg"
  init_args+=" -backend-config=$backend_config_sa"
  init_args+=" -backend-config=$backend_config_key"
  
  if [ "$VERBOSE" = false ]; then
    init_args+=" -no-color"
  fi
  
  cd "$INFRA_DIR"
  
  if [ "$DRY_RUN" = true ]; then
    log "INFO" "[DRY RUN] Would execute: terraform init $init_args"
  else
    log "INFO" "Configuring backend with:"
    log "INFO" "  Resource Group: $BACKEND_RESOURCE_GROUP"
    log "INFO" "  Storage Account: $BACKEND_STORAGE_ACCOUNT"
    log "INFO" "  State Key: $BACKEND_STATE_KEY"
    
    if terraform init $init_args; then
      log "SUCCESS" "Terraform initialized successfully with Azure Storage backend"
    else
      log "ERROR" "Terraform initialization failed"
      log "ERROR" "Please verify:"
      log "ERROR" "  1. Storage account '$BACKEND_STORAGE_ACCOUNT' exists"
      log "ERROR" "  2. Resource group '$BACKEND_RESOURCE_GROUP' exists"
      log "ERROR" "  3. You have proper permissions to the storage account"
      log "ERROR" "  4. Azure CLI is authenticated"
      return 1
    fi
  fi
  
  return 0
}

#
# Validates Terraform configuration files
# Arguments: None
# Returns: 0 if valid, 1 if validation fails
#
terraform_validate() {
  log "INFO" "Validating Terraform configuration..."
  
  cd "$INFRA_DIR"
  
  if [ "$DRY_RUN" = true ]; then
    log "INFO" "[DRY RUN] Would execute: terraform validate"
  else
    if terraform validate; then
      log "SUCCESS" "Terraform configuration is valid"
    else
      log "ERROR" "Terraform validation failed"
      return 1
    fi
  fi
  
  return 0
}

#
# Executes terraform plan with specified variables file
# Arguments: None
# Returns: 0 on success, 1 on failure
#
terraform_plan() {
  log "INFO" "Creating Terraform execution plan..."
  
  local plan_args="-var-file=$TFVARS_FILE"
  local plan_file="${INFRA_DIR}/tfplan_${TIMESTAMP}.out"
  
  if [ "$VERBOSE" = false ]; then
    plan_args+=" -no-color"
  fi
  
  plan_args+=" -out=$plan_file"
  
  cd "$INFRA_DIR"
  
  if [ "$DRY_RUN" = true ]; then
    log "INFO" "[DRY RUN] Would execute: terraform plan $plan_args"
  else
    if terraform plan $plan_args; then
      log "SUCCESS" "Terraform plan created successfully"
      log "INFO" "Plan saved to: $plan_file"
    else
      log "ERROR" "Terraform plan failed"
      return 1
    fi
  fi
  
  return 0
}

#
# Executes terraform apply with specified variables file
# Arguments: None
# Returns: 0 on success, 1 on failure
#
terraform_apply() {
  log "INFO" "Applying Terraform configuration..."
  
  local apply_args="-var-file=$TFVARS_FILE"
  
  if [ "$VERBOSE" = false ]; then
    apply_args+=" -no-color"
  fi
  
  # Auto-approve only in non-interactive environments or if explicitly set
  if [ "${CI:-false}" = "true" ] || [ "${AUTO_APPROVE:-false}" = "true" ]; then
    apply_args+=" -auto-approve"
    log "INFO" "Auto-approve enabled for non-interactive environment"
  else
    log "WARN" "Interactive approval required for apply operation"
  fi
  
  cd "$INFRA_DIR"
  
  if [ "$DRY_RUN" = true ]; then
    log "INFO" "[DRY RUN] Would execute: terraform apply $apply_args"
  else
    if terraform apply $apply_args; then
      log "SUCCESS" "Terraform apply completed successfully"
      
      # Show outputs
      log "INFO" "Terraform outputs:"
      terraform output || log "WARN" "No outputs available or output command failed"
      
      # Generate Azure portal link
      local subscription_id
      subscription_id=$(az account show --query id -o tsv 2>/dev/null || echo "unknown")
      if [ "$subscription_id" != "unknown" ]; then
        local resource_group
        resource_group=$(terraform output -raw resource_group_name 2>/dev/null || echo "unknown")
        if [ "$resource_group" != "unknown" ]; then
          log "INFO" "Azure Portal: https://portal.azure.com/#@/resource/subscriptions/$subscription_id/resourceGroups/$resource_group"
        fi
      fi
    else
      log "ERROR" "Terraform apply failed"
      return 1
    fi
  fi
  
  return 0
}

#
# Executes terraform destroy with specified variables file
# Arguments: None
# Returns: 0 on success, 1 on failure
#
terraform_destroy() {
  log "WARN" "DESTRUCTIVE OPERATION: This will destroy all Terraform-managed infrastructure"
  
  # Confirmation prompt (skip in CI or if auto-approved)
  if [ "${CI:-false}" != "true" ] && [ "${AUTO_APPROVE:-false}" != "true" ] && [ "$DRY_RUN" = false ]; then
    read -p "Are you sure you want to destroy the infrastructure? Type 'yes' to confirm: " -r
    if [ "$REPLY" != "yes" ]; then
      log "INFO" "Destroy operation cancelled"
      return 0
    fi
  fi
  
  local destroy_args="-var-file=$TFVARS_FILE"
  
  if [ "$VERBOSE" = false ]; then
    destroy_args+=" -no-color"
  fi
  
  if [ "${CI:-false}" = "true" ] || [ "${AUTO_APPROVE:-false}" = "true" ]; then
    destroy_args+=" -auto-approve"
  fi
  
  cd "$INFRA_DIR"
  
  if [ "$DRY_RUN" = true ]; then
    log "INFO" "[DRY RUN] Would execute: terraform destroy $destroy_args"
  else
    if terraform destroy $destroy_args; then
      log "SUCCESS" "Terraform destroy completed successfully"
    else
      log "ERROR" "Terraform destroy failed"
      return 1
    fi
  fi
  
  return 0
}

# =============================================================================
# MAIN WORKFLOW FUNCTIONS
# =============================================================================

#
# Parses command line arguments and sets global variables
# Arguments: All command line arguments ($@)
# Returns: 0 on success, 1 on invalid arguments
#
parse_arguments() {
  if [ $# -eq 0 ]; then
    log "ERROR" "No command specified"
    usage
  fi
  
  TERRAFORM_COMMAND="$1"
  shift
  
  while [[ $# -gt 0 ]]; do
    case $1 in
      --tfvars=*)
        TFVARS_FILE="${1#*=}"
        shift
        ;;
      --build)
        BUILD_CONTAINERS=true
        shift
        ;;
      --no-cache)
        NO_CACHE=true
        shift
        ;;
      --verbose)
        VERBOSE=true
        shift
        ;;
      --dry-run)
        DRY_RUN=true
        shift
        ;;
      --static-images)
        USE_STATIC_IMAGES=true
        shift
        ;;
      --help)
        usage
        ;;
      *)
        log "ERROR" "Unknown option: $1"
        usage
        ;;
    esac
  done
  
  # Set default tfvars file if not specified
  if [ -z "$TFVARS_FILE" ]; then
    TFVARS_FILE="$INFRA_DIR/$DEFAULT_TFVARS"
  elif [[ "$TFVARS_FILE" != /* ]]; then
    # Relative path, prepend infra directory
    TFVARS_FILE="$INFRA_DIR/$TFVARS_FILE"
  fi
  
  # Validate command
  case "$TERRAFORM_COMMAND" in
    plan|apply|destroy|validate)
      ;;
    build)
      BUILD_CONTAINERS=true
      ;;
    *)
      log "ERROR" "Invalid command: $TERRAFORM_COMMAND"
      log "ERROR" "Valid commands: plan, apply, destroy, build, validate"
      return 1
      ;;
  esac
  
  return 0
}

#
# Main execution function that orchestrates the entire deployment process
# Arguments: None
# Returns: 0 on success, 1 on failure
#
main() {
  log "INFO" "Starting Azure Container Infrastructure Deployment"
  log "INFO" "Script version: 1.0.0"
  log "INFO" "Execution timestamp: $TIMESTAMP"
  
  # Check prerequisites
  if ! check_prerequisites; then
    return 1
  fi
  
  # Build containers if requested
  if [ "$BUILD_CONTAINERS" = true ]; then
    if ! build_all_containers; then
      log "ERROR" "Container build failed, aborting deployment"
      return 1
    fi
    
    # Export built container images as Terraform variables
    export_container_images
  fi
  
  # Execute Terraform operations (except for build-only command)
  if [ "$TERRAFORM_COMMAND" != "build" ]; then
    # If containers weren't built but we're doing Terraform operations,
    # still export image variables with current git commit for consistency
    if [ "$BUILD_CONTAINERS" = false ]; then
      export_container_images
    fi
    
    # Validate tfvars file
    if ! validate_tfvars_file "$TFVARS_FILE"; then
      return 1
    fi
    
    # Initialize Terraform
    if ! terraform_init; then
      return 1
    fi
    
    # Validate configuration
    if ! terraform_validate; then
      return 1
    fi
    
    # Execute the requested Terraform command
    case "$TERRAFORM_COMMAND" in
      plan)
        if ! terraform_plan; then
          return 1
        fi
        ;;
      apply)
        if ! terraform_apply; then
          return 1
        fi
        ;;
      destroy)
        if ! terraform_destroy; then
          return 1
        fi
        ;;
      validate)
        log "SUCCESS" "Terraform validation completed"
        ;;
    esac
  fi
  
  log "SUCCESS" "Deployment script completed successfully"
  log "INFO" "Log file: $LOG_FILE"
  
  return 0
}

# =============================================================================
# SCRIPT ENTRY POINT
# =============================================================================

# Trap for cleanup on script exit
cleanup() {
  local exit_code=$?
  if [ $exit_code -ne 0 ]; then
    log "ERROR" "Script exited with error code: $exit_code"
    log "INFO" "Check the log file for details: $LOG_FILE"
  fi
}
trap cleanup EXIT

# Parse arguments and execute main function
if parse_arguments "$@"; then
  main
else
  exit 1
fi
