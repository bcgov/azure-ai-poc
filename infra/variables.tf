# -------------
# Common Variables for Azure Infrastructure
# -------------

variable "api_image" {
  description = "The image for the API container"
  type        = string
}

variable "app_env" {
  description = "Application environment (dev, test, prod)"
  type        = string
}

variable "app_name" {
  description = "Name of the application"
  type        = string
}

variable "app_service_sku_name_backend" {
  description = "SKU name for the backend App Service Plan"
  type        = string
  default     = "B1" # Basic tier 
}

variable "app_service_sku_name_frontend" {
  description = "SKU name for the frontend App Service Plan"
  type        = string
  default     = "B1" # Basic tier 
}

variable "client_id" {
  description = "Azure client ID for the service principal"
  type        = string
  sensitive   = true
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
}

variable "database_name" {
  description = "Name of the database to create"
  type        = string
  default     = "app"
}

variable "db_master_password" {
  description = "Master password for the PostgreSQL server"
  type        = string
  sensitive   = true
  validation {
    condition     = length(var.db_master_password) >= 12
    error_message = "The db_master_password must be at least 12 characters long."
  }
}

variable "enable_psql_sidecar" {
  description = "Whether to enable the CloudBeaver database management container"
  type        = bool
  default     = true
}

variable "flyway_image" {
  description = "The image for the Flyway container"
  type        = string
}

variable "frontend_image" {
  description = "The image for the Frontend container"
  type        = string
}

variable "frontdoor_sku_name" {
  description = "SKU name for the Front Door"
  type        = string
  default     = "Standard_AzureFrontDoor"
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "Canada Central"
}

variable "log_analytics_retention_days" {
  description = "Number of days to retain data in Log Analytics Workspace"
  type        = number
  default     = 30
}

variable "log_analytics_sku" {
  description = "SKU for Log Analytics Workspace"
  type        = string
  default     = "PerGB2018"
}

variable "postgres_auto_grow_enabled" {
  description = "Enable auto-grow for PostgreSQL Flexible Server storage"
  type        = bool
  default     = true
}

variable "postgres_backup_retention_period" {
  description = "Backup retention period in days for PostgreSQL Flexible Server"
  type        = number
  default     = 7
}

variable "postgres_geo_redundant_backup_enabled" {
  description = "Enable geo-redundant backup for PostgreSQL Flexible Server"
  type        = bool
  default     = false
}

variable "postgres_ha_enabled" {
  description = "Enable high availability for PostgreSQL Flexible Server"
  type        = bool
  default     = false
}

variable "postgres_is_postgis_enabled" {
  description = "Enable PostGIS extension for PostgreSQL Flexible Server"
  type        = bool
  default     = false
}

variable "postgres_sku_name" {
  description = "SKU name for PostgreSQL Flexible Server"
  type        = string
  default     = "B_Standard_B1ms"
}

variable "postgres_standby_availability_zone" {
  description = "Availability zone for standby replica of PostgreSQL Flexible Server"
  type        = string
  default     = "1"
}

variable "postgres_storage_mb" {
  description = "Storage in MB for PostgreSQL Flexible Server"
  type        = number
  default     = 32768
}

variable "postgres_version" {
  description = "Version of PostgreSQL Flexible Server"
  type        = string
  default     = "16"
}

variable "postgres_zone" {
  description = "Availability zone for PostgreSQL server"
  type        = string
  default     = "1"
}

variable "postgresql_admin_username" {
  description = "Administrator username for PostgreSQL server"
  type        = string
  default     = "pgadmin"
}

variable "repo_name" {
  description = "Name of the repository, used for resource naming"
  type        = string
  default     = "quickstart-azure-containers"
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
  sensitive   = true
}

variable "tenant_id" {
  description = "Azure tenant ID"
  type        = string
  sensitive   = true
}

variable "use_oidc" {
  description = "Use OIDC for authentication"
  type        = bool
  default     = true
}

variable "vnet_address_space" {
  type        = string
  description = "Address space for the virtual network, it is created by platform team"
}

variable "vnet_name" {
  description = "Name of the existing virtual network"
  type        = string
}

variable "vnet_resource_group_name" {
  description = "Resource group name where the virtual network exists"
  type        = string
}
