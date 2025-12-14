# Quickstart: Deploy Container Apps (dev/test)

1. Ensure you have Terraform and Azure CLI installed and authenticated:

```bash
az login
az account set --subscription "<subscription-id>"
terraform init infra
```

2. Prepare variables (example `tfvars`):

```hcl
resource_group_name = "rg-myapp-dev"
location            = "Canada Central"
app_env             = "dev"
app_name            = "myapp"
backend_image       = "ghcr.io/org/repo/backend:${IMAGE_TAG}"
container_apps_subnet_id = "<from module.network output>"
log_analytics_workspace_id = "<from module.monitoring output>"
```

3. Run plan & apply in a dev environment (use a dev subscription):

```bash
terraform plan -var-file=dev.tfvars -out plan.tfplan
terraform apply plan.tfplan
```

4. Verify:
- Ensure `backend_container_app_url` output is present
- Hit health endpoint: `curl <backend_container_app_url>/health`
- Check logs in Log Analytics / App Insights

Notes:
- This quickstart uses the repository's existing `infra/` layout and variables; the new module will be referenced from `infra/main.tf` and will consume `module.network` and `module.monitoring` outputs.
- For CI-based deploys, CI builds the image and publishes to the configured container registry; manual or CI-triggered Terraform runs can pick up the new image tag.
