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

variable "app_service_sku_name_proxy" {
  description = "SKU name for the frontend proxy App Service Plan"
  type        = string
  default     = "B1" # Basic tier 
}

variable "azure_openai_deployment_name" {
  description = "Azure OpenAI model deployment name"
  type        = string
  default     = "gpt-4o-mini"
}

variable "azure_openai_nano_deployment_name" {
  description = "Azure OpenAI GPT-4.1 Nano model deployment name"
  type        = string
  default     = "gpt-4.1-nano"
}

variable "azure_openai_embedding_deployment" {
  description = "Azure OpenAI embedding model deployment name"
  type        = string
  default     = "text-embedding-3-large"
}

variable "azure_search_index_name" {
  description = "Azure AI Search index name for document storage"
  type        = string
  default     = "documents-index"
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


variable "frontend_image" {
  description = "The image for the Frontend container"
  type        = string
}

variable "frontdoor_sku_name" {
  description = "SKU name for the Front Door"
  type        = string
  default     = "Standard_AzureFrontDoor"
}
variable "image_tag" {
  description = "Tag for the container images"
  type        = string
  default     = "latest"
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

variable "repo_name" {
  description = "Name of the repository, used for resource naming"
  type        = string
  nullable    = false
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


# Azure OpenAI Module Variables
variable "openai_sku_name" {
  description = "SKU name for the Azure OpenAI service"
  type        = string
  default     = "S0"
}

variable "openai_gpt_deployment_capacity" {
  description = "Capacity for the GPT model deployment"
  type        = number
  default     = 10000
}

variable "openai_gpt_nano_deployment_capacity" {
  description = "Capacity for the GPT-4.1 Nano model deployment"
  type        = number
  default     = 10000
}

variable "openai_embedding_deployment_capacity" {
  description = "Capacity for the embedding model deployment"
  type        = number
  default     = 10000
}

# Azure Document Intelligence Module Variables
variable "document_intelligence_sku_name" {
  description = "SKU name for the Azure Document Intelligence service"
  type        = string
  default     = "S0"
}

# Azure AI Search Module Variables
variable "search_sku" {
  description = "SKU for the Azure AI Search service"
  type        = string
  default     = "standard"
}

variable "search_replica_count" {
  description = "Number of replicas for the search service"
  type        = number
  default     = 1
}

variable "search_partition_count" {
  description = "Number of partitions for the search service"
  type        = number
  default     = 1
}

variable "search_semantic_search_sku" {
  description = "SKU for semantic search capabilities"
  type        = string
  default     = "standard"
}

variable "search_hosting_mode" {
  description = "Hosting mode for the search service"
  type        = string
  default     = "default"
}

variable "search_local_authentication_enabled" {
  description = "Whether local authentication is enabled for search service"
  type        = bool
  default     = false
}

variable "search_enable_managed_identity_permissions" {
  description = "Whether to assign permissions to the search service managed identity"
  type        = bool
  default     = true
}

variable "keycloak_url" {
  description = "The URL for the Keycloak authentication server."
  type        = string
  nullable    = false
  default     = "https://dev.loginproxy.gov.bc.ca/auth"
}
variable "proxy_image" {
  description = "The image for the Frontend proxy container"
  type        = string
}
