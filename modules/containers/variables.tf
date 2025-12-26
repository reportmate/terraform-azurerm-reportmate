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

variable "managed_identity_client_id" {
  type        = string
  description = "Client ID of the managed identity for Azure SDK authentication"
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

variable "app_insights_connection_string" {
  type        = string
  description = "Application Insights connection string"
  sensitive   = true
}

variable "log_analytics_workspace_id" {
  type        = string
  description = "Log Analytics workspace ID"
}

variable "key_vault_uri" {
  type        = string
  description = "Key Vault URI for secret references"
  default     = null
}

variable "auth_secrets" {
  type = object({
    nextauth_secret_name = string
    client_secret_name   = string
  })
  description = "Authentication secret names in Key Vault"
  default = null
}

variable "client_passphrases" {
  type        = string
  description = "Client authentication passphrases (comma-separated)"
  sensitive   = true
}

variable "enable_custom_domain" {
  type        = bool
  description = "Enable custom domain configuration"
  default     = false
}

variable "custom_domain_name" {
  type        = string
  description = "Custom domain name"
  default     = ""
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to resources"
  default     = {}
}

# Container Image Configuration
variable "frontend_image_tag" {
  type        = string
  description = "Frontend container image tag to deploy"
  default     = "latest"
}

# API Container Configuration
variable "api_image_tag" {
  type        = string
  description = "API container image tag to deploy"
  default     = "latest"
}

variable "database_host" {
  type        = string
  description = "Database hostname"
}

variable "database_name" {
  type        = string
  description = "Database name"
}

variable "database_username" {
  type        = string
  description = "Database username"
}

variable "database_password" {
  type        = string
  description = "Database password"
  sensitive   = true
}

variable "web_pubsub_connection" {
  type        = string
  description = "Web PubSub connection string"
  sensitive   = true
}

# Authentication Configuration
variable "auth_client_id" {
  type        = string
  description = "Azure AD Client ID"
  default     = ""
}

variable "auth_tenant_id" {
  type        = string
  description = "Azure AD Tenant ID"
  default     = ""
}

# Container Environment Configuration
variable "container_environment_name" {
  type        = string
  description = "Name of the Container Apps Environment"
  default     = "reportmate-env"
}

# Existing Registry Configuration (for non-custom registry deployments)
variable "existing_registry_server" {
  type        = string
  description = "Existing container registry server URL (used when use_custom_registry is false)"
  default     = "reportmateacr.azurecr.io"
}

# Container App Names
variable "frontend_container_name" {
  type        = string
  description = "Name of the frontend container app"
  default     = "reportmate-web-app-prod"
}

variable "api_container_name" {
  type        = string
  description = "Name of the API container app"
  default     = "reportmate-functions-api"
}

# Container Image Names (without registry prefix)
variable "frontend_image_name" {
  type        = string
  description = "Name of the frontend container image (without registry prefix)"
  default     = "reportmate"
}

variable "api_image_name" {
  type        = string
  description = "Name of the API container image (without registry prefix)"
  default     = "reportmate-api"
}

# Allowed domains for authentication
variable "allowed_domains" {
  type        = string
  description = "Comma-separated list of allowed email domains for authentication. Must be specified in terraform.tfvars"
  default     = ""
}

# Default site URL (used when custom domain is not enabled)
# This should be set to the Container App's expected FQDN pattern or a fallback URL
variable "default_site_url" {
  type        = string
  description = "Default site URL when custom domain is not enabled (derived from container environment)"
  default     = ""  # Will be computed from container environment if empty
}
