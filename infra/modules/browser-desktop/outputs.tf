# Browser Desktop Module Outputs

output "browser_desktop_url" {
  description = "URL of the browser desktop"
  value       = "https://${azurerm_linux_web_app.browser_desktop.default_hostname}"
}

output "browser_desktop_hostname" {
  description = "Default hostname of the browser desktop App Service"
  value       = azurerm_linux_web_app.browser_desktop.default_hostname
}

output "browser_desktop_id" {
  description = "ID of the browser desktop App Service"
  value       = azurerm_linux_web_app.browser_desktop.id
}

output "browser_desktop_managed_identity_principal_id" {
  description = "Principal ID of the browser desktop managed identity"
  value       = azurerm_linux_web_app.browser_desktop.identity[0].principal_id
}

output "browser_desktop_managed_identity_tenant_id" {
  description = "Tenant ID of the browser desktop managed identity"
  value       = azurerm_linux_web_app.browser_desktop.identity[0].tenant_id
}

output "app_service_plan_id" {
  description = "ID of the browser desktop App Service Plan"
  value       = azurerm_service_plan.browser_desktop.id
}
