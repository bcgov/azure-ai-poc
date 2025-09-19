output "document_intelligence_id" {
  description = "The ID of the Azure Document Intelligence service"
  value       = azurerm_cognitive_account.document_intelligence.id
}

output "endpoint" {
  description = "The endpoint URL of the Azure Document Intelligence service"
  value       = trimsuffix(azurerm_cognitive_account.document_intelligence.endpoint, "/")
}

output "host" {
  description = "The host portion of the Azure Document Intelligence endpoint"
  value       = trimsuffix(replace(azurerm_cognitive_account.document_intelligence.endpoint, "https://", ""), "/")
}


