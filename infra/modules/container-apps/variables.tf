variable "app_name" {
  type        = string
  description = "Application name prefix"
}

variable "app_env" {
  type        = string
  description = "Application environment (dev/test/prod)"
}

variable "resource_group_name" {
  type        = string
  description = "Resource group for Container Apps"
}

variable "location" {
  type        = string
  description = "Azure region"
}

variable "common_tags" {
  type        = map(string)
  description = "Tags applied to resources"
}

variable "container_apps_subnet_id" {
  type        = string
  description = "Subnet ID for Container Apps Environment"
}

variable "log_analytics_workspace_id" {
  type        = string
  description = "Log Analytics workspace id for diagnostics"
}

variable "backend_image" {
  type        = string
  description = "Container image for backend service"
}

variable "ingress_enabled" {
  type        = bool
  default     = true
  description = "Enable external ingress for the Container App"
}

variable "target_port" {
  type        = number
  default     = 8000
  description = "Target port exposed by the container"
}

variable "min_replicas" {
  type        = number
  default     = 1
}

variable "max_replicas" {
  type        = number
  default     = 5
}

variable "cpu" {
  type        = number
  default     = 0.25
}

variable "memory" {
  type        = string
  default     = "0.5Gi"
}

variable "secrets" {
  type        = map(string)
  default     = {}
  description = "Secrets for the Container App (injected as environment variables)"
}
