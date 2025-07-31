# -------------
# Root Level Terraform Configuration
# -------------
# Create the main resource group for all application resources
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.common_tags
  lifecycle {
    ignore_changes = [
      tags
    ]
  }
}
# User Assigned Managed Identity
resource "azurerm_user_assigned_identity" "app_service_identity" {
  depends_on          = [azurerm_resource_group.main]
  location            = var.location
  name                = "${var.app_name}-as-identity"
  resource_group_name = var.resource_group_name
  tags                = var.common_tags
}

# -------------
# Modules based on Dependency
# -------------
module "network" {
  source = "./modules/network"

  common_tags              = var.common_tags
  resource_group_name      = azurerm_resource_group.main.name
  vnet_address_space       = var.vnet_address_space
  vnet_name                = var.vnet_name
  vnet_resource_group_name = var.vnet_resource_group_name

  depends_on = [azurerm_resource_group.main]
}
module "monitoring" {
  source = "./modules/monitoring"

  app_name                     = var.app_name
  common_tags                  = var.common_tags
  location                     = var.location
  log_analytics_retention_days = var.log_analytics_retention_days
  log_analytics_sku            = var.log_analytics_sku
  resource_group_name          = azurerm_resource_group.main.name

  depends_on = [azurerm_resource_group.main, module.network]
}



module "frontdoor" {
  source = "./modules/frontdoor"

  app_name            = var.app_name
  common_tags         = var.common_tags
  frontdoor_sku_name  = var.frontdoor_sku_name
  resource_group_name = azurerm_resource_group.main.name

  depends_on = [azurerm_resource_group.main, module.network]
}


module "frontend" {
  source = "./modules/frontend"

  app_env                               = var.app_env
  app_name                              = var.app_name
  app_service_sku_name_frontend         = var.app_service_sku_name_frontend
  appinsights_connection_string         = module.monitoring.appinsights_connection_string
  appinsights_instrumentation_key       = module.monitoring.appinsights_instrumentation_key
  common_tags                           = var.common_tags
  frontend_frontdoor_resource_guid      = module.frontdoor.frontdoor_resource_guid
  frontend_image                        = var.frontend_image
  frontend_subnet_id                    = module.network.app_service_subnet_id
  frontdoor_frontend_firewall_policy_id = module.frontdoor.firewall_policy_id
  frontend_frontdoor_id                 = module.frontdoor.frontdoor_id
  location                              = var.location
  log_analytics_workspace_id            = module.monitoring.log_analytics_workspace_id
  repo_name                             = var.repo_name
  resource_group_name                   = azurerm_resource_group.main.name
  user_assigned_identity_client_id      = azurerm_user_assigned_identity.app_service_identity.client_id
  user_assigned_identity_id             = azurerm_user_assigned_identity.app_service_identity.id

  depends_on = [module.frontdoor, module.monitoring, module.network]
}

module "backend" {
  source = "./modules/backend"

  api_image                               = var.api_image
  app_env                                 = var.app_env
  app_name                                = var.app_name
  app_service_sku_name_backend            = var.app_service_sku_name_backend
  app_service_subnet_id                   = module.network.app_service_subnet_id
  appinsights_connection_string           = module.monitoring.appinsights_connection_string
  appinsights_instrumentation_key         = module.monitoring.appinsights_instrumentation_key
  backend_subnet_id                       = module.network.app_service_subnet_id
  common_tags                             = var.common_tags
  frontend_frontdoor_resource_guid        = module.frontdoor.frontdoor_resource_guid
  frontend_possible_outbound_ip_addresses = module.frontend.possible_outbound_ip_addresses
  location                                = var.location
  log_analytics_workspace_id              = module.monitoring.log_analytics_workspace_id
  private_endpoint_subnet_id              = module.network.private_endpoint_subnet_id
  repo_name                               = var.repo_name
  resource_group_name                     = azurerm_resource_group.main.name
  user_assigned_identity_client_id        = azurerm_user_assigned_identity.app_service_identity.client_id
  user_assigned_identity_id               = azurerm_user_assigned_identity.app_service_identity.id

  depends_on = [module.frontend]
}




