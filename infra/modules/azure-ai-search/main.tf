# Azure AI Search Service
resource "azurerm_search_service" "main" {
  name                = "${var.app_name}-search-${var.app_env}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.search_sku
  replica_count       = var.replica_count
  partition_count     = var.partition_count

  # Security settings - private access only for Landing Zone compliance
  public_network_access_enabled = false

  # Enable semantic search capabilities
  semantic_search_sku = var.semantic_search_sku

  # Hosting mode for higher storage and query limits
  hosting_mode = var.hosting_mode

  local_authentication_enabled = true
  authentication_failure_mode  = "http403"

  identity {
    type = "SystemAssigned"
  }

  tags = var.common_tags

  lifecycle {
    ignore_changes = [tags]
  }
}

# Private endpoint for Azure AI Search - always created for Landing Zone compliance
resource "azurerm_private_endpoint" "search" {
  name                = "${var.app_name}-search-pe-${var.app_env}"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.app_name}-search-psc-${var.app_env}"
    private_connection_resource_id = azurerm_search_service.main.id
    subresource_names              = ["searchService"]
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

  depends_on = [azurerm_search_service.main]
}

# Diagnostic settings for monitoring
resource "azurerm_monitor_diagnostic_setting" "search" {
  name                       = "${var.app_name}-search-monitor-${var.app_env}"
  target_resource_id         = azurerm_search_service.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "OperationLogs"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}

# Role assignment for Azure AI Search to access other resources (if needed)
# This allows the search service to access storage accounts, key vaults, etc.
resource "azurerm_role_assignment" "search_contributor" {
  count                = var.enable_managed_identity_permissions ? 1 : 0
  scope                = var.resource_group_id != null ? var.resource_group_id : "/subscriptions/${data.azurerm_subscription.current.subscription_id}/resourceGroups/${var.resource_group_name}"
  role_definition_name = "Search Service Contributor"
  principal_id         = azurerm_search_service.main.identity[0].principal_id

  depends_on = [azurerm_search_service.main]
}

data "azurerm_subscription" "current" {
}
