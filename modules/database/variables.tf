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
  description = "PostgreSQL storage floor in MB. Only sets the size at create time -- auto-grow owns it afterwards and the resource ignores changes to it. The default matches the live server (256 GB); a lower value would read as an attempt to shrink, which the service rejects."
  default     = 262144
}

variable "db_backup_retention_days" {
  type        = number
  description = "Point-in-time restore window. Seven days is shorter than the feedback loop on most data-quality problems here -- the 2026-07-16 storage incident ran longer than that from onset to diagnosis -- and shorter than a statutory long weekend plus a slow ticket."
  default     = 35

  validation {
    condition     = var.db_backup_retention_days >= 7 && var.db_backup_retention_days <= 35
    error_message = "Azure allows a retention window between 7 and 35 days."
  }
}

variable "db_geo_redundant_backup" {
  type        = bool
  description = "Replicate backups to the paired region. Costs roughly the backup storage again and can only be set when the server is created, so flipping it on an existing server is a rebuild, not an update."
  default     = false
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

variable "db_max_connections" {
  type        = number
  description = "Postgres max_connections. Static parameter: raising it restarts the server. Keep in step with api_db_pool_max * api_max_replicas in the containers module."
  default     = 50
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to resources"
  default     = {}
}
