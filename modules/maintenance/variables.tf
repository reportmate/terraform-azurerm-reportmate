variable "resource_prefix" {
  description = "Prefix for all resource names"
  type        = string
  default     = "reportmate"
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "container_app_environment_id" {
  description = "ID of the Container App Environment"
  type        = string
}

variable "acr_login_server" {
  description = "ACR login server URL"
  type        = string
}

variable "acr_admin_username" {
  description = "ACR admin username"
  type        = string
}

variable "acr_admin_password" {
  description = "ACR admin password"
  type        = string
  sensitive   = true
}

variable "db_host" {
  description = "PostgreSQL database host"
  type        = string
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "reportmate"
}

variable "db_user" {
  description = "PostgreSQL database user"
  type        = string
  default     = "reportmate"
}

variable "db_password" {
  description = "PostgreSQL database password"
  type        = string
  sensitive   = true
}

variable "event_retention_days" {
  description = "Number of days to retain events"
  type        = number
  default     = 30
}

variable "schedule_cron" {
  description = "Cron expression for maintenance schedule (default: 2 AM UTC daily)"
  type        = string
  default     = "0 2 * * *"
}
