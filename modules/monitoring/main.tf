# Log Analytics Workspace for detailed logging
resource "azurerm_log_analytics_workspace" "main" {
  name                = var.log_analytics_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days

  tags = var.tags
}

# Application Insights for monitoring and telemetry
resource "azurerm_application_insights" "main" {
  name                = var.app_insights_name
  location            = var.location
  resource_group_name = var.resource_group_name
  application_type    = "web"
  workspace_id        = azurerm_log_analytics_workspace.main.id

  # Enable detailed telemetry and logging
  retention_in_days    = 90
  daily_data_cap_in_gb = var.app_insights_daily_cap

  # Disable auto-generated failure anomaly detection rules
  disable_ip_masking = false

  tags = var.tags
}

# Random suffix to ensure unique monitoring resource names
resource "random_id" "monitor_suffix" {
  byte_length = 4
}
