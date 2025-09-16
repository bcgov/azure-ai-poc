output "search_service_name" {
  description = "The name of the Azure AI Search service"
  value       = azurerm_search_service.main.name
}

output "search_service_id" {
  description = "The resource ID of the Azure AI Search service"
  value       = azurerm_search_service.main.id
}

output "search_service_url" {
  description = "The URL of the Azure AI Search service"
  value       = "https://${azurerm_search_service.main.name}.search.windows.net"
}

output "search_service_primary_key" {
  description = "The primary admin key for the Azure AI Search service"
  value       = azurerm_search_service.main.primary_key
  sensitive   = true
}

output "search_service_secondary_key" {
  description = "The secondary admin key for the Azure AI Search service"
  value       = azurerm_search_service.main.secondary_key
  sensitive   = true
}

output "search_service_query_keys" {
  description = "The query keys for the Azure AI Search service"
  value       = azurerm_search_service.main.query_keys
  sensitive   = true
}

output "search_service_managed_identity_principal_id" {
  description = "The principal ID of the managed identity for the search service"
  value       = azurerm_search_service.main.identity[0].principal_id
}

output "search_service_managed_identity_tenant_id" {
  description = "The tenant ID of the managed identity for the search service"
  value       = azurerm_search_service.main.identity[0].tenant_id
}

output "private_endpoint_id" {
  description = "The resource ID of the private endpoint"
  value       = azurerm_private_endpoint.search.id
}
