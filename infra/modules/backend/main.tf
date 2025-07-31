# Backend App Service Plan
resource "azurerm_service_plan" "backend" {
  name                = "${var.app_name}-backend-asp"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.app_service_sku_name_backend
  tags                = var.common_tags
  lifecycle {
    ignore_changes = [tags]
  }
}

# Backend App Service
resource "azurerm_linux_web_app" "backend" {
  name                      = "${var.repo_name}-${var.app_env}-api"
  resource_group_name       = var.resource_group_name
  location                  = var.location
  service_plan_id           = azurerm_service_plan.backend.id
  https_only                = true
  virtual_network_subnet_id = var.backend_subnet_id
  identity {
    type         = "UserAssigned"
    identity_ids = [var.user_assigned_identity_id]
  }
  site_config {
    always_on                                     = true
    container_registry_use_managed_identity       = true
    container_registry_managed_identity_client_id = var.user_assigned_identity_client_id
    minimum_tls_version                           = "1.3"
    health_check_path                             = "/api/health"
    health_check_eviction_time_in_min             = 2
    application_stack {
      docker_image_name   = var.api_image
      docker_registry_url = var.container_registry_url
    }
    ftps_state = "Disabled"
    cors {
      allowed_origins     = ["*"]
      support_credentials = false
    }
    dynamic "ip_restriction" {
      for_each = split(",", var.frontend_possible_outbound_ip_addresses)
      content {
        ip_address                = ip_restriction.value != "" ? "${ip_restriction.value}/32" : null
        virtual_network_subnet_id = ip_restriction.value == "" ? var.app_service_subnet_id : null
        service_tag               = ip_restriction.value == "" ? "AppService" : null
        action                    = "Allow"
        name                      = "AFInbound${replace(ip_restriction.value, ".", "")}"
        priority                  = 100
      }
    }
    ip_restriction {
      service_tag               = "AzureFrontDoor.Backend"
      ip_address                = null
      virtual_network_subnet_id = null
      action                    = "Allow"
      priority                  = 100
      headers {
        x_azure_fdid      = [var.frontend_frontdoor_resource_guid]
        x_fd_health_probe = []
        x_forwarded_for   = []
        x_forwarded_host  = []
      }
      name = "Allow traffic from Front Door"
    }
    ip_restriction {
      name        = "DenyAll"
      action      = "Deny"
      priority    = 500
      ip_address  = "0.0.0.0/0"
      description = "Deny all other traffic"
    }
  }
  app_settings = {
    NODE_ENV                              = var.node_env
    PORT                                  = "80"
    WEBSITES_PORT                         = "3000"
    DOCKER_ENABLE_CI                      = "true"
    APPLICATIONINSIGHTS_CONNECTION_STRING = var.appinsights_connection_string
    APPINSIGHTS_INSTRUMENTATIONKEY        = var.appinsights_instrumentation_key
    POSTGRES_HOST                         = var.postgres_host
    POSTGRES_USER                         = var.postgresql_admin_username
    POSTGRES_PASSWORD                     = var.db_master_password
    POSTGRES_DATABASE                     = var.database_name
    WEBSITE_SKIP_RUNNING_KUDUAGENT        = "false"
    WEBSITES_ENABLE_APP_SERVICE_STORAGE   = "false"
    WEBSITE_ENABLE_SYNC_UPDATE_SITE       = "1"
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

# Backend Autoscaler
resource "azurerm_monitor_autoscale_setting" "backend_autoscale" {
  name                = "${var.app_name}-backend-autoscale"
  resource_group_name = var.resource_group_name
  location            = var.location
  target_resource_id  = azurerm_service_plan.backend.id
  enabled             = var.backend_autoscale_enabled
  profile {
    name = "default"
    capacity {
      default = 2
      minimum = 1
      maximum = 10
    }
    rule {
      metric_trigger {
        metric_name        = "CpuPercentage"
        metric_resource_id = azurerm_service_plan.backend.id
        time_grain         = "PT1M"
        statistic          = "Average"
        time_window        = "PT5M"
        time_aggregation   = "Average"
        operator           = "GreaterThan"
        threshold          = 70
      }
      scale_action {
        direction = "Increase"
        type      = "ChangeCount"
        value     = "1"
        cooldown  = "PT1M"
      }
    }
    rule {
      metric_trigger {
        metric_name        = "CpuPercentage"
        metric_resource_id = azurerm_service_plan.backend.id
        time_grain         = "PT1M"
        statistic          = "Average"
        time_window        = "PT5M"
        time_aggregation   = "Average"
        operator           = "LessThan"
        threshold          = 30
      }
      scale_action {
        direction = "Decrease"
        type      = "ChangeCount"
        value     = "1"
        cooldown  = "PT1M"
      }
    }
  }
}

# CloudBeaver Storage Account (optional)
resource "azurerm_storage_account" "cloudbeaver" {
  count                           = var.enable_psql_sidecar ? 1 : 0
  name                            = "${replace(var.app_name, "-", "")}cbstorage"
  resource_group_name             = var.resource_group_name
  location                        = var.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  public_network_access_enabled   = false
  allow_nested_items_to_be_public = false
  tags                            = var.common_tags
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "azurerm_storage_share" "cloudbeaver_workspace" {
  count              = var.enable_psql_sidecar ? 1 : 0
  name               = "${var.app_name}-cb-workspace"
  storage_account_id = azurerm_storage_account.cloudbeaver[0].id
  quota              = 10
}

resource "azurerm_private_endpoint" "cloudbeaver_storage" {
  count               = var.enable_psql_sidecar ? 1 : 0
  name                = "${var.app_name}-cb-storage-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id
  private_service_connection {
    name                           = "${var.app_name}-cb-storage-psc"
    private_connection_resource_id = azurerm_storage_account.cloudbeaver[0].id
    subresource_names              = ["file"]
    is_manual_connection           = false
  }
  tags = var.common_tags
  lifecycle {
    ignore_changes = [tags, private_dns_zone_group]
  }
}

resource "random_string" "cloudbeaver_admin_name" {
  count   = var.enable_psql_sidecar ? 1 : 0
  length  = 12
  special = false
  upper   = false
  numeric = true
}

resource "random_password" "cloudbeaver_admin_password" {
  count   = var.enable_psql_sidecar ? 1 : 0
  length  = 16
  special = true
}

resource "azurerm_linux_web_app" "psql_sidecar" {
  count                     = var.enable_psql_sidecar ? 1 : 0
  name                      = "${var.repo_name}-${var.app_env}-cloudbeaver"
  resource_group_name       = var.resource_group_name
  location                  = var.location
  service_plan_id           = azurerm_service_plan.backend.id
  virtual_network_subnet_id = var.backend_subnet_id
  https_only                = true
  identity {
    type         = "UserAssigned"
    identity_ids = [var.user_assigned_identity_id]
  }
  site_config {
    always_on                                     = true
    container_registry_use_managed_identity       = true
    container_registry_managed_identity_client_id = var.user_assigned_identity_client_id
    minimum_tls_version                           = "1.3"
    health_check_path                             = "/"
    health_check_eviction_time_in_min             = 10
    application_stack {
      docker_image_name   = "dbeaver/cloudbeaver:latest"
      docker_registry_url = "https://index.docker.io"
    }
    ftps_state       = "Disabled"
    app_command_line = "/bin/sh -c 'mkdir -p /opt/cloudbeaver/workspace && echo \"CloudBeaver starting with persistent workspace...\" && /opt/cloudbeaver/run-server.sh'"
  }
  app_settings = {
    WEBSITES_ENABLE_APP_SERVICE_STORAGE   = "false"
    DOCKER_ENABLE_CI                      = "true"
    APPLICATIONINSIGHTS_CONNECTION_STRING = var.appinsights_connection_string
    APPINSIGHTS_INSTRUMENTATIONKEY        = var.appinsights_instrumentation_key
    WEBSITES_PORT                         = "8978"
    PORT                                  = "8978"
    CB_SERVER_NAME                        = var.app_name
    CB_SERVER_URL                         = "https://${var.app_name}-cloudbeaver-app.azurewebsites.net"
    CB_ADMIN_NAME                         = random_string.cloudbeaver_admin_name[0].result
    CB_ADMIN_PASSWORD                     = random_password.cloudbeaver_admin_password[0].result
    POSTGRES_HOST                         = var.postgres_host
    POSTGRES_USER                         = var.postgresql_admin_username
    POSTGRES_PASSWORD                     = var.db_master_password
    POSTGRES_DATABASE                     = var.database_name
    POSTGRES_PORT                         = "5432"
    CB_LOCAL_HOST_ACCESS                  = "false"
    CB_ENABLE_REVERSEPROXY_AUTH           = "false"
    CB_DEV_MODE                           = "false"
    AZURE_STORAGE_CONNECTION_STRING       = azurerm_storage_account.cloudbeaver[0].primary_connection_string
    WORKSPACE_PATH                        = "/opt/cloudbeaver/workspace"
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

# Backend Diagnostics
resource "azurerm_monitor_diagnostic_setting" "backend_diagnostics" {
  name                       = "${var.app_name}-backend-diagnostics"
  target_resource_id         = azurerm_linux_web_app.backend.id
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
