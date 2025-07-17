variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "database_name" {
  description = "Name of the database"
  type        = string
}

variable "admin_username" {
  description = "Database administrator username"
  type        = string
  sensitive   = true
}

variable "admin_password" {
  description = "Database administrator password"
  type        = string
  sensitive   = true
}

variable "suffix" {
  description = "Random suffix for unique naming"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
