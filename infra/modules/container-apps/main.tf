resource "azurerm_container_app_environment" "this" {
  name                = "${var.app_name}-${var.app_env}-cae"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.common_tags

  dynamic "vnet_configuration" {
    for_each = var.container_apps_subnet_id != "" ? [1] : []
    content {
      infrastructure_subnet_id = var.container_apps_subnet_id
    }
  }

  logs {
    log_analytics_workspace_id = var.log_analytics_workspace_id
  }

  lifecycle {
    ignore_changes = [tags]
  }
}

resource "azurerm_container_app" "backend" {
  name                     = "${var.app_name}-${var.app_env}-backend"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  managed_environment_id   = azurerm_container_app_environment.this.id
  revision_mode            = "Single"
  identity {
    type = "SystemAssigned"
  }

  configuration {
    ingress {
      external_enabled = var.ingress_enabled
      target_port      = var.target_port
      transport        = "Auto"
    }
    dapr {
      enabled = false
    }
  }

  template {
    container {
      name  = "backend"
      image = var.backend_image
      resources {
        cpu    = var.cpu
        memory = var.memory
      }
      env {
        for k, v in var.secrets : {
          name  = k
          value = v
        }
      }
    }

    scale {
      min_replicas = var.min_replicas
      max_replicas = var.max_replicas
    }
  }

  tags = var.common_tags

  lifecycle {
    ignore_changes = [tags]
  }
}

resource "azurerm_monitor_diagnostic_setting" "backend_diagnostics" {
  name                       = "${var.app_name}-backend-diagnostics"
  target_resource_id         = azurerm_container_app.backend.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  log {
    category = "ContainerAppPlatformLogs"
    enabled  = true
  }
}
