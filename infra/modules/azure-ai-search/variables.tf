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

variable "search_sku" {
  description = "SKU for the Azure AI Search service"
  type        = string
  default     = "standard"
  validation {
    condition = contains([
      "free", "basic", "standard", "standard2", "standard3",
      "storage_optimized_l1", "storage_optimized_l2"
    ], var.search_sku)
    error_message = "SKU must be one of: free, basic, standard, standard2, standard3, storage_optimized_l1, storage_optimized_l2."
  }
}

variable "replica_count" {
  description = "Number of replicas for the search service"
  type        = number
  default     = 1
  validation {
    condition     = var.replica_count >= 1 && var.replica_count <= 12
    error_message = "Replica count must be between 1 and 12."
  }
}

variable "partition_count" {
  description = "Number of partitions for the search service"
  type        = number
  default     = 1
  validation {
    condition     = contains([1, 2, 3, 4, 6, 12], var.partition_count)
    error_message = "Partition count must be one of: 1, 2, 3, 4, 6, 12."
  }
}

variable "semantic_search_sku" {
  description = "SKU for semantic search capabilities"
  type        = string
  default     = "standard"
  validation {
    condition     = contains(["disabled", "free", "standard"], var.semantic_search_sku)
    error_message = "Semantic search SKU must be one of: disabled, free, standard."
  }
}

variable "hosting_mode" {
  description = "Hosting mode for the search service"
  type        = string
  default     = "default"
  validation {
    condition     = contains(["default", "highDensity"], var.hosting_mode)
    error_message = "Hosting mode must be either 'default' or 'highDensity'."
  }
}



variable "customer_managed_key_enforcement_enabled" {
  description = "Whether customer managed key enforcement is enabled"
  type        = bool
  default     = null
}

variable "private_endpoint_subnet_id" {
  description = "Subnet ID for private endpoint"
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID for diagnostic settings"
  type        = string
}

variable "enable_managed_identity_permissions" {
  description = "Whether to assign permissions to the managed identity"
  type        = bool
  default     = false
}

variable "resource_group_id" {
  description = "Resource group ID for role assignments"
  type        = string
  default     = null
}
