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

# App Service Plan (Flex Consumption — replaces retired Linux Y1 Consumption).
# Renamed from "<app>-plan": Y1->FC1 is not an in-place SKU change, so a fresh
# plan is created and the old one destroyed.
resource "azurerm_service_plan" "functions" {
  name                = "${var.function_app_name}-flex-plan"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.sku_name

  tags = var.tags
}

# Flex Consumption requires a dedicated blob container for the deployment package.
resource "azurerm_storage_container" "deployments" {
  name               = "deployments"
  storage_account_id = azurerm_storage_account.functions.id
}

# Function App (Flex Consumption, Python 3.11)
resource "azurerm_function_app_flex_consumption" "main" {
  name                = var.function_app_name
  resource_group_name = var.resource_group_name
  location            = var.location
  service_plan_id     = azurerm_service_plan.functions.id
  https_only          = true

  # Deployment-package storage, access-key auth (like-for-like with the old app).
  # The runtime AzureWebJobsStorage is set explicitly in app_settings below
  # because the Flex resource does not auto-wire it.
  storage_container_type      = "blobContainer"
  storage_container_endpoint  = "${azurerm_storage_account.functions.primary_blob_endpoint}${azurerm_storage_container.deployments.name}"
  storage_authentication_type = "StorageAccountConnectionString"
  storage_access_key          = azurerm_storage_account.functions.primary_access_key

  runtime_name    = "python"
  runtime_version = "3.11"

  instance_memory_in_mb  = 512
  maximum_instance_count = 40

  site_config {
    application_insights_connection_string = var.app_insights_connection_string

    cors {
      allowed_origins = ["*"]
    }
  }

  # Application settings / environment variables
  app_settings = merge(
    {
      # Runtime storage (timers, keys, locks) — Flex does not auto-wire this the
      # way storage_account_access_key did, so set it explicitly.
      "AzureWebJobsStorage"             = azurerm_storage_account.functions.primary_connection_string
      "PYTHON_ENABLE_WORKER_EXTENSIONS" = "1"
      "AzureWebJobsFeatureFlags"        = "EnableWorkerIndexing"

      # ReportMate API Configuration
      "REPORTMATE_API_URL"    = var.api_base_url
      "REPORTMATE_PASSPHRASE" = var.client_passphrases
      "REPORTMATE_API_KEY"    = var.client_passphrases

      # Default Teams webhook (optional - set if you want alerts)
      "TEAMS_WEBHOOK_URL" = var.teams_webhook_url

      # Render alerts table (used by render_alerts_receive / render_alerts_digest)
      "RENDER_ALERTS_TABLE" = azurerm_storage_table.render_alerts.name

      "APPLICATIONINSIGHTS_DISABLE_DEPENDENCY_TRACKING" = "true"
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
  tenant_id    = azurerm_function_app_flex_consumption.main.identity[0].tenant_id
  object_id    = azurerm_function_app_flex_consumption.main.identity[0].principal_id

  secret_permissions = [
    "Get",
    "List"
  ]
}
