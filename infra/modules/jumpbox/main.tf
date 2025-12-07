# -----------------------------------------------------------------------------
# Azure Spot VM (Jumpbox) Module
# -----------------------------------------------------------------------------
# Creates a Linux Spot VM for development/testing with browser support.
# Uses Azure Spot pricing for cost optimization with Deallocate eviction policy.
# -----------------------------------------------------------------------------

# Generate SSH key pair using azapi_resource_action
resource "azapi_resource_action" "ssh_public_key_gen" {
  type        = "Microsoft.Compute/sshPublicKeys@2022-11-01"
  resource_id = azapi_resource.ssh_public_key.id
  action      = "generateKeyPair"
  method      = "POST"

  response_export_values = ["publicKey", "privateKey"]
}

# SSH Public Key resource in Azure
resource "azapi_resource" "ssh_public_key" {
  type      = "Microsoft.Compute/sshPublicKeys@2022-11-01"
  name      = "${var.app_name}-jumpbox-ssh-key"
  location  = var.location
  parent_id = "/subscriptions/${data.azurerm_subscription.current.subscription_id}/resourceGroups/${var.resource_group_name}"

  body = {}

  tags = var.common_tags
  lifecycle {
    ignore_changes = [tags]
  }
}

# Get current subscription for resource ID construction
data "azurerm_subscription" "current" {}

# Network Interface for the VM (no public IP - accessed via Bastion)
resource "azurerm_network_interface" "jumpbox" {
  name                = "${var.app_name}-jumpbox-nic"
  location            = var.location
  resource_group_name = var.resource_group_name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Dynamic"
  }

  tags = var.common_tags
  lifecycle {
    ignore_changes = [tags]
  }
}

# Azure Spot Linux Virtual Machine
resource "azurerm_linux_virtual_machine" "jumpbox" {
  name                = "${var.app_name}-jumpbox"
  resource_group_name = var.resource_group_name
  location            = var.location
  size                = var.vm_size
  admin_username      = var.admin_username

  # Spot VM Configuration
  priority        = "Spot"
  eviction_policy = "Deallocate"
  max_bid_price   = -1 # Pay up to on-demand price

  network_interface_ids = [
    azurerm_network_interface.jumpbox.id,
  ]

  admin_ssh_key {
    username   = var.admin_username
    public_key = azapi_resource_action.ssh_public_key_gen.output.publicKey
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = var.os_disk_type
    disk_size_gb         = var.os_disk_size_gb
  }

  # Ubuntu 24.04 LTS (Noble Numbat) with desktop support capability
  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  # Enable boot diagnostics with managed storage
  boot_diagnostics {
    storage_account_uri = null # Uses managed storage account
  }

  # Custom data script to install Ubuntu Desktop with native browser and xRDP
  custom_data = base64encode(<<-EOF
#!/bin/bash
set -ex
exec > /var/log/cloud-init-custom.log 2>&1

echo "Starting Ubuntu 24.04 jumpbox setup at $(date)"

# Update system packages
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

# Install Ubuntu Desktop (minimal) - includes native Firefox snap
echo "Installing Ubuntu Desktop minimal..."
DEBIAN_FRONTEND=noninteractive apt-get install -y ubuntu-desktop-minimal

# Install xRDP for remote desktop access via Bastion
echo "Installing xRDP..."
DEBIAN_FRONTEND=noninteractive apt-get install -y xrdp

# Add xrdp user to ssl-cert group (required for Ubuntu 24.04)
usermod -a -G ssl-cert xrdp

# Configure xRDP for GNOME session
echo "Configuring xRDP for GNOME..."
cat > /etc/polkit-1/localauthority/50-local.d/45-allow-colord.pkla << 'POLKIT'
[Allow Colord all Users]
Identity=unix-user:*
Action=org.freedesktop.color-manager.create-device;org.freedesktop.color-manager.create-profile;org.freedesktop.color-manager.delete-device;org.freedesktop.color-manager.delete-profile;org.freedesktop.color-manager.modify-device;org.freedesktop.color-manager.modify-profile
ResultAny=no
ResultInactive=no
ResultActive=yes
POLKIT

# Configure xRDP session
cat > /home/${var.admin_username}/.xsessionrc << 'XSESSION'
export GNOME_SHELL_SESSION_MODE=ubuntu
export XDG_CURRENT_DESKTOP=ubuntu:GNOME
export XDG_SESSION_TYPE=x11
export XDG_CONFIG_DIRS=/etc/xdg/xdg-ubuntu:/etc/xdg
XSESSION
chown ${var.admin_username}:${var.admin_username} /home/${var.admin_username}/.xsessionrc

# Enable and restart xRDP
systemctl enable xrdp
systemctl restart xrdp

# Install Google Chrome (Firefox comes with ubuntu-desktop-minimal as snap)
echo "Installing Google Chrome..."
wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /tmp/chrome.deb
DEBIAN_FRONTEND=noninteractive apt-get install -y /tmp/chrome.deb || apt-get install -f -y
rm -f /tmp/chrome.deb

# Install additional useful tools
echo "Installing additional tools..."
apt-get install -y \
  curl \
  wget \
  git \
  vim \
  htop \
  net-tools \
  dnsutils \
  jq \
  unzip \
  ca-certificates \
  gnupg \
  lsb-release

# Install Azure CLI
echo "Installing Azure CLI..."
curl -sL https://aka.ms/InstallAzureCLIDeb | bash

# Set password for admin user (for RDP login)
echo "Setting up RDP password..."
RDP_PASSWORD=$(openssl rand -base64 16)
echo "${var.admin_username}:$RDP_PASSWORD" | chpasswd
echo "RDP Password: $RDP_PASSWORD" > /home/${var.admin_username}/.rdp_password
chmod 600 /home/${var.admin_username}/.rdp_password
chown ${var.admin_username}:${var.admin_username} /home/${var.admin_username}/.rdp_password

# Clean up
apt-get autoremove -y
apt-get clean

echo "Ubuntu 24.04 jumpbox setup complete at $(date)!"
echo "RDP is ready. Connect via Azure Bastion using RDP."
echo "Firefox (snap) and Chrome are installed."
  EOF
  )

  identity {
    type = "SystemAssigned"
  }

  tags = var.common_tags
  lifecycle {
    ignore_changes = [tags]
  }
}

