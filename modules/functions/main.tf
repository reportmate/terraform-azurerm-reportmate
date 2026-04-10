# Azure Functions App for ReportMate
# Storage alerts and other scheduled functions

# Storage account for Functions App (required for Azure Functions)
resource "azurerm_storage_account" "functions" {
  name                     = "${replace(var.function_app_name, "-", "")}storage"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  tags = var.tags
}

# Table Storage for render farm alert aggregation
# render_alerts_receive upserts per-machine rows here; render_alerts_digest
# reads them at 04:15 UTC to build the daily Teams message.
resource "azurerm_storage_table" "render_alerts" {
  name                 = "renderalerts"
  storage_account_name = azurerm_storage_account.functions.name
}

# App Service Plan (Consumption/Serverless)
resource "azurerm_service_plan" "functions" {
  name                = "${var.function_app_name}-plan"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.sku_name

  tags = var.tags
}

# Linux Function App (Python 3.11)
resource "azurerm_linux_function_app" "main" {
  name                = var.function_app_name
  resource_group_name = var.resource_group_name
  location            = var.location

  storage_account_name       = azurerm_storage_account.functions.name
  storage_account_access_key = azurerm_storage_account.functions.primary_access_key
  service_plan_id            = azurerm_service_plan.functions.id
  https_only                 = true

  site_config {
    application_stack {
      python_version = "3.11"
    }

    application_insights_connection_string = var.app_insights_connection_string

    # CORS configuration
    cors {
      allowed_origins = ["*"]
    }

    # Always on for dedicated plans (disabled for consumption)
    always_on = var.sku_name != "Y1" ? true : false
  }

  # Application settings / environment variables
  app_settings = merge(
    {
      "FUNCTIONS_WORKER_RUNTIME"        = "python"
      "PYTHON_ENABLE_WORKER_EXTENSIONS" = "1"
      "ENABLE_ORYX_BUILD"               = "true"
      "SCM_DO_BUILD_DURING_DEPLOYMENT"  = "true"
      "AzureWebJobsFeatureFlags"        = "EnableWorkerIndexing"

      # ReportMate API Configuration
      "REPORTMATE_API_URL"    = var.api_base_url
      "REPORTMATE_PASSPHRASE" = var.client_passphrases
      "REPORTMATE_API_KEY"    = var.client_passphrases

      # Default Teams webhook (optional - set if you want alerts)
      "TEAMS_WEBHOOK_URL" = var.teams_webhook_url

      # Render alerts table (used by render_alerts_receive / render_alerts_digest)
      "RENDER_ALERTS_TABLE" = azurerm_storage_table.render_alerts.name
    },
    # Additional indexed Teams webhooks: TEAMS_WEBHOOK_1, TEAMS_WEBHOOK_2, ...
    { for idx, url in var.teams_webhooks : "TEAMS_WEBHOOK_${idx + 1}" => url },
    var.additional_app_settings
  )

  # Managed Identity
  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# Grant Functions App access to Key Vault (if provided)
resource "azurerm_key_vault_access_policy" "functions" {
  count = var.key_vault_id != null ? 1 : 0

  key_vault_id = var.key_vault_id
  tenant_id    = azurerm_linux_function_app.main.identity[0].tenant_id
  object_id    = azurerm_linux_function_app.main.identity[0].principal_id

  secret_permissions = [
    "Get",
    "List"
  ]
}
