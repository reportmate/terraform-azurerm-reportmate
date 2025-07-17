# Required Variables
variable "resource_group_name" {
  description = "Name of the Azure Resource Group"
  type        = string
}

variable "location" {
  description = "Azure region where resources will be deployed"
  type        = string
  default     = "East US"
}

variable "database_name" {
  description = "Name of the PostgreSQL database"
  type        = string
  default     = "reportmate"
}

variable "database_admin_username" {
  description = "Administrator username for PostgreSQL server"
  type        = string
  sensitive   = true
}

variable "database_admin_password" {
  description = "Administrator password for PostgreSQL server"
  type        = string
  sensitive   = true
  validation {
    condition     = length(var.database_admin_password) >= 8
    error_message = "Database password must be at least 8 characters long."
  }
}

# Optional Variables
variable "custom_domain" {
  description = "Custom domain for the ReportMate API (optional)"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Environment = "production"
    Project     = "ReportMate"
  }
}
