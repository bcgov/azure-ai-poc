output "proxy_chisel_auth" {
  description = "Chisel auth string for the proxy tunnel (CHISEL_AUTH)."
  value       = "tunnel:${random_password.proxy_chisel_password.result}"
  sensitive   = true
}
output "frontend_url" {
  description = "The URL of the frontend application"
  value       = "https://${azurerm_linux_web_app.frontend.default_hostname}"
}

output "possible_outbound_ip_addresses" {
  description = "Possible outbound IP addresses for the frontend application."
  value       = azurerm_linux_web_app.frontend.possible_outbound_ip_addresses
}

output "proxy_url" {
  description = "The URL of the proxy/tunnel App Service"
  value       = "https://${azurerm_linux_web_app.frontend_proxy.default_hostname}"
}
