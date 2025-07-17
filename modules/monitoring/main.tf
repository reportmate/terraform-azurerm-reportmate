# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "reportmate" {
  name                = "reportmate-logs-${var.suffix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = var.tags
}

# Application Insights
resource "azurerm_application_insights" "reportmate" {
  name                = "reportmate-insights-${var.suffix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  workspace_id        = azurerm_log_analytics_workspace.reportmate.id
  application_type    = "web"

  tags = var.tags
}
