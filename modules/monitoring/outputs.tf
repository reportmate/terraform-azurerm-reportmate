output "app_insights_id" {
  value       = azurerm_application_insights.main.id
  description = "ID of the Application Insights instance"
}

output "app_insights_key" {
  value       = azurerm_application_insights.main.instrumentation_key
  description = "Instrumentation key of the Application Insights instance"
  sensitive   = true
}

output "app_insights_connection_string" {
  value       = azurerm_application_insights.main.connection_string
  description = "Connection string of the Application Insights instance"
  sensitive   = true
}

output "log_analytics_workspace_id" {
  value       = azurerm_log_analytics_workspace.main.workspace_id
  description = "Workspace ID of the Log Analytics workspace"
}

output "log_analytics_workspace_key" {
  value       = azurerm_log_analytics_workspace.main.primary_shared_key
  description = "Primary shared key of the Log Analytics workspace"
  sensitive   = true
}

output "log_analytics_id" {
  value       = azurerm_log_analytics_workspace.main.id
  description = "ID of the Log Analytics workspace"
}

output "app_insights_name" {
  value       = azurerm_application_insights.main.name
  description = "Name of the Application Insights instance"
}

output "log_analytics_workspace_name" {
  value       = azurerm_log_analytics_workspace.main.name
  description = "Name of the Log Analytics workspace"
}
