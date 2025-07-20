# Azure Functions API Module
# This module creates the Azure Functions infrastructure and deploys the API code

# Random suffix for unique resource names
resource "random_id" "api_suffix" {
  byte_length = 4
}

# Service Plan for Linux Functions
resource "azurerm_service_plan" "api" {
  name                = var.service_plan_name
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.sku_name

  tags = var.tags
}

# Function App
resource "azurerm_linux_function_app" "api" {
  name                       = var.function_app_name
  resource_group_name        = var.resource_group_name
  location                   = var.location
  service_plan_id            = azurerm_service_plan.api.id
  storage_account_name       = var.storage_account_name
  storage_account_access_key = var.storage_account_access_key

  # Assign managed identity to Function App
  identity {
    type         = "UserAssigned"
    identity_ids = [var.managed_identity_id]
  }

  site_config {
    application_stack {
      python_version = var.python_version
    }

    # Enable detailed logging and monitoring
    application_insights_connection_string = var.app_insights_connection_string

    # Enable health check endpoint
    health_check_path                 = "/api/health"
    health_check_eviction_time_in_min = 2

    # CORS configuration for web app access
    cors {
      allowed_origins     = var.allowed_origins
      support_credentials = false
    }

    # Deployment configuration
    scm_use_main_ip_restriction = false
  }

  app_settings = {
    FUNCTIONS_WORKER_RUNTIME              = "python"
    WEBSITE_RUN_FROM_PACKAGE              = "1"
    AZURE_STORAGE_CONNECTION_STRING       = var.storage_connection_string
    QUEUE_NAME                            = var.queue_name
    DATABASE_URL                          = var.database_url
    EVENTS_CONNECTION                     = var.web_pubsub_connection_string
    APPINSIGHTS_INSTRUMENTATIONKEY        = var.app_insights_key
    APPLICATIONINSIGHTS_CONNECTION_STRING = var.app_insights_connection_string
    APPINSIGHTS_CONNECTION_STRING         = var.app_insights_connection_string
    
    # Managed Identity configuration
    AZURE_CLIENT_ID = var.managed_identity_client_id
    
    # Client authentication
    CLIENT_PASSPHRASES    = var.client_passphrases
    ENABLE_MACHINE_GROUPS = var.enable_machine_groups
    ENABLE_BUSINESS_UNITS = var.enable_business_units
    
    # Enhanced logging configuration
    AZURE_FUNCTIONS_ENVIRONMENT     = "Production"
    FUNCTIONS_WORKER_PROCESS_COUNT  = "1"
    WEBSITE_ENABLE_SYNC_UPDATE_SITE = "true"
    
    # Python environment
    PYTHONPATH = "/home/site/wwwroot"
    
    # Log Analytics workspace connection
    WORKSPACE_ID  = var.log_analytics_workspace_id
    WORKSPACE_KEY = var.log_analytics_workspace_key
  }

  # Deploy API code using zip deployment
  zip_deploy_file = var.enable_code_deployment ? data.archive_file.api_code[0].output_path : null

  lifecycle {
    ignore_changes = [
      tags["hidden-link: /app-insights-resource-id"],
      app_settings["APPINSIGHTS_INSTRUMENTATIONKEY"],
      app_settings["APPLICATIONINSIGHTS_CONNECTION_STRING"],
      app_settings["APPINSIGHTS_CONNECTION_STRING"],
      app_settings["WEBSITE_RUN_FROM_PACKAGE"],
      app_settings["DATABASE_URL"],
      site_config[0].application_insights_key
    ]
  }

  tags = var.tags
}

# Create deployment package if enabled
data "archive_file" "api_code" {
  count = var.enable_code_deployment ? 1 : 0
  
  type        = "zip"
  output_path = "${path.module}/api-deployment.zip"
  
  source_dir = "${path.module}/api"
  excludes = [
    "*.tf",
    "*.tfvars",
    "*.md",
    "api-deployment.zip"
  ]
}
