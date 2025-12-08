# Browser Desktop Module Variables

variable "app_name" {
  description = "Application name used in resource naming"
  type        = string
}

variable "app_env" {
  description = "Application environment (dev, test, prod)"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
}

variable "app_service_sku_name" {
  description = "SKU name for the browser desktop App Service Plan (P3v3 recommended for GUI workloads)"
  type        = string
  default     = "P3v3"
}

variable "subnet_id" {
  description = "Subnet ID for VNet integration"
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics Workspace ID for diagnostics"
  type        = string
}

variable "repo_name" {
  description = "Repository name for container image reference"
  type        = string
}

variable "docker_image" {
  description = "Docker image for the browser desktop (without tag)"
  type        = string
  default     = "accetto/ubuntu-vnc-xfce-chromium-g3"
}

variable "image_tag" {
  description = "Tag for the container image"
  type        = string
  default     = "latest"
}

variable "vnc_password" {
  description = "Password for VNC access (VNC_PW env var)"
  type        = string
  sensitive   = true
}

variable "vnc_resolution" {
  description = "Screen resolution for the VNC desktop"
  type        = string
  default     = "1920x1080"
}

variable "container_registry_url" {
  description = "Container registry URL (Docker Hub for accetto images)"
  type        = string
  default     = "https://index.docker.io"
}
