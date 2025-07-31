include {
  path = find_in_parent_folders()
}

# Include the common terragrunt configuration for all modules
generate "tools_tfvars" {
  path              = "tools.auto.tfvars"
  if_exists         = "overwrite"
  disable_signature = true
  contents          = <<-EOF
  vnet_name = "b9cee3-tools-vwan-spoke"
  vnet_address_space = "10.46.10.0/24"
EOF
}