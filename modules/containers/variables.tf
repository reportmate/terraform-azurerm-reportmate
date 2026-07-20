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
  default     = null
}

variable "client_passphrases" {
  type        = string
  description = "Client authentication passphrases (comma-separated)"
  sensitive   = true
}

variable "api_internal_secret" {
  type        = string
  description = "Shared secret for internal container-to-container API authentication (frontend to API)"
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
  default     = "" # Will be computed from container environment if empty
}

# OIDC bearer auth for the API container (provider-agnostic SSO). Inert unless
# enable_oidc_auth is true and the issuer/audience are set.
variable "enable_oidc_auth" {
  type        = bool
  description = "Enable OIDC bearer authentication on the API container (sets ENABLE_OIDC_AUTH)."
  default     = false
}

variable "oidc_issuers" {
  type        = string
  description = "Comma-separated trusted OIDC issuers for API bearer auth (OIDC_ISSUERS)."
  default     = ""
}

variable "oidc_audience" {
  type        = string
  description = "Comma-separated accepted audiences for API bearer auth (OIDC_AUDIENCE)."
  default     = ""
}

# Database connection pool sizing for the API container.
#
# The API holds a DBUtils PooledDB per replica, so the fleet-wide demand on
# Postgres is api_db_pool_max * api_max_replicas. That product must stay under
# the server's max_connections with room to spare: Postgres reserves slots for
# superuser and maintenance, and autovacuum holds several during a vacuum pass.
#
# Sizing these independently is what caused the 2026-07-20 outage — a pool of 10
# against max_replicas of 5 demanded exactly all 50 connections, so the API broke
# itself the moment autoscale reacted to a traffic surge. The precondition on the
# api_functions resource now enforces the relationship instead of leaving it to
# whoever edits one of the three numbers next.
variable "api_db_pool_max" {
  type        = number
  description = "Max pooled Postgres connections held by each API replica (DB_POOL_MAX)."
  default     = 6
}

variable "api_db_pool_min" {
  type        = number
  description = "Warm pooled Postgres connections kept per API replica (DB_POOL_MIN)."
  default     = 1
}

variable "api_max_replicas" {
  type        = number
  description = "Max API container replicas. Bounds total pool demand together with api_db_pool_max."
  default     = 5
}

variable "db_max_connections" {
  type        = number
  description = "Postgres max_connections on the ReportMate server. Used to bound total pool demand."
  default     = 50
}

variable "db_connection_reserve" {
  type        = number
  description = "Connections held back from the API pools for superuser, autovacuum, migrations, and ad-hoc admin access."
  default     = 15
}
