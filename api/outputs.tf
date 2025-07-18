# API Module Outputs

output "function_app_name" {
  description = "Name of the Function App"
  value       = azurerm_linux_function_app.api.name
}

output "function_app_hostname" {
  description = "Hostname of the Function App"
  value       = azurerm_linux_function_app.api.default_hostname
}

output "function_app_url" {
  description = "URL of the Function App"
  value       = "https://${azurerm_linux_function_app.api.default_hostname}"
}

output "function_app_id" {
  description = "Resource ID of the Function App"
  value       = azurerm_linux_function_app.api.id
}

output "service_plan_id" {
  description = "Resource ID of the App Service Plan"
  value       = azurerm_service_plan.api.id
}
