resource "azurerm_cosmosdb_account" "cosmosdb_sql" {
  name                          = "${var.app_name}-cosmosdb-sql"
  location                      = var.location
  resource_group_name           = var.resource_group_name
  offer_type                    = "Standard"
  kind                          = "GlobalDocumentDB"
  public_network_access_enabled = false

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

# Private Endpoint for Cosmos DB
resource "azurerm_private_endpoint" "cosmosdb_private_endpoint" {
  name                = "${var.app_name}-cosmosdb-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.app_name}-cosmosdb-psc"
    private_connection_resource_id = azurerm_cosmosdb_account.cosmosdb_sql.id
    subresource_names              = ["Sql"]
    is_manual_connection           = false
  }

  lifecycle {
    ignore_changes = [
      # Ignore changes to private_dns_zone_group, as Azure Policy
      # updates it automatically in the Azure Landing Zone.
      private_dns_zone_group,
    ]
  }

  tags = var.common_tags
}


resource "azurerm_cosmosdb_sql_database" "cosmosdb_sql_db" {
  name                = var.cosmosdb_sql_database_name
  account_name        = azurerm_cosmosdb_account.cosmosdb_sql.name
  resource_group_name = var.resource_group_name
  autoscale_settings {
    max_throughput = 4000
  }
}

# Main container for chat history, sessions, and document metadata
# Note: Vector embeddings are stored in Azure AI Search, not Cosmos DB
resource "azurerm_cosmosdb_sql_container" "cosmosdb_sql_db_container" {
  name                = var.cosmosdb_sql_database_container_name
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.cosmosdb_sql.name
  database_name       = azurerm_cosmosdb_sql_database.cosmosdb_sql_db.name
  partition_key_paths = ["/user_id"]

  # Optimized indexing policy for chat, metadata, and workflow storage
  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    # Composite index for user_id + type queries (optimizes session/document listing)
    composite_index {
      index {
        path  = "/user_id"
        order = "ascending"
      }
      index {
        path  = "/type"
        order = "ascending"
      }
    }

    # Composite index for session queries with timestamp ordering
    composite_index {
      index {
        path  = "/session_id"
        order = "ascending"
      }
      index {
        path  = "/timestamp"
        order = "ascending"
      }
    }

    # Index for last_updated for session sorting
    composite_index {
      index {
        path  = "/last_updated"
        order = "descending"
      }
      index {
        path  = "/type"
        order = "ascending"
      }
    }
  }
}

# Workflows container for Microsoft Agent Framework distributed workflow persistence
resource "azurerm_cosmosdb_sql_container" "workflows_container" {
  name                = "workflows"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.cosmosdb_sql.name
  database_name       = azurerm_cosmosdb_sql_database.cosmosdb_sql_db.name
  partition_key_paths = ["/user_id"]

  # Indexing policy for workflow state queries
  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    # Composite index for user workflow listing with status filter
    composite_index {
      index {
        path  = "/user_id"
        order = "ascending"
      }
      index {
        path  = "/status"
        order = "ascending"
      }
    }

    # Composite index for workflow type filtering
    composite_index {
      index {
        path  = "/user_id"
        order = "ascending"
      }
      index {
        path  = "/workflow_type"
        order = "ascending"
      }
    }

    # Index for updated_at for workflow sorting
    composite_index {
      index {
        path  = "/updated_at"
        order = "descending"
      }
      index {
        path  = "/type"
        order = "ascending"
      }
    }
  }
}

