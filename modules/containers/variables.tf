# Containers Module - Azure Container Apps and Registry

variable "resource_group_name" {
  type        = string
  description = "Name of the resource group"
}

variable "location" {
  type        = string
  description = "Azure region"
}

variable "container_registry_name" {
  type        = string
  description = "Name of the Azure Container Registry (will be made globally unique)"
  default     = "reportmateacr"
}

variable "use_custom_registry" {
  type        = bool
  description = "Whether to use a custom container registry instead of official images"
  default     = false
}

variable "container_image" {
  type        = string
  description = "Container image to deploy"
  default     = "ghcr.io/reportmate/reportmate-app-web:latest"
}

variable "environment" {
  type        = string
  description = "Environment (dev, prod, both)"
  default     = "prod"
}

variable "deploy_dev" {
  type        = bool
  description = "Deploy development environment"
  default     = false
}

variable "deploy_prod" {
  type        = bool
  description = "Deploy production environment"
  default     = true
}

# Dependencies
variable "managed_identity_id" {
  type        = string
  description = "ID of the managed identity"
}

variable "managed_identity_principal_id" {
  type        = string
  description = "Principal ID of the managed identity for role assignments"
}

variable "database_url" {
  type        = string
  description = "Database connection URL"
  sensitive   = true
}

variable "web_pubsub_hostname" {
  type        = string
  description = "Web PubSub hostname"
}

variable "function_app_hostname" {
  type        = string
  description = "Function App hostname"
}

variable "app_insights_connection_string" {
  type        = string
  description = "Application Insights connection string"
  sensitive   = true
}

variable "log_analytics_workspace_id" {
  type        = string
  description = "Log Analytics workspace ID"
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to resources"
  default     = {}
}
