# Application Insights for monitoring and telemetry
resource "azurerm_application_insights" "ai" {
  name                = "reportmate-app-insights"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  application_type    = "web"
}
