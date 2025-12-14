output "container_app_environment_id" {
  value       = azurerm_container_app_environment.this.id
  description = "ID of the Container Apps Environment"
}

output "backend_container_app_url" {
  value       = azurerm_container_app.backend.configuration[0].ingress[0].fqdn
  description = "FQDN/URL for the backend container app"
}

output "backend_container_app_id" {
  value       = azurerm_container_app.backend.id
  description = "ID of the backend Container App"
}
