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

variable "frontend_frontdoor_id" {
  description = "The ID of the Front Door profile for the frontend."
  type        = string
  nullable    = false
}

variable "frontend_frontdoor_resource_guid" {
  description = "The resource GUID of the Front Door profile for the frontend."
  type        = string
  nullable    = false
}

variable "frontend_image" {
  description = "The Docker image for the frontend application."
  type        = string
  nullable    = false
}

variable "frontend_subnet_id" {
  description = "The subnet ID for the frontend App Service."
  type        = string
  nullable    = false
}

variable "frontdoor_frontend_firewall_policy_id" {
  description = "The resource ID of the Front Door firewall policy for the frontend."
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
  description = "The client ID of the user-assigned managed identity for the frontend."
  type        = string
  nullable    = false
}

variable "user_assigned_identity_id" {
  description = "The resource ID of the user-assigned managed identity for the frontend."
  type        = string
  nullable    = false
}

variable "app_service_sku_name_frontend" {
  description = "The SKU name for the frontend App Service plan."
  type        = string
  nullable    = false
}