# Save private key to local file for documentation purposes
# NOTE: This file should be in .gitignore
resource "local_sensitive_file" "ssh_private_key" {
  content         = azapi_resource_action.ssh_public_key_gen.output.privateKey
  filename        = "${path.root}/../sensitive/jumpbox_ssh_key.pem"
  file_permission = "0600"
}

# -----------------------------------------------------------------------------
# Auto-Shutdown Schedule (7 PM PST / 3 AM UTC next day)
# -----------------------------------------------------------------------------
# Note: Azure stores time in UTC. PST = UTC-8, so 7 PM PST = 3:00 AM UTC (next day)
resource "azurerm_dev_test_global_vm_shutdown_schedule" "jumpbox" {
  virtual_machine_id    = azurerm_linux_virtual_machine.jumpbox.id
  location              = var.location
  enabled               = true
  daily_recurrence_time = "1900" # 7:00 PM in the specified timezone
  timezone              = "Pacific Standard Time"

  notification_settings {
    enabled = false # Set to true and configure webhook/email if notifications needed
  }

  tags = var.common_tags
  lifecycle {
    ignore_changes = [tags]
  }
}

# -----------------------------------------------------------------------------
# Auto-Start Schedule (8 AM PST, Monday-Friday)
# Requires Azure Automation Account with Runbook
# -----------------------------------------------------------------------------
resource "azurerm_automation_account" "jumpbox" {
  name                = "${var.app_name}-jumpbox-automation"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku_name            = "Basic"

  identity {
    type = "SystemAssigned"
  }

  tags = var.common_tags
  lifecycle {
    ignore_changes = [tags]
  }
}

# PowerShell Runbook to start the VM
resource "azurerm_automation_runbook" "start_vm" {
  name                    = "Start-JumpboxVM"
  location                = var.location
  resource_group_name     = var.resource_group_name
  automation_account_name = azurerm_automation_account.jumpbox.name
  log_verbose             = false
  log_progress            = false
  runbook_type            = "PowerShell"

  content = <<-POWERSHELL
    # Start Jumpbox VM Runbook
    # This runbook starts the VM using the Automation Account's managed identity
    
    param(
        [Parameter(Mandatory=$true)]
        [string]$ResourceGroupName,
        
        [Parameter(Mandatory=$true)]
        [string]$VMName
    )
    
    # Connect using managed identity
    try {
        Connect-AzAccount -Identity
        Write-Output "Successfully connected using managed identity"
    }
    catch {
        Write-Error "Failed to connect using managed identity: $_"
        throw $_
    }
    
    # Start the VM
    try {
        Write-Output "Starting VM: $VMName in Resource Group: $ResourceGroupName"
        Start-AzVM -ResourceGroupName $ResourceGroupName -Name $VMName
        Write-Output "VM started successfully"
    }
    catch {
        Write-Error "Failed to start VM: $_"
        throw $_
    }
  POWERSHELL

  tags = var.common_tags
  lifecycle {
    ignore_changes = [tags]
  }
}

# Schedule for weekday mornings (8 AM PST, Monday-Friday)
resource "azurerm_automation_schedule" "weekday_start" {
  name                    = "Weekday-8AM-Start"
  resource_group_name     = var.resource_group_name
  automation_account_name = azurerm_automation_account.jumpbox.name
  frequency               = "Week"
  interval                = 1
  timezone                = "America/Los_Angeles"       # Pacific Time (PST/PDT)
  start_time              = timeadd(timestamp(), "24h") # Start from tomorrow
  week_days               = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

  lifecycle {
    ignore_changes = [start_time] # Ignore changes after initial creation
  }
}

# Link the schedule to the runbook with parameters
resource "azurerm_automation_job_schedule" "start_vm" {
  resource_group_name     = var.resource_group_name
  automation_account_name = azurerm_automation_account.jumpbox.name
  schedule_name           = azurerm_automation_schedule.weekday_start.name
  runbook_name            = azurerm_automation_runbook.start_vm.name

  parameters = {
    resourcegroupname = var.resource_group_name
    vmname            = azurerm_linux_virtual_machine.jumpbox.name
  }
}

# Role assignment: Allow Automation Account to start/stop the VM
resource "azurerm_role_assignment" "automation_vm_contributor" {
  scope                = azurerm_linux_virtual_machine.jumpbox.id
  role_definition_name = "Virtual Machine Contributor"
  principal_id         = azurerm_automation_account.jumpbox.identity[0].principal_id
}

