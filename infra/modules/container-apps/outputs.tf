
output "backend_container_app_url" {
  value       = "https://${azurerm_container_app.backend.ingress[0].fqdn}"
  description = "FQDN/URL for the backend container app"
}

output "backend_container_app_id" {
  value       = azurerm_container_app.backend.id
  description = "ID of the backend Container App"
}

output "backend_managed_identity_principal_id" {
  value       = azurerm_container_app.backend.identity[0].principal_id
  description = "Principal ID for the backend Container App's system-assigned identity"
}
