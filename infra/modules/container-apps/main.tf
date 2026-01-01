# =============================================================================
# Azure Container Apps Module - Backend Only
# =============================================================================
# This module creates Azure Container Apps Environment with Consumption workload
# and a backend Container App for API services. Frontend remains in App Service.

# -----------------------------------------------------------------------------
# Container Apps Environment with Consumption Workload Profile
# -----------------------------------------------------------------------------
resource "azurerm_container_app_environment" "main" {
  name                               = "${var.app_name}-${var.app_env}-containerenv"
  location                           = var.location
  resource_group_name                = var.resource_group_name
  log_analytics_workspace_id         = var.log_analytics_workspace_id
  infrastructure_subnet_id           = var.container_apps_subnet_id
  infrastructure_resource_group_name = "${var.resource_group_name}CAE" # changing this will force , delete and recreate the managed environment
  internal_load_balancer_enabled     = true                            # Enable internal load balancer for private access
  # Consumption workload profile (serverless)
  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }

  tags = merge(var.common_tags, {
    Component = "Container Apps Environment"
    Purpose   = "Managed environment for Backend Container Apps"
    Workload  = "Consumption"
  })

  lifecycle {
    ignore_changes = [tags]
  }
}


# Update Container Apps Environment with Log Analytics shared key using Azure CLI
resource "null_resource" "container_app_env_logs" {
  triggers = {
    env_id       = azurerm_container_app_environment.main.id
    workspace_id = var.log_analytics_workspace_customer_id
  }

  provisioner "local-exec" {
    command = "az containerapp env update --name ${azurerm_container_app_environment.main.name} --resource-group ${var.resource_group_name} --logs-destination log-analytics --logs-workspace-id ${var.log_analytics_workspace_customer_id} --logs-workspace-key ${var.log_analytics_workspace_key}"
  }

  depends_on = [azurerm_container_app_environment.main]
}


# Private Endpoint for Container Apps Environment
# Note: DNS zone association will be automatically managed by Azure Policy
resource "azurerm_private_endpoint" "containerapps" {
  name                = "${var.app_name}-containerapps-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.app_name}-containerapps-psc"
    private_connection_resource_id = azurerm_container_app_environment.main.id
    subresource_names              = ["managedEnvironments"]
    is_manual_connection           = false
  }

  tags = var.common_tags

  # Lifecycle block to ignore DNS zone group changes managed by Azure Policy
  lifecycle {
    ignore_changes = [
      private_dns_zone_group,
      tags
    ]
  }
}

