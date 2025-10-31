# Azure OpenAI Service
resource "azurerm_cognitive_account" "openai" {
  name                = "${var.app_name}-openai-${var.app_env}"
  resource_group_name = var.resource_group_name
  location            = "Canada East" # Currently Azure OpenAI is only available in Canada East
  kind                = "OpenAI"
  sku_name            = var.openai_sku_name

  public_network_access_enabled = false
  custom_subdomain_name         = "${var.app_name}-openai-${var.app_env}"

  identity {
    type = "SystemAssigned"
  }

  tags = var.common_tags

  lifecycle {
    ignore_changes = [tags]
  }
}

# GPT-4o-mini model deployment
resource "azurerm_cognitive_deployment" "gpt4o_mini" {
  name                 = var.gpt_deployment_name
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-4o-mini"
    version = "2024-07-18"
  }

  sku {
    name     = "GlobalStandard"
    capacity = var.gpt_deployment_capacity
  }

  depends_on = [azurerm_cognitive_account.openai]
}

# Text embedding model deployment (large)
resource "azurerm_cognitive_deployment" "text_embedding_large" {
  name                 = var.embedding_deployment_name
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "text-embedding-3-large"
    version = "1"
  }

  sku {
    name     = "GlobalStandard"
    capacity = var.embedding_deployment_capacity
  }

  depends_on = [azurerm_cognitive_account.openai]
}

# Private endpoint for Azure OpenAI - always created for Landing Zone compliance
resource "azurerm_private_endpoint" "openai" {
  name                = "${var.app_name}-openai-pe-${var.app_env}"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.app_name}-openai-psc-${var.app_env}"
    private_connection_resource_id = azurerm_cognitive_account.openai.id
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

  depends_on = [azurerm_cognitive_account.openai]
}

# Diagnostic settings for monitoring
resource "azurerm_monitor_diagnostic_setting" "openai" {
  name                       = "${var.app_name}-openai-diagnostics-${var.app_env}"
  target_resource_id         = azurerm_cognitive_account.openai.id
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
