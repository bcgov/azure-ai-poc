# Browser Desktop App Service Module
# Provides a browser-based Ubuntu desktop for accessing private Azure PaaS services

# App Service Plan - P3v3 for GUI workloads (8 vCPU, 32GB RAM)
resource "azurerm_service_plan" "browser_desktop" {
  name                = "${var.app_name}-browser-desktop-asp"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.app_service_sku_name

  tags = var.common_tags
  lifecycle {
    ignore_changes = [tags]
  }
}

# App Service for browser desktop container
resource "azurerm_linux_web_app" "browser_desktop" {
  name                      = "${var.repo_name}-${var.app_env}-browser-desktop"
  resource_group_name       = var.resource_group_name
  location                  = var.location
  service_plan_id           = azurerm_service_plan.browser_desktop.id
  https_only                = true
  virtual_network_subnet_id = var.subnet_id

  identity {
    type = "SystemAssigned"
  }

  site_config {
    always_on                               = true
    container_registry_use_managed_identity = false # Using public Docker Hub
    minimum_tls_version                     = "1.3"
    ftps_state                              = "Disabled"
    websockets_enabled                      = true # Required for noVNC

    application_stack {
      docker_image_name   = "${var.docker_image}:${var.image_tag}"
      docker_registry_url = var.container_registry_url
    }

    # No IP restrictions - protected by basic auth via VNC_PW
    ip_restriction_default_action = "Allow"
  }

  app_settings = {
    # Container port configuration (accetto images use 6901 for noVNC)
    WEBSITES_PORT                       = "6901"
    DOCKER_ENABLE_CI                    = "true"
    WEBSITE_SKIP_RUNNING_KUDUAGENT      = "true"
    WEBSITES_ENABLE_APP_SERVICE_STORAGE = "false"
    WEBSITE_ENABLE_SYNC_UPDATE_SITE     = "1"

    # VNC Configuration (accetto image uses VNC_PW, not VNC_PASSWORD)
    VNC_PW         = var.vnc_password
    VNC_RESOLUTION = var.vnc_resolution
    VNC_COL_DEPTH  = "24"

    # Increase timeout for container startup (GUI is heavy)
    WEBSITES_CONTAINER_START_TIME_LIMIT = "600"
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
    application_logs {
      file_system_level = "Information"
    }
  }

  tags = var.common_tags
  lifecycle {
    ignore_changes = [tags]
  }
}

# Diagnostic settings for App Service
resource "azurerm_monitor_diagnostic_setting" "browser_desktop" {
  name                       = "${var.app_name}-browser-desktop-diag"
  target_resource_id         = azurerm_linux_web_app.browser_desktop.id
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

  enabled_metric {
    category = "AllMetrics"
  }
}
