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
module "postgresql" {
  source = "./modules/postgresql"

  app_name                     = var.app_name
  auto_grow_enabled            = var.postgres_auto_grow_enabled
  backup_retention_period      = var.postgres_backup_retention_period
  common_tags                  = var.common_tags
  database_name                = var.database_name
  db_master_password           = var.db_master_password
  geo_redundant_backup_enabled = var.postgres_geo_redundant_backup_enabled
  ha_enabled                   = var.postgres_ha_enabled
  is_postgis_enabled           = var.postgres_is_postgis_enabled
  location                     = var.location
  postgresql_admin_username    = var.postgresql_admin_username
  postgresql_sku_name          = var.postgres_sku_name
  postgresql_storage_mb        = var.postgres_storage_mb
  private_endpoint_subnet_id   = module.network.private_endpoint_subnet_id
  resource_group_name          = azurerm_resource_group.main.name
  standby_availability_zone    = var.postgres_standby_availability_zone
  zone                         = var.postgres_zone
  postgres_version             = var.postgres_version

  depends_on = [module.network]
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

module "flyway" {
  source   = "./modules/flyway"
  app_name = var.app_name

  container_instance_subnet_id = module.network.container_instance_subnet_id
  database_name                = module.postgresql.database_name
  db_master_password           = var.db_master_password
  dns_servers                  = module.network.dns_servers
  flyway_image                 = var.flyway_image
  location                     = var.location
  log_analytics_workspace_id   = module.monitoring.log_analytics_workspace_workspaceId
  log_analytics_workspace_key  = module.monitoring.log_analytics_workspace_key
  postgres_host                = module.postgresql.postgres_host
  postgresql_admin_username    = var.postgresql_admin_username
  resource_group_name          = azurerm_resource_group.main.name

  depends_on = [module.postgresql, module.monitoring]
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
  database_name                           = var.database_name
  db_master_password                      = var.db_master_password
  enable_psql_sidecar                     = var.enable_psql_sidecar
  frontend_frontdoor_resource_guid        = module.frontdoor.frontdoor_resource_guid
  frontend_possible_outbound_ip_addresses = module.frontend.possible_outbound_ip_addresses
  location                                = var.location
  log_analytics_workspace_id              = module.monitoring.log_analytics_workspace_id
  postgres_host                           = module.postgresql.postgres_host
  postgresql_admin_username               = var.postgresql_admin_username
  private_endpoint_subnet_id              = module.network.private_endpoint_subnet_id
  repo_name                               = var.repo_name
  resource_group_name                     = azurerm_resource_group.main.name
  user_assigned_identity_client_id        = azurerm_user_assigned_identity.app_service_identity.client_id
  user_assigned_identity_id               = azurerm_user_assigned_identity.app_service_identity.id

  depends_on = [module.frontend, module.flyway]
}




