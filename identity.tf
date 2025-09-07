# =================================================================
# RBAC and Permissions Configuration
# This file defines all role assignments and permissions needed
# for the ReportMate application to function securely
# =================================================================

# Data source to get current Azure client configuration
data "azurerm_client_config" "current" {}

# User-assigned managed identity for secure authentication
resource "azurerm_user_assigned_identity" "main" {
  name                = "reportmate-identity"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
}

# =================================================================
# SERVICE PRINCIPAL PERMISSIONS (for Azure DevOps Pipeline)
# =================================================================

# Grant pipeline service principal Container Registry Contributor access
resource "azurerm_role_assignment" "pipeline_acr_contributor" {
  count                = var.enable_pipeline_permissions ? 1 : 0
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "Container Registry Contributor"
  principal_id         = var.pipeline_service_principal_id

  depends_on = [azurerm_container_registry.acr]
}

# Grant pipeline service principal Container Apps Contributor access
resource "azurerm_role_assignment" "pipeline_container_apps" {
  count                = var.enable_pipeline_permissions ? 1 : 0
  scope                = azurerm_resource_group.rg.id
  role_definition_name = "Container Apps Contributor"
  principal_id         = var.pipeline_service_principal_id

  depends_on = [azurerm_resource_group.rg]
}

# =================================================================
# FUNCTION APP MANAGED IDENTITY PERMISSIONS
# =================================================================

# Function App needs to access storage queues
resource "azurerm_role_assignment" "func_storage_queue_data_contributor" {
  scope                = azurerm_storage_account.reportmate.id
  role_definition_name = "Storage Queue Data Contributor"
  principal_id         = azurerm_user_assigned_identity.main.principal_id

  # Add retry logic to handle Azure API throttling
  timeouts {
    create = "10m"
    read   = "5m"
    delete = "10m"
  }

  depends_on = [
    azurerm_storage_account.reportmate,
    azurerm_user_assigned_identity.main
  ]
}

# Function App needs to access storage blobs for logs/diagnostics
resource "azurerm_role_assignment" "func_storage_blob_data_contributor" {
  scope                = azurerm_storage_account.reportmate.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.main.principal_id

  # Add retry logic to handle Azure API throttling
  timeouts {
    create = "10m"
    read   = "5m"
    delete = "10m"
  }

  depends_on = [
    azurerm_storage_account.reportmate,
    azurerm_user_assigned_identity.main,
    azurerm_role_assignment.func_storage_queue_data_contributor
  ]
}

# Function App needs to send messages to Web PubSub
resource "azurerm_role_assignment" "func_web_pubsub_service_owner" {
  scope                = azurerm_web_pubsub.wps.id
  role_definition_name = "Web PubSub Service Owner"
  principal_id         = azurerm_user_assigned_identity.main.principal_id

  # Add retry logic to handle Azure API throttling
  timeouts {
    create = "10m"
    read   = "5m"
    delete = "10m"
  }

  depends_on = [
    azurerm_web_pubsub.wps,
    azurerm_user_assigned_identity.main,
    azurerm_role_assignment.func_storage_blob_data_contributor
  ]
}

# Function App needs monitoring insights contributor for Application Insights
resource "azurerm_role_assignment" "func_monitoring_contributor" {
  scope                = azurerm_application_insights.ai.id
  role_definition_name = "Monitoring Contributor"
  principal_id         = azurerm_user_assigned_identity.main.principal_id

  depends_on = [
    azurerm_application_insights.ai,
    azurerm_user_assigned_identity.main
  ]
}

# =================================================================
# CONTAINER APP MANAGED IDENTITY PERMISSIONS
# =================================================================

# Container App needs to pull images from ACR
resource "azurerm_role_assignment" "container_acr_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.main.principal_id

  depends_on = [
    azurerm_container_registry.acr,
    azurerm_user_assigned_identity.main
  ]
}

# Container App might need to push images (for CI/CD scenarios)
resource "azurerm_role_assignment" "container_acr_push" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPush"
  principal_id         = azurerm_user_assigned_identity.main.principal_id

  depends_on = [
    azurerm_container_registry.acr,
    azurerm_user_assigned_identity.main
  ]
}

# =================================================================
# POSTGRESQL PERMISSIONS
# =================================================================

# Note: PostgreSQL Flexible Server doesn't support managed identity authentication yet
# We use connection strings for now, but this is ready for future enhancement

# =================================================================
# CROSS-SERVICE PERMISSIONS
# =================================================================

# Allow Function App to communicate with Container Apps (if needed)
resource "azurerm_role_assignment" "func_container_apps_reader" {
  scope                = azurerm_container_app_environment.env.id
  role_definition_name = "Reader"
  principal_id         = azurerm_user_assigned_identity.main.principal_id

  depends_on = [
    azurerm_container_app_environment.env,
    azurerm_user_assigned_identity.main
  ]
}

# =================================================================
# DIAGNOSTIC AND MONITORING PERMISSIONS
# =================================================================

# Log Analytics Workspace permissions for centralized logging
resource "azurerm_role_assignment" "logs_contributor" {
  scope                = azurerm_log_analytics_workspace.logs.id
  role_definition_name = "Log Analytics Contributor"
  principal_id         = azurerm_user_assigned_identity.main.principal_id

  depends_on = [
    azurerm_log_analytics_workspace.logs,
    azurerm_user_assigned_identity.main
  ]
}

# =================================================================
# OUTPUTS
# =================================================================

output "rbac_assignments_summary" {
  value = {
    managed_identity_id = azurerm_user_assigned_identity.main.id
    role_assignments = [
      "Storage Queue Data Contributor",
      "Storage Blob Data Contributor", 
      "Web PubSub Service Owner",
      "AcrPull",
      "AcrPush",
      "Monitoring Contributor",
      "Reader (Container Apps Environment)",
      "Log Analytics Contributor"
    ]
    pipeline_permissions_enabled = var.enable_pipeline_permissions
  }
}
