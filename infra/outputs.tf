output "app_url" {
  description = "The URL of the application"
  value       = module.frontend.frontend_url
}

# Azure OpenAI outputs
output "azure_openai_endpoint" {
  description = "The Azure OpenAI service endpoint"
  value       = module.azure_openai.openai_endpoint
  sensitive   = false
}

output "azure_openai_gpt_deployment_name" {
  description = "The name of the GPT model deployment"
  value       = module.azure_openai.gpt_deployment_name
}

output "azure_openai_embedding_deployment_name" {
  description = "The name of the embedding model deployment"
  value       = module.azure_openai.embedding_deployment_name
}

# Azure AI Search outputs (module disabled)
/* output "azure_search_service_name" {
  description = "The name of the Azure AI Search service"
  value       = module.azure_ai_search.search_service_name
}

output "azure_search_service_url" {
  description = "The URL of the Azure AI Search service"
  value       = module.azure_ai_search.search_service_url
} */

# Azure Document Intelligence outputs
output "azure_document_intelligence_endpoint" {
  description = "The Azure Document Intelligence service endpoint"
  value       = module.document_intelligence.endpoint
  sensitive   = false
}

output "azure_document_intelligence_host" {
  description = "The host portion of the Azure Document Intelligence endpoint"
  value       = module.document_intelligence.host
}

# -----------------------------------------------------------------------------
# Jumpbox and Bastion Outputs
# -----------------------------------------------------------------------------

output "jumpbox_vm_name" {
  description = "Name of the Jumpbox VM"
  value       = module.jumpbox.vm_name
}

output "jumpbox_private_ip" {
  description = "Private IP address of the Jumpbox VM"
  value       = module.jumpbox.private_ip_address
}

output "jumpbox_admin_username" {
  description = "Admin username for SSH access to the Jumpbox"
  value       = module.jumpbox.admin_username
}

output "jumpbox_ssh_private_key_path" {
  description = "Path to the SSH private key file for Jumpbox access"
  value       = module.jumpbox.ssh_private_key_path
}

output "bastion_name" {
  description = "Name of the Azure Bastion host"
  value       = module.bastion.bastion_name
}

output "bastion_dns_name" {
  description = "DNS name of the Azure Bastion host"
  value       = module.bastion.bastion_dns_name
}

