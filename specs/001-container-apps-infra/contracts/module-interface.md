# Module Contract: `infra/modules/container-apps`

## Inputs (variables)
- `app_name` (string, required)
- `app_env` (string, required)
- `resource_group_name` (string, required)
- `location` (string, required)
- `container_apps_subnet_id` (string, required)
- `log_analytics_workspace_id` (string, required)
- `backend_image` (string, required)
- `ingress_enabled` (bool, default true)
- `target_port` (number, default 8000)
- `min_replicas` (number, default 1)
- `max_replicas` (number, default 5)
- `cpu` (number, default 0.25)
- `memory` (string, default "0.5Gi")
- `secrets` (map<string>, optional)

## Outputs
- `container_app_environment_id` (string)
- `backend_container_app_url` (string)
- `backend_container_app_id` (string)

## Behavior
- The module will provision a Container Apps Environment attached to provided subnet and connect to the provided Log Analytics workspace.
- It will create a Container App for the backend service using the provided image and configuration.
- The module will create appropriate role assignments for the app's managed identity where necessary (Key Vault and Cognitive Services as required).

## Contract guarantees
- Idempotent Terraform runs
- No secrets are emitted in outputs
