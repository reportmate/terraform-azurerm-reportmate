output "key_vault_id" {
  description = "ID of the Key Vault"
  value       = azurerm_key_vault.reportmate.id
}

output "key_vault_name" {
  description = "Name of the Key Vault"
  value       = azurerm_key_vault.reportmate.name
}

output "key_vault_uri" {
  description = "URI of the Key Vault"
  value       = azurerm_key_vault.reportmate.vault_uri
}

# =================================================================
# SECRET OUTPUTS - Key Vault Secret References
# =================================================================

# Database Configuration Secret IDs
output "db_password_secret_id" {
  description = "Key Vault secret ID for database password"
  value       = azurerm_key_vault_secret.db_password.id
  sensitive   = true
}

output "postgres_server_name_secret_id" {
  description = "Key Vault secret ID for PostgreSQL server name"
  value       = azurerm_key_vault_secret.postgres_server_name.id
}

output "db_username_secret_id" {
  description = "Key Vault secret ID for database username"
  value       = azurerm_key_vault_secret.db_username.id
}

output "db_name_secret_id" {
  description = "Key Vault secret ID for database name"
  value       = azurerm_key_vault_secret.db_name.id
}

# Authentication Configuration Secret IDs
output "azure_ad_client_id_secret_id" {
  description = "Key Vault secret ID for Azure AD client ID"
  value       = azurerm_key_vault_secret.azure_ad_client_id.id
  sensitive   = true
}

output "azure_ad_tenant_id_secret_id" {
  description = "Key Vault secret ID for Azure AD tenant ID"
  value       = azurerm_key_vault_secret.azure_ad_tenant_id.id
  sensitive   = true
}

# Client Authentication Secret IDs
output "client_passphrase_secret_id" {
  description = "Key Vault secret ID for client passphrase"
  value       = azurerm_key_vault_secret.client_passphrase.id
  sensitive   = true
}

# Security Group Secret ID
output "devops_group_object_id_secret_id" {
  description = "Key Vault secret ID for DevOps group object ID"
  value       = azurerm_key_vault_secret.devops_group_object_id.id
  sensitive   = true
}

# Domain Configuration Secret ID
output "custom_domain_name_secret_id" {
  description = "Key Vault secret ID for custom domain name"
  value       = azurerm_key_vault_secret.custom_domain_name.id
}

# NextAuth Secret ID
output "nextauth_secret_id" {
  description = "Key Vault secret ID for NextAuth secret"
  value       = azurerm_key_vault_secret.nextauth_secret.id
  sensitive   = true
}

# Secret names for reference by applications
output "secret_names" {
  description = "Map of secret names in Key Vault"
  value = {
    db_password              = azurerm_key_vault_secret.db_password.name
    postgres_server_name     = azurerm_key_vault_secret.postgres_server_name.name
    db_username              = azurerm_key_vault_secret.db_username.name
    db_name                  = azurerm_key_vault_secret.db_name.name
    azure_ad_client_id       = azurerm_key_vault_secret.azure_ad_client_id.name
    azure_ad_tenant_id       = azurerm_key_vault_secret.azure_ad_tenant_id.name
    client_passphrase        = azurerm_key_vault_secret.client_passphrase.name
    devops_group_object_id   = azurerm_key_vault_secret.devops_group_object_id.name
    custom_domain_name       = azurerm_key_vault_secret.custom_domain_name.name
    nextauth_secret          = azurerm_key_vault_secret.nextauth_secret.name
  }
}
