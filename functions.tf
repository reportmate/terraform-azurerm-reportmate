# Linux Function App for API endpoints and queue processing
resource "azurerm_service_plan" "plan" {
  name                = "reportmate-functions"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = "Y1"
}

resource "azurerm_linux_function_app" "func" {
  name                       = "reportmate-api"
  resource_group_name        = azurerm_resource_group.rg.name
  location                   = azurerm_resource_group.rg.location
  service_plan_id            = azurerm_service_plan.plan.id
  storage_account_name       = azurerm_storage_account.reportmate.name
  storage_account_access_key = azurerm_storage_account.reportmate.primary_access_key

  # Assign managed identity to Function App
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.main.id]
  }

  site_config {
    application_stack {
      python_version = "3.12"
    }
  }

  app_settings = {
    FUNCTIONS_WORKER_RUNTIME               = "python"
    WEBSITE_RUN_FROM_PACKAGE               = "1"
    AZURE_STORAGE_CONNECTION_STRING        = azurerm_storage_account.reportmate.primary_connection_string
    QUEUE_NAME                             = azurerm_storage_queue.ingest.name
    DATABASE_URL                           = "postgresql://${var.db_username}:${var.db_password}@${azurerm_postgresql_flexible_server.pg.fqdn}:5432/${azurerm_postgresql_flexible_server_database.db.name}?sslmode=require"
    EVENTS_CONNECTION                      = azurerm_web_pubsub.wps.primary_connection_string
    WebPubSubConnectionString              = azurerm_web_pubsub.wps.primary_connection_string
    APPINSIGHTS_INSTRUMENTATIONKEY         = azurerm_application_insights.ai.instrumentation_key
    APPLICATIONINSIGHTS_CONNECTION_STRING  = azurerm_application_insights.ai.connection_string
    APPINSIGHTS_CONNECTION_STRING          = azurerm_application_insights.ai.connection_string
    # Managed Identity configuration
    AZURE_CLIENT_ID                        = azurerm_user_assigned_identity.main.client_id
    # Client authentication
    CLIENT_PASSPHRASES                     = var.client_passphrases
    ENABLE_MACHINE_GROUPS                  = var.enable_machine_groups
    ENABLE_BUSINESS_UNITS                  = var.enable_business_units
  }

  lifecycle {
    ignore_changes = [
      tags["hidden-link: /app-insights-resource-id"],
      app_settings["APPINSIGHTS_INSTRUMENTATIONKEY"],
      app_settings["APPLICATIONINSIGHTS_CONNECTION_STRING"],
      app_settings["APPINSIGHTS_CONNECTION_STRING"],
      app_settings["DATABASE_URL"]
    ]
  }
}
