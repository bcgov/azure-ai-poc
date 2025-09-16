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


module "cosmos" {
  source = "./modules/cosmos"

  app_name                   = var.app_name
  common_tags                = var.common_tags
  location                   = var.location
  resource_group_name        = azurerm_resource_group.main.name
  private_endpoint_subnet_id = module.network.private_endpoint_subnet_id
  log_analytics_workspace_id = module.monitoring.log_analytics_workspace_id

  depends_on = [azurerm_resource_group.main, module.network]
}

# Azure OpenAI module
module "azure_openai" {
  source = "./modules/azure-openai"

  app_name                      = var.app_name
  app_env                       = var.app_env
  resource_group_name           = azurerm_resource_group.main.name
  location                      = var.location
  common_tags                   = var.common_tags
  openai_sku_name               = var.openai_sku_name
  private_endpoint_subnet_id    = module.network.private_endpoint_subnet_id
  log_analytics_workspace_id    = module.monitoring.log_analytics_workspace_id
  gpt_deployment_name           = var.azure_openai_deployment_name
  gpt_deployment_capacity       = var.openai_gpt_deployment_capacity
  embedding_deployment_name     = var.azure_openai_embedding_deployment
  embedding_deployment_capacity = var.openai_embedding_deployment_capacity

  depends_on = [azurerm_resource_group.main, module.network, module.monitoring]
}

# Azure AI Search module
module "azure_ai_search" {
  source = "./modules/azure-ai-search"

  app_name                            = var.app_name
  app_env                             = var.app_env
  resource_group_name                 = azurerm_resource_group.main.name
  location                            = var.location
  common_tags                         = var.common_tags
  search_sku                          = var.search_sku
  replica_count                       = var.search_replica_count
  partition_count                     = var.search_partition_count
  semantic_search_sku                 = var.search_semantic_search_sku
  hosting_mode                        = var.search_hosting_mode
  local_authentication_enabled        = var.search_local_authentication_enabled
  private_endpoint_subnet_id          = module.network.private_endpoint_subnet_id
  log_analytics_workspace_id          = module.monitoring.log_analytics_workspace_id
  enable_managed_identity_permissions = var.search_enable_managed_identity_permissions

  depends_on = [azurerm_resource_group.main, module.network, module.monitoring]
}



module "frontend" {
  source = "./modules/frontend"

  app_env                         = var.app_env
  app_name                        = var.app_name
  app_service_sku_name_frontend   = var.app_service_sku_name_frontend
  appinsights_connection_string   = module.monitoring.appinsights_connection_string
  appinsights_instrumentation_key = module.monitoring.appinsights_instrumentation_key
  common_tags                     = var.common_tags
  frontend_image                  = var.frontend_image
  frontend_subnet_id              = module.network.app_service_subnet_id
  location                        = var.location
  log_analytics_workspace_id      = module.monitoring.log_analytics_workspace_id
  repo_name                       = var.repo_name
  resource_group_name             = azurerm_resource_group.main.name

  depends_on = [module.monitoring, module.network]
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
  azure_openai_endpoint                   = module.azure_openai.openai_endpoint
  azure_openai_api_key                    = module.azure_openai.openai_primary_key
  azure_openai_deployment_name            = module.azure_openai.gpt_deployment_name
  azure_openai_embedding_deployment       = module.azure_openai.embedding_deployment_name
  backend_subnet_id                       = module.network.app_service_subnet_id
  common_tags                             = var.common_tags
  frontend_possible_outbound_ip_addresses = module.frontend.possible_outbound_ip_addresses
  location                                = var.location
  log_analytics_workspace_id              = module.monitoring.log_analytics_workspace_id
  private_endpoint_subnet_id              = module.network.private_endpoint_subnet_id
  repo_name                               = var.repo_name
  resource_group_name                     = azurerm_resource_group.main.name
  image_tag                               = var.image_tag
  azure_openai_embedding_endpoint         = module.azure_openai.openai_endpoint
  azure_openai_llm_endpoint               = module.azure_openai.openai_endpoint
  # CosmosDB
  cosmosdb_endpoint       = module.cosmos.cosmosdb_endpoint
  cosmosdb_db_name        = module.cosmos.cosmosdb_sql_database_name
  cosmosdb_container_name = module.cosmos.cosmosdb_sql_database_container_name
  depends_on              = [module.frontend, module.azure_openai, module.azure_ai_search]
}





# due to circular dependency issues this resource is created at root level
// Assign the App Service's managed identity to the Cosmos DB SQL Database with Data Contributor role

resource "azurerm_cosmosdb_sql_role_assignment" "cosmosdb_role_assignment_app_service_data_contributor" {
  resource_group_name = azurerm_resource_group.main.name
  account_name        = module.cosmos.account_name
  role_definition_id  = "${module.cosmos.account_id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = module.backend.backend_managed_identity_principal_id
  scope               = module.cosmos.account_id

  depends_on = [
    module.backend,
    module.cosmos
  ]
}
