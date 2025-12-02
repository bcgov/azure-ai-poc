output "app_url" {
  description = "The URL of the application"
  value       = module.frontend.frontend_url
}

# Azure OpenAI outputs
output "azure_openai_endpoint" {
  description = "The Azure OpenAI service endpoint"
  value       = module.azure_openai.openai_endpoint
  sensitive   = false
}

output "azure_openai_gpt_deployment_name" {
  description = "The name of the GPT model deployment"
  value       = module.azure_openai.gpt_deployment_name
}

output "azure_openai_embedding_deployment_name" {
  description = "The name of the embedding model deployment"
  value       = module.azure_openai.embedding_deployment_name
}

# Azure AI Search outputs (module disabled)
/* output "azure_search_service_name" {
  description = "The name of the Azure AI Search service"
  value       = module.azure_ai_search.search_service_name
}

output "azure_search_service_url" {
  description = "The URL of the Azure AI Search service"
  value       = module.azure_ai_search.search_service_url
} */

# Azure Document Intelligence outputs
output "azure_document_intelligence_endpoint" {
  description = "The Azure Document Intelligence service endpoint"
  value       = module.document_intelligence.endpoint
  sensitive   = false
}

output "azure_document_intelligence_host" {
  description = "The host portion of the Azure Document Intelligence endpoint"
  value       = module.document_intelligence.host
}
