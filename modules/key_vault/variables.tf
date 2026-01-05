variable "key_vault_name" {
  description = "Name of the Key Vault"
  type        = string
}

variable "location" {
  description = "Azure region for the Key Vault"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "sku_name" {
  description = "Key Vault SKU name"
  type        = string
  default     = "standard"
}

variable "default_network_action" {
  description = "Default network access action"
  type        = string
  default     = "Allow"
}

variable "allowed_ips" {
  description = "List of allowed IP addresses"
  type        = list(string)
  default     = []
}

variable "enable_purge_protection" {
  description = "Enable purge protection"
  type        = bool
  default     = true
}

variable "soft_delete_retention_days" {
  description = "Soft delete retention period in days"
  type        = number
  default     = 7
}

variable "managed_identity_principal_id" {
  description = "Principal ID of the managed identity to grant access"
  type        = string
  default     = null
}

variable "devops_resource_infrasec_group_object_id" {
  description = "Object ID of the DevOps Resource InfraSec group for Key Vault access"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

# =================================================================
# SECRET VARIABLES - Sensitive Values for Key Vault Storage
# =================================================================

variable "db_password" {
  description = "PostgreSQL database password to store in Key Vault"
  type        = string
  sensitive   = true
}

variable "postgres_server_name" {
  description = "PostgreSQL server name to store in Key Vault"
  type        = string
}

variable "db_username" {
  description = "PostgreSQL database username to store in Key Vault"
  type        = string
}

variable "db_name" {
  description = "PostgreSQL database name to store in Key Vault"
  type        = string
}

variable "azure_ad_client_id" {
  description = "Azure AD application client ID to store in Key Vault"
  type        = string
  sensitive   = true
}

variable "azure_ad_tenant_id" {
  description = "Azure AD tenant ID to store in Key Vault"
  type        = string
  sensitive   = true
}

variable "client_passphrases" {
  description = "Client authentication passphrase to store in Key Vault"
  type        = string
  sensitive   = true
}

variable "custom_domain_name" {
  description = "Custom domain name to store in Key Vault"
  type        = string
}

variable "nextauth_secret" {
  description = "NextAuth session encryption secret (optional - will be generated if not provided)"
  type        = string
  default     = null
  sensitive   = true
}

# =================================================================
# AZURE SERVICE CONNECTION STRINGS (Optional)
# These can be passed from parent module to store in Key Vault
# =================================================================

variable "storage_connection_string" {
  description = "Azure Storage Account connection string (optional)"
  type        = string
  default     = null
  sensitive   = true
}

variable "web_pubsub_connection_string" {
  description = "Azure Web PubSub connection string (optional)"
  type        = string
  default     = null
  sensitive   = true
}

variable "app_insights_connection_string" {
  description = "Application Insights connection string (optional)"
  type        = string
  default     = null
  sensitive   = true
}

variable "api_base_url" {
  description = "FastAPI container base URL (optional)"
  type        = string
  default     = null
}

variable "frontend_url" {
  description = "Frontend container URL (optional)"
  type        = string
  default     = null
}

# =================================================================
# MACOS CLIENT SIGNING SECRETS (Optional)
# Used by macOS client for code signing and notarization
# =================================================================

variable "macdev_team_id" {
  description = "macOS Team ID for code signing (optional)"
  type        = string
  default     = ""
}

variable "macdev_signing_identity_app" {
  description = "macOS Developer ID Application for code signing (optional)"
  type        = string
  default     = ""
}

variable "macdev_signing_identity_installer" {
  description = "macOS Developer ID Installer for PKG signing (optional)"
  type        = string
  default     = ""
}

variable "macdev_notarization_apple_id" {
  description = "Apple ID email for notarization (optional)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "macdev_notarization_password" {
  description = "App-specific password for Apple notarization (optional)"
  type        = string
  default     = ""
  sensitive   = true
}

# =================================================================
# AUTHENTICATION & SSH SECRETS
# Additional secrets for Azure AD authentication and SSH access
# =================================================================

variable "auth_client_id" {
  description = "Azure AD application (client) ID for authentication"
  type        = string
  default     = ""
  sensitive   = true
}

variable "auth_client_secret" {
  description = "Azure AD client secret for authentication"
  type        = string
  default     = ""
  sensitive   = true
}

variable "auth_tenant_id" {
  description = "Azure AD tenant ID for authentication"
  type        = string
  default     = ""
  sensitive   = true
}

variable "ssh_password" {
  description = "SSH password for remote access"
  type        = string
  default     = ""
  sensitive   = true
}
