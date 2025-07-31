output "frontend_url" {
  description = "The URL of the frontend application"
  value       = "https://${azurerm_cdn_frontdoor_endpoint.frontend_fd_endpoint.host_name}"
}

output "possible_outbound_ip_addresses" {
  description = "Possible outbound IP addresses for the frontend application."
  value       = azurerm_linux_web_app.frontend.possible_outbound_ip_addresses
}