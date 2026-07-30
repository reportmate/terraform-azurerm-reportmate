# Database Module - PostgreSQL Flexible Server

variable "resource_group_name" {
  type        = string
  description = "Name of the resource group"
}

variable "location" {
  type        = string
  description = "Azure region"
}

variable "db_username" {
  type        = string
  description = "PostgreSQL administrator username"
}

variable "db_password" {
  type        = string
  description = "PostgreSQL administrator password"
  sensitive   = true
}

variable "db_name" {
  type        = string
  description = "Name of the database"
}

variable "db_sku_name" {
  type        = string
  description = "PostgreSQL SKU name"
  default     = "B_Standard_B1ms"
}

variable "db_storage_mb" {
  type        = number
  description = "PostgreSQL storage size in MB"
  default     = 32768
}

variable "postgres_server_name" {
  type        = string
  description = "Name of the PostgreSQL server (if empty, will generate unique name)"
  default     = ""
}

variable "allowed_ips" {
  type        = list(string)
  description = <<-EOT
    Extra client IP ranges (CIDR) allowed to reach the database, on top of the
    always-present allow_azure rule that lets Azure-hosted services connect.
    Empty by default: the database is not reachable from the public internet
    unless an operator opts in. Passing "0.0.0.0/0" creates an allow_all rule
    that exposes the server to every address on the internet - only ever do
    that knowingly, and never in production.
  EOT
  default     = []
}

variable "api_endpoint" {
  type        = string
  description = "API endpoint URL for database initialization"
  default     = ""
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to resources"
  default     = {}
}
