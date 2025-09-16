variable "app_name" {
  description = "Name of the application"
  type        = string
}

variable "app_env" {
  description = "Environment (dev, test, prod)"
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
  default     = {}
}

variable "openai_sku_name" {
  description = "SKU name for the Azure OpenAI service"
  type        = string
  default     = "S0"
}

variable "private_endpoint_subnet_id" {
  description = "Subnet ID for private endpoint"
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID for diagnostic settings"
  type        = string
}

variable "gpt_deployment_name" {
  description = "Name for the GPT model deployment"
  type        = string
  default     = "gpt-4o-mini"
}

variable "gpt_deployment_capacity" {
  description = "Capacity for the GPT model deployment"
  type        = number
  default     = 10
}

variable "embedding_deployment_name" {
  description = "Name for the embedding model deployment"
  type        = string
  default     = "text-embedding-3-large"
}

variable "embedding_deployment_capacity" {
  description = "Capacity for the embedding model deployment"
  type        = number
  default     = 10
}
