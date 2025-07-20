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
  description = "List of IP addresses allowed to access the database"
  default     = ["0.0.0.0/0"]
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to resources"
  default     = {}
}
