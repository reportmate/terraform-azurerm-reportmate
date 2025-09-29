# Azure Key Vault for ReportMate secret storage
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.33"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }
}

# Get current client configuration
data "azurerm_client_config" "current" {}

# Create Key Vault
resource "azurerm_key_vault" "reportmate" {
  name                = var.key_vault_name
  location            = var.location
  resource_group_name = var.resource_group_name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = var.sku_name

  # Network access rules
  network_acls {
    bypass         = "AzureServices"
    default_action = var.default_network_action
    ip_rules       = var.allowed_ips
  }

  # RBAC for access control
  rbac_authorization_enabled = true

  # Security features
  purge_protection_enabled   = var.enable_purge_protection
  soft_delete_retention_days = var.soft_delete_retention_days

  tags = var.tags
}

# Grant access to the current user/service principal
resource "azurerm_role_assignment" "current_user" {
  scope                = azurerm_key_vault.reportmate.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Grant access to managed identity (will be created after managed identity exists)
# Note: This will be created in a separate apply after the managed identity exists
# resource "azurerm_role_assignment" "managed_identity" {
#   scope                = azurerm_key_vault.reportmate.id
#   role_definition_name = "Key Vault Secrets User"
#   principal_id         = var.managed_identity_principal_id
#   
#   # Only create this if managed identity principal ID is provided
#   count = var.managed_identity_principal_id != "" && var.managed_identity_principal_id != null ? 1 : 0
# }

# Grant access to DevOps Resource InfraSec group
resource "azurerm_role_assignment" "devops_group" {
  count                = var.devops_resource_infrasec_group_object_id != null ? 1 : 0
  scope                = azurerm_key_vault.reportmate.id
  role_definition_name = "Key Vault Administrator"
  principal_type       = "Group"
  principal_id         = var.devops_resource_infrasec_group_object_id
}

# =================================================================
# KEY VAULT SECRETS - Infrastructure as Code
# =================================================================

# Database Configuration Secrets
resource "azurerm_key_vault_secret" "db_password" {
  name         = "reportmate-db-password"
  value        = var.db_password
  key_vault_id = azurerm_key_vault.reportmate.id
  content_type = "PostgreSQL database password for reportmate user"

  tags = merge(var.tags, {
    Purpose = "Database Authentication"
    Type    = "Password"
  })

  depends_on = [azurerm_role_assignment.current_user]
}

resource "azurerm_key_vault_secret" "postgres_server_name" {
  name         = "reportmate-postgres-server-name"
  value        = var.postgres_server_name
  key_vault_id = azurerm_key_vault.reportmate.id
  content_type = "PostgreSQL server name"

  tags = merge(var.tags, {
    Purpose = "Database Configuration"
    Type    = "ServerName"
  })

  depends_on = [azurerm_role_assignment.current_user]
}

resource "azurerm_key_vault_secret" "db_username" {
  name         = "reportmate-db-username"
  value        = var.db_username
  key_vault_id = azurerm_key_vault.reportmate.id
  content_type = "PostgreSQL database username"

  tags = merge(var.tags, {
    Purpose = "Database Configuration"
    Type    = "Username"
  })

  depends_on = [azurerm_role_assignment.current_user]
}

resource "azurerm_key_vault_secret" "db_name" {
  name         = "reportmate-db-name"
  value        = var.db_name
  key_vault_id = azurerm_key_vault.reportmate.id
  content_type = "PostgreSQL database name"

  tags = merge(var.tags, {
    Purpose = "Database Configuration"
    Type    = "DatabaseName"
  })

  depends_on = [azurerm_role_assignment.current_user]
}

# Authentication Configuration Secrets
resource "azurerm_key_vault_secret" "azure_ad_client_id" {
  name         = "reportmate-azure-ad-client-id"
  value        = var.azure_ad_client_id
  key_vault_id = azurerm_key_vault.reportmate.id
  content_type = "Azure AD application client ID"

  tags = merge(var.tags, {
    Purpose = "Azure AD Authentication"
    Type    = "ClientID"
  })

  depends_on = [azurerm_role_assignment.current_user]
}

resource "azurerm_key_vault_secret" "azure_ad_tenant_id" {
  name         = "reportmate-azure-ad-tenant-id"
  value        = var.azure_ad_tenant_id
  key_vault_id = azurerm_key_vault.reportmate.id
  content_type = "Azure AD tenant ID"

  tags = merge(var.tags, {
    Purpose = "Azure AD Authentication"
    Type    = "TenantID"
  })

  depends_on = [azurerm_role_assignment.current_user]
}

# Client Authentication Passphrase Secret
resource "azurerm_key_vault_secret" "client_passphrase" {
  name         = "reportmate-client-passphrase"
  value        = var.client_passphrases
  key_vault_id = azurerm_key_vault.reportmate.id
  content_type = "Client authentication passphrase for Windows agents"

  tags = merge(var.tags, {
    Purpose = "Client Authentication"
    Type    = "Passphrase"
  })

  depends_on = [azurerm_role_assignment.current_user]
}

# Security Group Object ID
resource "azurerm_key_vault_secret" "devops_group_object_id" {
  name         = "reportmate-devops-group-object-id"
  value        = var.devops_resource_infrasec_group_object_id
  key_vault_id = azurerm_key_vault.reportmate.id
  content_type = "DevOps Resource InfraSec group object ID for access control"

  tags = merge(var.tags, {
    Purpose = "Access Control"
    Type    = "GroupObjectID"
  })

  depends_on = [azurerm_role_assignment.current_user]
}

# Custom Domain Configuration
resource "azurerm_key_vault_secret" "custom_domain_name" {
  name         = "reportmate-custom-domain-name"
  value        = var.custom_domain_name
  key_vault_id = azurerm_key_vault.reportmate.id
  content_type = "Custom domain name for ReportMate frontend"

  tags = merge(var.tags, {
    Purpose = "Domain Configuration"
    Type    = "DomainName"
  })

  depends_on = [azurerm_role_assignment.current_user]
}

# NextAuth Secret (for session encryption)
resource "azurerm_key_vault_secret" "nextauth_secret" {
  name         = "reportmate-nextauth-secret"
  value        = var.nextauth_secret != null ? var.nextauth_secret : random_password.nextauth_secret.result
  key_vault_id = azurerm_key_vault.reportmate.id
  content_type = "NextAuth session encryption secret"

  tags = merge(var.tags, {
    Purpose = "Web Authentication"
    Type    = "Secret"
  })

  depends_on = [azurerm_role_assignment.current_user]
}

# Generate NextAuth secret if not provided
resource "random_password" "nextauth_secret" {
  length  = 32
  special = true
}
