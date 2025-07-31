include {
  path = find_in_parent_folders()
}
generate "dev_tfvars" {
  path              = "dev.auto.tfvars"
  if_exists         = "overwrite"
  disable_signature = true
  contents          = <<-EOF
  enable_psql_sidecar    = true
  vnet_name              = "b9cee3-dev-vwan-spoke"
  vnet_address_space     = "10.46.9.0/24"
EOF
}