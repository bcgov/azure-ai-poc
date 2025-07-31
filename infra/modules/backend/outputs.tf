output "cloudbeaver_app_service_url" {
  description = "The URL of the CloudBeaver App Service"
  value       = var.enable_psql_sidecar ? "https://${azurerm_linux_web_app.psql_sidecar[0].default_hostname}" : null
}
