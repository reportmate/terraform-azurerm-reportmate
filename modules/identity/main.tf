# Random suffix for unique resource names
resource "random_id" "identity_suffix" {
  byte_length = 4
}

# User-assigned managed identity for services
resource "azurerm_user_assigned_identity" "main" {
  name                = "${var.managed_identity_name}-${random_id.identity_suffix.hex}"
  resource_group_name = var.resource_group_name
  location            = var.location

  tags = var.tags
}

# Storage Account RBAC assignments
resource "azurerm_role_assignment" "storage_blob_contributor" {
  scope                = var.storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.main.principal_id
}

resource "azurerm_role_assignment" "storage_queue_contributor" {
  scope                = var.storage_account_id
  role_definition_name = "Storage Queue Data Contributor"
  principal_id         = azurerm_user_assigned_identity.main.principal_id
}

# Web PubSub RBAC assignment
resource "azurerm_role_assignment" "web_pubsub_service_owner" {
  scope                = var.web_pubsub_id
  role_definition_name = "Web PubSub Service Owner"
  principal_id         = azurerm_user_assigned_identity.main.principal_id
}

# Application Insights RBAC assignment
resource "azurerm_role_assignment" "monitoring_contributor" {
  scope                = var.app_insights_id
  role_definition_name = "Monitoring Contributor"
  principal_id         = azurerm_user_assigned_identity.main.principal_id
}

# Optional: Pipeline service principal permissions
resource "azurerm_role_assignment" "pipeline_contributor" {
  count                = var.enable_pipeline_permissions && var.pipeline_service_principal_id != "" ? 1 : 0
  scope                = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/resourceGroups/${var.resource_group_name}"
  role_definition_name = "Contributor"
  principal_id         = var.pipeline_service_principal_id
}

# Get current client configuration
data "azurerm_client_config" "current" {}
