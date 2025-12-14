# Data / Resource Model

This document lists the Terraform resources, inputs, outputs, and relationships required for Container Apps infra.

## Resources
- `azurerm_container_app_environment` (container apps environment)
  - Inputs: `name`, `location`, `resource_group_name`, `log_analytics_workspace_id`, `subnet_id`
  - Outputs: `id`, `environment_id`

- `azurerm_container_app` (one per service)
  - Inputs: `name`, `image`, `managed_environment_id`, `cpu`, `memory`, `ingress` settings, `secrets`, `env_vars`, `registry_credentials`
  - Outputs: `fqdn`, `url`, `id`

- Role assignments for required resources (Key Vault access, Cognitive Services user role, etc.)

## Module Inputs (proposed)
- `app_name` (string)
- `app_env` (string)
- `resource_group_name` (string)
- `location` (string)
- `container_apps_subnet_id` (string)
- `log_analytics_workspace_id` (string)
- `backend_image` (string)
- `ingress_enabled` (bool, default true)
- `target_port` (number, default 8000)
- `min_replicas` (number, default 1)
- `max_replicas` (number, default 5)
- `cpu` (number, default 0.25)
- `memory` (string, default "0.5Gi")
- `secrets` (map)

## Module Outputs
- `container_app_environment_id`
- `backend_container_app_url`
- `backend_container_app_id`

## Dependencies
- `module.network.container_apps_subnet_id` required for `subnet_id`
- `module.monitoring.log_analytics_workspace_id` required for environment telemetry
- Registry credentials come from existing CI published images; module consumes image location only
