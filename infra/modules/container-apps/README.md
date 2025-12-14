# Container Apps module

This Terraform module provisions an Azure Container Apps Environment and a Container App for the backend service.

Inputs
- `app_name`, `app_env`, `resource_group_name`, `location`, `common_tags`
- `container_apps_subnet_id` - subnet id from `module.network`
- `log_analytics_workspace_id` - log analytics workspace id from `module.monitoring`
- `backend_image` - image for the backend

Outputs
- `container_app_environment_id`, `backend_container_app_url`, `backend_container_app_id`

Notes
- Follow repo patterns for tags and managed identities; role assignments for Key Vault or other resources should be added in the root `infra/main.tf` if they need cross-module coordination.
