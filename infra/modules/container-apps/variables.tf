# Container Apps Module Variables - Backend Only

variable "app_env" {
  description = "Application environment (dev, test, prod)"
  type        = string
  nullable    = false
}

variable "app_name" {
  description = "Name of the application"
  type        = string
  nullable    = false
}


variable "appinsights_connection_string" {
  description = "Application Insights connection string"
  type        = string
  sensitive   = true
  nullable    = false
}

variable "appinsights_instrumentation_key" {
  description = "Application Insights instrumentation key"
  type        = string
  sensitive   = true
  nullable    = false
}

variable "azure_document_intelligence_endpoint" {
  description = "The endpoint for the Azure Document Intelligence service."
  type        = string
  nullable    = false
}

variable "azure_openai_api_key" {
  description = "Azure OpenAI API key"
  type        = string
  sensitive   = true
  nullable    = false
}

variable "azure_openai_deployment_name" {
  description = "Azure OpenAI model deployment name"
  type        = string
  default     = "gpt-4o"
}

variable "azure_openai_embedding_deployment" {
  description = "Azure OpenAI embedding model deployment name"
  type        = string
  default     = "text-embedding-3-large"
}

variable "azure_openai_embedding_endpoint" {
  description = "The endpoint for the Azure OpenAI embedding service."
  type        = string
  nullable    = false
}

variable "azure_openai_llm_endpoint" {
  description = "The endpoint for the Azure OpenAI LLM service."
  type        = string
  nullable    = false
}

variable "azure_search_endpoint" {
  description = "Azure AI Search service endpoint URL"
  type        = string
  nullable    = false
}

variable "azure_search_index_name" {
  description = "Azure AI Search index name for document storage"
  type        = string
  default     = "documents-index"
}

variable "azure_speech_endpoint" {
  description = "The endpoint for the Azure Speech service."
  type        = string
  nullable    = false
}

variable "azure_speech_key" {
  description = "The API key for the Azure Speech service."
  type        = string
  nullable    = false
}

variable "backend_image" {
  description = "Container image for the backend API"
  type        = string
  nullable    = false
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  nullable    = false
}

variable "container_apps_subnet_id" {
  description = "Subnet ID for Container Apps Environment"
  type        = string
  nullable    = false
}

variable "container_cpu" {
  description = "CPU allocation for backend container app (in cores)"
  type        = number
  default     = 0.5
  nullable    = false
}

variable "container_memory" {
  description = "Memory allocation for backend container app"
  type        = string
  default     = "1Gi"
  nullable    = false
}

variable "cosmosdb_container_name" {
  description = "The name of the Cosmos DB container."
  type        = string
  nullable    = false
}

variable "cosmosdb_db_name" {
  description = "The name of the Cosmos DB database."
  type        = string
  nullable    = false
}

variable "cosmosdb_endpoint" {
  description = "The endpoint URL for the Cosmos DB instance."
  type        = string
  nullable    = false
}


variable "enable_system_assigned_identity" {
  description = "Enable system assigned managed identity"
  type        = bool
  default     = true
  nullable    = false
}

variable "image_tag" {
  description = "Tag for the container images"
  type        = string
  nullable    = false
}

variable "keycloak_url" {
  description = "The URL for the Keycloak authentication server."
  type        = string
  nullable    = false
}

variable "location" {
  description = "Azure region where resources will be deployed"
  type        = string
  nullable    = false
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics Workspace ID for Container Apps Environment"
  type        = string
  nullable    = false
}

variable "max_replicas" {
  description = "Maximum number of replicas for backend"
  type        = number
  default     = 10 # Higher max for Consumption workload
  nullable    = false
}

variable "min_replicas" {
  description = "Minimum number of replicas for backend"
  type        = number
  default     = 1 # Allow scale to zero for Consumption workload
  nullable    = false
}

variable "private_endpoint_subnet_id" {
  description = "Subnet ID for the private endpoint"
  type        = string
  nullable    = false
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  nullable    = false
}
