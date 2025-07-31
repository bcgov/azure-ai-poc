variable "api_image" {
  description = "The Docker image for the backend API."
  type        = string
  nullable    = false
}

variable "app_env" {
  description = "The deployment environment (e.g., dev, test, prod)."
  type        = string
  nullable    = false
}

variable "app_name" {
  description = "The base name of the application. Used for naming Azure resources."
  type        = string
  nullable    = false
}

variable "app_service_sku_name_backend" {
  description = "The SKU name for the backend App Service plan."
  type        = string
  nullable    = false
}

variable "app_service_subnet_id" {
  description = "The subnet ID for the App Service."
  type        = string
  nullable    = false
}

variable "appinsights_connection_string" {
  description = "The Application Insights connection string for monitoring."
  type        = string
  nullable    = false
}

variable "appinsights_instrumentation_key" {
  description = "The Application Insights instrumentation key."
  type        = string
  nullable    = false
}

variable "backend_autoscale_enabled" {
  description = "Whether autoscaling is enabled for the backend App Service plan."
  type        = bool
  default     = true
}

variable "backend_depends_on" {
  description = "A list of resources this backend depends on."
  type        = list(any)
  default     = []
}

variable "backend_subnet_id" {
  description = "The subnet ID for the backend App Service."
  type        = string
  nullable    = false
}

variable "common_tags" {
  description = "A map of tags to apply to resources."
  type        = map(string)
  default     = {}
}

variable "container_registry_url" {
  description = "The URL of the container registry to pull images from."
  type        = string
  nullable    = false
  default     = "https://ghcr.io"
}

variable "database_name" {
  description = "The name of the PostgreSQL database."
  type        = string
  nullable    = false
}

variable "db_master_password" {
  description = "The password for the PostgreSQL admin user."
  type        = string
  sensitive   = true
  nullable    = false
}

variable "enable_psql_sidecar" {
  description = "Whether to enable the CloudBeaver PostgreSQL sidecar."
  type        = bool
  default     = false
}

variable "frontend_frontdoor_resource_guid" {
  description = "The resource GUID for the Front Door service associated with the frontend App Service."
  type        = string
  nullable    = false
}

variable "frontend_possible_outbound_ip_addresses" {
  description = "Possible outbound IP addresses for the frontend App Service."
  type        = string
  nullable    = false
}

variable "location" {
  description = "The Azure region where resources will be created."
  type        = string
  nullable    = false
}

variable "log_analytics_workspace_id" {
  description = "The resource ID of the Log Analytics workspace for diagnostics."
  type        = string
  nullable    = false
}

variable "node_env" {
  description = "The Node.js environment (e.g., production, development)."
  type        = string
  default     = "production"
}

variable "postgres_host" {
  description = "The FQDN of the PostgreSQL server."
  type        = string
  nullable    = false
}

variable "postgresql_admin_username" {
  description = "The admin username for the PostgreSQL server."
  type        = string
  nullable    = false
}

variable "private_endpoint_subnet_id" {
  description = "The subnet ID for private endpoints."
  type        = string
  nullable    = false
}

variable "repo_name" {
  description = "The repository name, used for resource naming."
  type        = string
  nullable    = false
}

variable "resource_group_name" {
  description = "The name of the resource group in which to create resources."
  type        = string
  nullable    = false
}

variable "user_assigned_identity_client_id" {
  description = "The client ID of the user-assigned managed identity for the backend."
  type        = string
  nullable    = false
}

variable "user_assigned_identity_id" {
  description = "The resource ID of the user-assigned managed identity for the backend."
  type        = string
  nullable    = false
}
