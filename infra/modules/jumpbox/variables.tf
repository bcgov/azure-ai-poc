# -----------------------------------------------------------------------------
# Jumpbox Module Variables
# -----------------------------------------------------------------------------

variable "app_name" {
  description = "Name of the application, used for resource naming"
  type        = string
  nullable    = false
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  nullable    = false
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  nullable    = false
}

variable "subnet_id" {
  description = "Subnet ID for the jumpbox VM"
  type        = string
  nullable    = false
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  nullable    = false
}

variable "vm_size" {
  description = "Size of the virtual machine (4 vCPU, 8 GB RAM recommended)"
  type        = string
  default     = "Standard_D4as_v5"
  nullable    = false
}

variable "admin_username" {
  description = "Admin username for the VM"
  type        = string
  default     = "azureadmin"
  nullable    = false
}

variable "os_disk_type" {
  description = "Storage account type for the OS disk"
  type        = string
  default     = "Standard_LRS" # Use Standard for Spot VMs to reduce costs
  nullable    = false
}

variable "os_disk_size_gb" {
  description = "Size of the OS disk in GB"
  type        = number
  default     = 64
  nullable    = false
}
