# Azure Document Intelligence Service
resource "azurerm_cognitive_account" "document_intelligence" {
  name                = "${var.app_name}-doc-intelligence"
  resource_group_name = var.resource_group_name
  location            = var.location
  kind                = "FormRecognizer"
  sku_name            = var.document_intelligence_sku_name

  # Security settings - private access only for Landing Zone compliance
  public_network_access_enabled = false
  custom_subdomain_name         = "${var.app_name}-doc-intel-${var.app_env}"

  identity {
    type = "SystemAssigned"
  }

  tags = var.common_tags

  lifecycle {
    ignore_changes = [tags]
  }
}

# Private endpoint for Azure Document Intelligence - always created for Landing Zone compliance
resource "azurerm_private_endpoint" "document_intelligence" {
  name                = "${var.app_name}-doc-intelligence-pe"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.app_name}-doc-intelligence-psc"
    private_connection_resource_id = azurerm_cognitive_account.document_intelligence.id
    subresource_names              = ["account"]
    is_manual_connection           = false
  }

  # DO NOT configure private_dns_zone_group here
  # The Azure Landing Zone will automatically manage this via Azure Policy
  # See: https://docs.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/private-link-and-dns-integration-at-scale

  tags = var.common_tags

  lifecycle {
    ignore_changes = [
      # Ignore changes to private_dns_zone_group, as Azure Policy manages this automatically
      private_dns_zone_group,
      tags
    ]
  }

  depends_on = [azurerm_cognitive_account.document_intelligence]
}

# Diagnostic settings for monitoring
resource "azurerm_monitor_diagnostic_setting" "document_intelligence" {
  name                       = "${var.app_name}-doc-intel-diagnostics-${var.app_env}"
  target_resource_id         = azurerm_cognitive_account.document_intelligence.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "Audit"
  }

  enabled_log {
    category = "RequestResponse"
  }

  enabled_log {
    category = "Trace"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}
