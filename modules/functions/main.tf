# Service Plan for Linux Functions
resource "azurerm_service_plan" "reportmate" {
  name                = "reportmate-plan-${var.suffix}"
  resource_group_name = var.resource_group_name
  location           = var.location
  os_type            = "Linux"
  sku_name           = "Y1"

  tags = var.tags
}

# Function App
resource "azurerm_linux_function_app" "reportmate" {
  name                = "reportmate-func-${var.suffix}"
  resource_group_name = var.resource_group_name
  location           = var.location

  storage_account_name       = var.storage_account_name
  storage_account_access_key = var.storage_connection_string
  service_plan_id           = azurerm_service_plan.reportmate.id

  site_config {
    application_stack {
      python_version = "3.11"
    }
    
    cors {
      allowed_origins = ["*"]
      support_credentials = false
    }
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"              = "python"
    "AzureWebJobsFeatureFlags"             = "EnableWorkerIndexing"
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = var.application_insights_key
    "DATABASE_CONNECTION_STRING"           = var.database_connection_string
    "AZURE_STORAGE_CONNECTION_STRING"      = var.storage_connection_string
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}
