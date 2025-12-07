# Azure Bastion and Jumpbox VM

This module deploys an Azure Spot VM (Jumpbox) with Azure Bastion for secure, browser-based access to private Azure resources.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Internet                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Azure Portal (HTTPS)                         │
│                    https://portal.azure.com                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Azure Bastion (Basic SKU)                    │
│                    AzureBastionSubnet /26                       │
│                    Public IP: Standard SKU                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ RDP (Port 3389) or SSH (Port 22)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Jumpbox VM (Spot Instance)                   │
│                    Ubuntu 24.04 LTS + GNOME Desktop             │
│                    4 vCPU / 8 GB RAM (Standard_D4as_v5)         │
│                    Firefox (native) + Chrome Browsers           │
│                    xRDP for Remote Desktop                      │
│                    jumpbox-subnet /28                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Private Endpoints
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Azure PaaS Services (Private Access)               │
│    • Azure OpenAI    • Cosmos DB    • Azure AI Search           │
│    • Document Intelligence    • Key Vault                       │
└─────────────────────────────────────────────────────────────────┘
```

## Features

- **Azure Spot VM**: Cost-optimized compute with up to 90% discount vs regular pricing
- **Ubuntu 24.04 LTS**: Latest LTS release (Noble Numbat) with long-term support until 2034
- **GNOME Desktop**: Native Ubuntu desktop environment via ubuntu-desktop-minimal
- **Browsers**: Firefox (native snap) and Google Chrome pre-installed
- **xRDP**: Remote desktop access via Azure Bastion (RDP)
- **Azure Bastion**: Secure RDP/SSH without public IP on VM
- **Managed Identity**: Access Azure services without storing credentials
- **Auto-generated SSH Keys**: Keys stored in Azure and locally
- **Auto-Shutdown**: VM automatically shuts down at 7 PM PST daily
- **Auto-Start**: VM automatically starts at 8 AM PST Monday-Friday

## VM Schedule

The Jumpbox VM has automatic scheduling to minimize costs:

| Action | Time | Days | Mechanism |
|--------|------|------|-----------|
| **Auto-Shutdown** | 7:00 PM PST | Daily (including weekends) | Azure DevTest Labs Schedule |
| **Auto-Start** | 8:00 AM PST | Monday - Friday only | Azure Automation Runbook |

### Schedule Details

- **Weekdays (Mon-Fri)**: VM runs from 8 AM to 7 PM PST (11 hours)
- **Weekends (Sat-Sun)**: VM stays OFF (no auto-start on weekends)
- **Time Zone**: Pacific Standard Time (PST/PDT)

### Manual Override

If you need the VM outside scheduled hours:

```bash
# Start VM manually via Azure CLI
az vm start --resource-group <rg-name> --name <vm-name>

# Stop VM manually
az vm deallocate --resource-group <rg-name> --name <vm-name>
```

Or via Azure Portal:
1. Navigate to **Virtual Machines** → Select your Jumpbox
2. Click **Start** or **Stop** button

## Connecting to the Jumpbox VM

### Via RDP (Recommended for GUI Access)

This is the recommended method for accessing the desktop environment with browsers.

1. Navigate to the [Azure Portal](https://portal.azure.com)
2. Go to **Virtual Machines** → Select your Jumpbox VM (`*-jumpbox`)
3. Click **Connect** → **Connect via Bastion**
4. Select **Connection Type**: **RDP**
5. Enter credentials:
   - **Username**: `azureadmin`
   - **Password**: Check the file on the VM at `/home/azureadmin/.rdp_password`
6. Click **Connect**

> **First Time Setup**: The RDP password is auto-generated during VM creation. You can retrieve or change it by SSH first:
> ```bash
> # SSH into the VM first, then:
> cat ~/.rdp_password          # View the auto-generated password
> sudo passwd azureadmin       # Or set a new password
> ```

### Via SSH (Terminal Access)

1. Navigate to the [Azure Portal](https://portal.azure.com)
2. Go to **Virtual Machines** → Select your Jumpbox VM
3. Click **Connect** → **Connect via Bastion**
4. Select **Connection Type**: **SSH**
5. Select **Authentication Type**: **SSH Private Key from Local File**
6. Enter username: `azureadmin`
7. Upload the private key from `sensitive/jumpbox_ssh_key.pem`
8. Click **Connect**

### Finding the SSH Private Key

The SSH private key is automatically generated and stored in two locations:

#### 1. Azure Portal (SSH Public Keys Resource)

1. Navigate to [Azure Portal](https://portal.azure.com)
2. Search for **"SSH public keys"** in the search bar
3. Find the key named `{app_name}-jumpbox-ssh-key`
4. The public key is displayed here
5. **Note**: The private key is only available at creation time

#### 2. Local File (Generated by Terraform)

The private key is saved locally at:
```
sensitive/jumpbox_ssh_key.pem
```

⚠️ **Security Notes**:
- This file is in `.gitignore` and should **NEVER** be committed to version control
- File permissions are set to `0600` (owner read/write only)
- Store securely and rotate keys periodically

### Using the Desktop Environment

After connecting via RDP through Bastion:

1. You'll see the Ubuntu GNOME desktop environment
2. **Firefox**: Click the Firefox icon in the dock or find it in Activities
3. **Chrome**: Find Google Chrome in the Applications grid
4. **Terminal**: Press `Ctrl+Alt+T` or find Terminal in Applications
5. **Azure CLI** is pre-installed:
   ```bash
   az login --identity
   ```

### Installed Software

| Software | Purpose |
|----------|---------||
| Ubuntu Desktop (minimal) | GNOME desktop environment |
| Firefox (snap) | Native web browser |
| Google Chrome | Web browser |
| xRDP | Remote desktop server |
| Azure CLI | Azure command-line tools |
| Git, curl, wget, vim, htop | Development tools |

## Spot VM Considerations

⚠️ **Important**: This is a Spot VM which can be evicted when Azure needs the capacity.

- **Eviction Policy**: `Deallocate` - VM is stopped but disk is preserved
- **Max Price**: `-1` (pay up to regular on-demand price)
- **Use Case**: Development, testing, non-critical workloads
- **Not Recommended**: Production workloads requiring high availability

### Handling Eviction

If the VM is evicted:
1. The VM will be in a "Stopped (deallocated)" state
2. Start it again from the Azure Portal when capacity is available
3. All data on the OS disk is preserved

## Subnet Allocation

| Subnet | CIDR | Purpose |
|--------|------|---------|
| jumpbox-subnet | x.x.x.144/28 | Jumpbox VM (11 usable IPs) |
| AzureBastionSubnet | x.x.x.192/26 | Azure Bastion (59 usable IPs) |

## Security

- **No Public IP**: The Jumpbox VM has no public IP address
- **NSG Rules**: Only SSH (22) and RDP (3389) from Bastion subnet are allowed inbound
- **Private Subnet**: Default outbound access is disabled
- **Managed Identity**: VM can access Azure services without credentials

## Troubleshooting

### Bastion Connection Issues

1. Ensure NSG rules allow traffic between Bastion and VM subnets
2. Check that the VM is in "Running" state
3. Verify the username is correct

### VM Evicted

1. Check VM state in Azure Portal
2. Click "Start" to restart when capacity is available
3. Consider reserving a Standard VM for critical workloads

### Desktop Not Loading

The XFCE installation runs via `custom_data` script at first boot. Wait 5-10 minutes after initial deployment for installation to complete.

---

## Azure Bastion Cost Optimization

Azure Bastion has an hourly cost even when idle. Here are strategies to reduce costs:

### Option 1: Delete and Recreate Bastion (Recommended)

**Delete Bastion when not needed:**

```bash
# Delete Bastion (keeps the subnet and NSG)
az network bastion delete \
  --name <bastion-name> \
  --resource-group <rg-name>

