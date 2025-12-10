output "openai_endpoint" {
  description = "The endpoint URL for the Azure OpenAI service"
  value       = trimsuffix(azurerm_cognitive_account.openai.endpoint, "/")
  sensitive   = false
}

output "openai_primary_key" {
  description = "The primary access key for the Azure OpenAI service"
  value       = azurerm_cognitive_account.openai.primary_access_key
  sensitive   = true
}

output "openai_secondary_key" {
  description = "The secondary access key for the Azure OpenAI service"
  value       = azurerm_cognitive_account.openai.secondary_access_key
  sensitive   = true
}

output "openai_id" {
  description = "The resource ID of the Azure OpenAI service"
  value       = azurerm_cognitive_account.openai.id
}

output "openai_name" {
  description = "The name of the Azure OpenAI service"
  value       = azurerm_cognitive_account.openai.name
}

output "gpt_deployment_name" {
  description = "The name of the GPT model deployment"
  value       = azurerm_cognitive_deployment.gpt4o_mini.name
}

output "embedding_deployment_name" {
  description = "The name of the embedding model deployment"
  value       = azurerm_cognitive_deployment.text_embedding_large.name
}

output "openai_custom_subdomain" {
  description = "The custom subdomain name for the Azure OpenAI service"
  value       = azurerm_cognitive_account.openai.custom_subdomain_name
}

output "openai_managed_identity_principal_id" {
  description = "The principal ID of the managed identity for Azure OpenAI"
  value       = azurerm_cognitive_account.openai.identity[0].principal_id
}

output "openai_managed_identity_tenant_id" {
  description = "The tenant ID of the managed identity for Azure OpenAI"
  value       = azurerm_cognitive_account.openai.identity[0].tenant_id
}

output "private_endpoint_id" {
  description = "The resource ID of the private endpoint"
  value       = azurerm_private_endpoint.openai.id
}
output "openai_host" {
  description = "The host for the Azure OpenAI service"
  value       = trimsuffix(replace(azurerm_cognitive_account.openai.endpoint, "https://", ""), "/")
}

# Speech Services outputs
output "speech_endpoint" {
  description = "The endpoint URL for the Azure Speech service"
  value       = azurerm_cognitive_account.speech.endpoint
  sensitive   = false
}

output "speech_id" {
  description = "The resource ID of the Azure Speech service"
  value       = azurerm_cognitive_account.speech.id
}
