# Azure Key Vault for ReportMate secret storage
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.33"
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
  enable_rbac_authorization = true

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

# Grant access to managed identity
resource "azurerm_role_assignment" "managed_identity" {
  count                = var.managed_identity_principal_id != null ? 1 : 0
  scope                = azurerm_key_vault.reportmate.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = var.managed_identity_principal_id
}

# Grant access to DevOps Resource InfraSec group
resource "azurerm_role_assignment" "devops_group" {
  count                = var.devops_resource_infrasec_group_object_id != null ? 1 : 0
  scope                = azurerm_key_vault.reportmate.id
  role_definition_name = "Key Vault Administrator"
  principal_type       = "Group"
  principal_id         = var.devops_resource_infrasec_group_object_id
}