# Delete the Public IP (saves ~$3/month)
az network public-ip delete \
  --name <bastion-pip-name> \
  --resource-group <rg-name>
```

**Recreate when needed:**

```bash
# Create Public IP
az network public-ip create \
  --name <bastion-pip-name> \
  --resource-group <rg-name> \
  --location canadacentral \
  --sku Standard \
  --allocation-method Static

# Create Bastion
az network bastion create \
  --name <bastion-name> \
  --resource-group <rg-name> \
  --location canadacentral \
  --vnet-name <vnet-name> \
  --public-ip-address <bastion-pip-name> \
  --sku Basic
```

### Option 2: Use Terraform Workspace Targeting

```bash
# Destroy only Bastion resources
cd infra
terraform destroy -target=module.bastion

# Recreate when needed
terraform apply -target=module.bastion
```

### Option 3: Automated Schedule with GitHub Actions

Create a scheduled workflow to delete Bastion at end of day:

```yaml
# .github/workflows/bastion-scheduler.yml
name: Bastion Cost Scheduler

on:
  schedule:
    # Delete at 7 PM PST (3 AM UTC next day)
    - cron: '0 3 * * *'
  workflow_dispatch:
    inputs:
      action:
        description: 'Action to perform'
        required: true
        default: 'delete'
        type: choice
        options:
          - delete
          - create

jobs:
  manage-bastion:
    runs-on: ubuntu-latest
    steps:
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      - name: Delete Bastion
        if: github.event.inputs.action == 'delete' || github.event_name == 'schedule'
        run: |
          az network bastion delete --name ${{ vars.BASTION_NAME }} --resource-group ${{ vars.RESOURCE_GROUP }} --yes || true
          az network public-ip delete --name ${{ vars.BASTION_PIP_NAME }} --resource-group ${{ vars.RESOURCE_GROUP }} || true
```

### Option 4: Use Bastion Developer SKU (Free)

If you only need basic access, consider using **Bastion Developer SKU**:
- **Cost**: Free (no hourly charges)
- **Limitation**: One VM connection at a time
- **No dedicated subnet required**

⚠️ **Note**: Developer SKU is not deployed via this module. It must be configured per-VM in the portal.

### Cost Comparison

| Resource | Hourly Cost | Monthly Cost (24/7) | Monthly (8AM-7PM M-F) |
|----------|-------------|---------------------|----------------------|
| Bastion Basic | ~$0.19 | ~$140 | ~$45 |
| Bastion Standard | ~$0.35 | ~$260 | ~$80 |
| Public IP (Standard) | ~$0.004 | ~$3 | ~$3 |
| **Total Basic** | - | ~$143 | ~$48 |

**Delete/Recreate Strategy**: If you only use Bastion 2 hours/day for testing, you'd pay ~$12/month instead of $143/month.

### When to Keep Bastion Running

- Multiple team members need VM access throughout the day
- You're actively debugging production issues
- You need immediate access without 5-minute deployment wait

### When to Delete Bastion

- Weekend/holiday periods
- After-hours (if using scheduled deletion)
- Project is in maintenance mode with infrequent access needs
