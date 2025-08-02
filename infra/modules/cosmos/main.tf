resource "azurerm_cosmosdb_account" "cosmosdb_sql" {
  name                          = "${var.app_name}-cosmosdb-sql"
  location                      = var.location
  resource_group_name           = var.resource_group_name
  offer_type                    = "Standard"
  kind                          = "GlobalDocumentDB"
  public_network_access_enabled = false

  # Enable serverless capacity mode for cost optimization
  capabilities {
    name = "EnableServerless"
  }

  # Enable vector search capability
  capabilities {
    name = "EnableNoSQLVectorSearch"
  }

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = "canadacentral"
    failover_priority = 0
  }
  tags = var.common_tags
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "azurerm_monitor_diagnostic_setting" "cosmosdb_sql_diagnostics" {
  name                       = "${var.app_name}-cosmosdb-diagnostics"
  target_resource_id         = azurerm_cosmosdb_account.cosmosdb_sql.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "DataPlaneRequests"
  }
  enabled_log {
    category = "MongoRequests"
  }
  enabled_log {
    category = "QueryRuntimeStatistics"
  }
  enabled_log {
    category = "PartitionKeyRUConsumption"
  }
  enabled_log {
    category = "ControlPlaneRequests"
  }

}


resource "azurerm_cosmosdb_sql_database" "cosmosdb_sql_db" {
  name                = var.cosmosdb_sql_database_name
  account_name        = azurerm_cosmosdb_account.cosmosdb_sql.name
  resource_group_name = var.resource_group_name
  # Remove throughput for serverless mode - not supported
}

resource "azurerm_cosmosdb_sql_container" "cosmosdb_sql_db_container" {
  name                = var.cosmosdb_sql_database_container_name
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.cosmosdb_sql.name
  database_name       = azurerm_cosmosdb_sql_database.cosmosdb_sql_db.name
  partition_key_paths = ["/partitionKey"]

  # Optimized indexing policy for document storage with embeddings
  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    excluded_path {
      path = "/embedding/?*"
    }
  }
}

