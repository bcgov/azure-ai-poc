
# App Service Plan for frontend application
resource "azurerm_service_plan" "frontend" {
  name                = "${var.app_name}-frontend-asp"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.app_service_sku_name_frontend
  tags                = var.common_tags
  lifecycle {
    ignore_changes = [tags]
  }
}

# App Service for Frontend with container
resource "azurerm_linux_web_app" "frontend" {
  name                      = "${var.repo_name}-${var.app_env}-frontend"
  resource_group_name       = var.resource_group_name
  location                  = var.location
  service_plan_id           = azurerm_service_plan.frontend.id
  virtual_network_subnet_id = var.frontend_subnet_id
  https_only                = true
  identity {
    type = "SystemAssigned"
  }
  site_config {
    always_on                               = true
    container_registry_use_managed_identity = true
    minimum_tls_version                     = "1.3"
    health_check_path                       = "/"
    health_check_eviction_time_in_min       = 2
    application_stack {
      docker_image_name   = var.frontend_image
      docker_registry_url = var.container_registry_url
    }
    ftps_state = "Disabled"
    cors {
      allowed_origins     = ["*"]
      support_credentials = false
    }
    ip_restriction_default_action = "Allow"
  }
  app_settings = {
    PORT                                  = "80"
    WEBSITES_PORT                         = "3000"
    WEBSITES_ENABLE_APP_SERVICE_STORAGE   = "false"
    DOCKER_ENABLE_CI                      = "true"
    APPLICATIONINSIGHTS_CONNECTION_STRING = var.appinsights_connection_string
    APPINSIGHTS_INSTRUMENTATIONKEY        = var.appinsights_instrumentation_key
    VITE_BACKEND_URL                      = "https://${var.repo_name}-${var.app_env}-api.azurewebsites.net"
    LOG_LEVEL                             = "info"
    VITE_KEYCLOAK_URL                     = "https://dev.loginproxy.gov.bc.ca/auth"
    VITE_KEYCLOAK_REALM                   = "standard"
    VITE_KEYCLOAK_CLIENT_ID               = "azure-poc-6086"
  }
  logs {
    detailed_error_messages = true
    failed_request_tracing  = true
    http_logs {
      file_system {
        retention_in_days = 7
        retention_in_mb   = 100
      }
    }
  }
  tags = var.common_tags
  lifecycle {
    ignore_changes = [tags]
  }

}
resource "azurerm_linux_web_app" "frontend_proxy" {
  name                      = "${var.repo_name}-${var.app_env}-proxy"
  resource_group_name       = var.resource_group_name
  location                  = var.location
  service_plan_id           = azurerm_service_plan.frontend.id
  virtual_network_subnet_id = var.frontend_subnet_id
  https_only                = true
  identity {
    type = "SystemAssigned"
  }
  site_config {
    always_on                               = true
    container_registry_use_managed_identity = true
    minimum_tls_version                     = "1.3"
    health_check_path                       = "/healthz"
    health_check_eviction_time_in_min       = 2
    application_stack {
      docker_image_name   = "ghcr.io/bcgov/nr-containers/proxy/caddy:2-alpine"
      docker_registry_url = var.container_registry_url
    }
    ftps_state = "Disabled"
    cors {
      allowed_origins     = ["*"]
      support_credentials = false
    }
    ip_restriction_default_action = "Allow"
  }
  app_settings = {
    PORT                                  = "80"
    WEBSITES_PORT                         = "80"
    WEBSITES_ENABLE_APP_SERVICE_STORAGE   = "false"
    DOCKER_ENABLE_CI                      = "true"
    APPLICATIONINSIGHTS_CONNECTION_STRING = var.appinsights_connection_string
    APPINSIGHTS_INSTRUMENTATIONKEY        = var.appinsights_instrumentation_key
    LOG_LEVEL                             = "info"
    AZURE_COSMOS_ENDPOINT                 = var.azure_cosmos_endpoint
    AZURE_COSMOS_HOST                     = var.azure_cosmos_host
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT  = var.azure_document_intelligence_endpoint
    AZURE_DOCUMENT_INTELLIGENCE_HOST      = var.azure_document_intelligence_host
    AZURE_OPENAI_ENDPOINT                 = var.azure_openai_endpoint
    AZURE_OPENAI_HOST                     = var.azure_openai_host
    AZURE_SEARCH_ENDPOINT                 = var.azure_search_endpoint
    AZURE_SEARCH_HOST                     = var.azure_search_host

  }
  logs {
    detailed_error_messages = true
    failed_request_tracing  = true
    http_logs {
      file_system {
        retention_in_days = 7
        retention_in_mb   = 100
      }
    }
  }
  tags = var.common_tags
  lifecycle {
    ignore_changes = [tags]
  }

}

# Frontend Diagnostics
resource "azurerm_monitor_diagnostic_setting" "frontend_diagnostics" {
  name                       = "${var.app_name}-frontend-diagnostics"
  target_resource_id         = azurerm_linux_web_app.frontend.id
  log_analytics_workspace_id = var.log_analytics_workspace_id
  enabled_log {
    category = "AppServiceHTTPLogs"
  }
  enabled_log {
    category = "AppServiceConsoleLogs"
  }
  enabled_log {
    category = "AppServiceAppLogs"
  }
  enabled_log {
    category = "AppServicePlatformLogs"
  }
}
resource "azurerm_monitor_diagnostic_setting" "frontend_proxy_diagnostics" {
  name                       = "${var.app_name}-frontend-proxy-diagnostics"
  target_resource_id         = azurerm_linux_web_app.frontend_proxy.id
  log_analytics_workspace_id = var.log_analytics_workspace_id
  enabled_log {
    category = "AppServiceHTTPLogs"
  }
  enabled_log {
    category = "AppServiceConsoleLogs"
  }
  enabled_log {
    category = "AppServiceAppLogs"
  }
  enabled_log {
    category = "AppServicePlatformLogs"
  }
}
