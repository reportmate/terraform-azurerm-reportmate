output "function_app_name" {
  description = "Name of the Function App"
  value       = azurerm_linux_function_app.reportmate.name
}

output "function_app_url" {
  description = "URL of the Function App"
  value       = "https://${azurerm_linux_function_app.reportmate.default_hostname}"
}

output "function_app_hostname" {
  description = "Hostname of the Function App"
  value       = azurerm_linux_function_app.reportmate.default_hostname
}

output "function_app_id" {
  description = "ID of the Function App"
  value       = azurerm_linux_function_app.reportmate.id
}
