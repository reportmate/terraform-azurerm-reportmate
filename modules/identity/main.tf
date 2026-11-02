# Random suffix for unique resource names
resource "random_id" "identity_suffix" {
  byte_length = 4
}

# User-assigned managed identity for services. Created unless the deployment
# brings its own (existing_managed_identity_id) and turns creation off.
resource "azurerm_user_assigned_identity" "main" {
  count = var.create_managed_identity ? 1 : 0

  name                = var.managed_identity_name
  resource_group_name = var.resource_group_name
  location            = var.location

  tags = var.tags
}

moved {
  from = azurerm_user_assigned_identity.main
  to   = azurerm_user_assigned_identity.main[0]
}

# An identity managed outside this module. Its resource id is
# /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.ManagedIdentity/userAssignedIdentities/<name>.
data "azurerm_user_assigned_identity" "existing" {
  count = var.existing_managed_identity_id != null ? 1 : 0

  name                = element(split("/", var.existing_managed_identity_id), 8)
  resource_group_name = element(split("/", var.existing_managed_identity_id), 4)
}

# The identity the services run as: the existing one when given, otherwise the
# one created here. The role assignments below always follow it.
locals {
  identity = var.existing_managed_identity_id != null ? {
    id           = data.azurerm_user_assigned_identity.existing[0].id
    client_id    = data.azurerm_user_assigned_identity.existing[0].client_id
    principal_id = data.azurerm_user_assigned_identity.existing[0].principal_id
    name         = data.azurerm_user_assigned_identity.existing[0].name
    } : {
    id           = one(azurerm_user_assigned_identity.main[*].id)
    client_id    = one(azurerm_user_assigned_identity.main[*].client_id)
    principal_id = one(azurerm_user_assigned_identity.main[*].principal_id)
    name         = one(azurerm_user_assigned_identity.main[*].name)
  }
}

# Storage Account RBAC assignments
resource "azurerm_role_assignment" "storage_blob_contributor" {
  scope                = var.storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = local.identity.principal_id

  lifecycle {
    create_before_destroy = true
  }
}

resource "azurerm_role_assignment" "storage_queue_contributor" {
  scope                = var.storage_account_id
  role_definition_name = "Storage Queue Data Contributor"
  principal_id         = local.identity.principal_id

  lifecycle {
    create_before_destroy = true
  }
}

# Application Insights RBAC assignment
resource "azurerm_role_assignment" "monitoring_contributor" {
  scope                = var.app_insights_id
  role_definition_name = "Monitoring Contributor"
  principal_id         = local.identity.principal_id

  lifecycle {
    create_before_destroy = true
  }
}

# Optional: Pipeline service principal permissions
resource "azurerm_role_assignment" "pipeline_contributor" {
  count                            = var.enable_pipeline_permissions && var.pipeline_service_principal_id != "" ? 1 : 0
  scope                            = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/resourceGroups/${var.resource_group_name}"
  role_definition_name             = "Contributor"
  principal_id                     = var.pipeline_service_principal_id
  skip_service_principal_aad_check = true
}

# Get current client configuration
data "azurerm_client_config" "current" {}