resource "azurerm_container_app" "backend" {
  name                         = "${var.app_name}-api"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"
  workload_profile_name        = "Consumption" # Use Consumption workload profile

  identity {
    type = var.enable_system_assigned_identity ? "SystemAssigned" : "None"
  }


  secret {
    name  = "appinsights-connection-string"
    value = var.appinsights_connection_string
  }

  secret {
    name  = "appinsights-instrumentation-key"
    value = var.appinsights_instrumentation_key
  }

  template {
    max_replicas                     = var.max_replicas
    min_replicas                     = var.min_replicas
    termination_grace_period_seconds = 10

    container {
      name   = "backend"
      image  = var.backend_image
      cpu    = var.container_cpu
      memory = var.container_memory

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      env {
        name  = "PORT"
        value = "3000"
      }
      env {
        name  = "DOCKER_ENABLE_CI"
        value = "true"
      }
      env {
        name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        value = var.appinsights_connection_string
      }
      env {
        name  = "APPINSIGHTS_INSTRUMENTATIONKEY"
        value = var.appinsights_instrumentation_key
      }
      env {
        name  = "WEBSITE_SKIP_RUNNING_KUDUAGENT"
        value = "false"
      }
      env {
        name  = "WEBSITES_ENABLE_APP_SERVICE_STORAGE"
        value = "false"
      }
      env {
        name  = "WEBSITE_ENABLE_SYNC_UPDATE_SITE"
        value = "1"
      }
      env {
        name  = "IMAGE_TAG"
        value = var.image_tag
      }
      env {
        name  = "AZURE_OPENAI_DEPLOYMENT"
        value = var.azure_openai_deployment_name
      }
      env {
        name  = "AZURE_OPENAI_API_VERSION"
        value = "2024-12-01-preview"
      }
      env {
        name  = "AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME"
        value = var.azure_openai_embedding_deployment
      }
      env {
        name  = "AZURE_OPENAI_LLM_ENDPOINT"
        value = var.azure_openai_llm_endpoint
      }
      env {
        name  = "AZURE_OPENAI_ENDPOINT"
        value = var.azure_openai_llm_endpoint
      }
      env {
        name  = "AZURE_OPENAI_EMBEDDING_ENDPOINT"
        value = var.azure_openai_embedding_endpoint
      }
      env {
        name  = "AZURE_OPENAI_API_KEY"
        value = var.azure_openai_api_key
      }
      env {
        name  = "AZURE_SEARCH_ENDPOINT"
        value = var.azure_search_endpoint
      }
      env {
        name  = "AZURE_SEARCH_INDEX_NAME"
        value = var.azure_search_index_name
      }
      env {
        name  = "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
        value = var.azure_document_intelligence_endpoint
      }
      env {
        name  = "COSMOS_DB_ENDPOINT"
        value = var.cosmosdb_endpoint
      }
      env {
        name  = "COSMOS_DB_DATABASE_NAME"
        value = var.cosmosdb_db_name
      }
      env {
        name  = "COSMOS_DB_CONTAINER_NAME"
        value = var.cosmosdb_container_name
      }
      env {
        name  = "AZURE_COSMOSDB_DIAGNOSTICS_LEVEL"
        value = "info"
      }
      env {
        name  = "AZURE_LOG_LEVEL"
        value = "error"
      }
      env {
        name  = "KEYCLOAK_URL"
        value = var.keycloak_url
      }
      env {
        name  = "KEYCLOAK_REALM"
        value = "standard"
      }
      env {
        name  = "KEYCLOAK_CLIENT_ID"
        value = "azure-poc-6086"
      }
      env {
        name  = "AZURE_SPEECH_ENDPOINT"
        value = var.azure_speech_endpoint
      }
      env {
        name  = "AZURE_SPEECH_KEY"
        value = var.azure_speech_key
      }

      startup_probe {
        transport = "HTTP"
        path      = "/health"
        port      = 3000
        timeout   = 5
      }
      readiness_probe {
        transport               = "HTTP"
        path                    = "/health"
        port                    = 3000
        timeout                 = 5
        failure_count_threshold = 3
      }
      liveness_probe {
        transport               = "HTTP"
        path                    = "/health"
        port                    = 3000
        timeout                 = 5
        failure_count_threshold = 3
      }

    }
    http_scale_rule {
      name                = "http-scaling"
      concurrent_requests = "10"
    }
  }

  ingress {
    external_enabled = false
    target_port      = 3000
    transport        = "http"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }

    allow_insecure_connections = false
  }

  tags = merge(var.common_tags, {
    Component = "Backend Container App"
    Purpose   = "API application backend"
    Workload  = "Consumption"
  })

  lifecycle {
    ignore_changes = [tags]
  }


  depends_on = [azurerm_container_app_environment.main]
}

resource "azurerm_monitor_diagnostic_setting" "container_app_env_diagnostics" {
  name                       = "${var.app_name}-ca-env-diagnostics"
  target_resource_id         = azurerm_container_app_environment.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  # Container console logs (stdout/stderr from your application)
  enabled_log {
    category = "ContainerAppConsoleLogs"
  }

  # System logs (scaling events, container restarts, platform events)
  enabled_log {
    category = "ContainerAppSystemLogs"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}
