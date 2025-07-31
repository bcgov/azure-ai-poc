variable "app_name" {
  description = "Name of the application"
  type        = string
  nullable    = false
}

variable "auto_grow_enabled" {
  description = "Enable auto-grow for storage"
  type        = bool
  nullable    = false
}

variable "backup_retention_period" {
  description = "Backup retention period in days"
  type        = number
  nullable    = false
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  nullable    = false
}

variable "database_name" {
  description = "Name of the database to create"
  type        = string
  nullable    = false
}

variable "db_master_password" {
  description = "The password for the PostgreSQL admin user."
  type        = string
  sensitive   = true
  nullable    = false
}

variable "geo_redundant_backup_enabled" {
  description = "Enable geo-redundant backup"
  type        = bool
  nullable    = false
}

variable "ha_enabled" {
  description = "Enable high availability"
  type        = bool
  nullable    = false
}

variable "is_postgis_enabled" {
  description = "Enable PostGIS extension for PostgreSQL Flexible Server"
  type        = bool
  nullable    = false
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  nullable    = false
}

variable "postgres_version" {
  description = "The version of PostgreSQL to use."
  type        = string
  nullable    = false
}

variable "postgresql_admin_username" {
  description = "Administrator username for PostgreSQL server"
  type        = string
  default     = "pgadmin"
}

variable "postgresql_sku_name" {
  description = "SKU name for PostgreSQL Flexible Server"
  type        = string
  nullable    = false
}

variable "postgresql_storage_mb" {
  description = "Storage in MB for PostgreSQL server"
  type        = number
  nullable    = false
}

variable "private_endpoint_subnet_id" {
  description = "The ID of the subnet for the private endpoint."
  type        = string
  nullable    = false
}

variable "resource_group_name" {
  description = "The name of the resource group to create."
  type        = string
  nullable    = false
}

variable "standby_availability_zone" {
  description = "Availability zone for standby replica"
  type        = string
  nullable    = false
}

variable "zone" {
  description = "The availability zone for the PostgreSQL Flexible Server."
  type        = string
  nullable    = false
}