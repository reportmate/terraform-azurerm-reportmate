output "function_app_id" {
  description = "ID of the Azure Functions App"
  value       = azurerm_linux_function_app.main.id
}

output "function_app_name" {
  description = "Name of the Azure Functions App"
  value       = azurerm_linux_function_app.main.name
}

output "function_app_default_hostname" {
  description = "Default hostname of the Functions App"
  value       = azurerm_linux_function_app.main.default_hostname
}

output "function_app_identity_principal_id" {
  description = "Principal ID of the Functions App managed identity"
  value       = azurerm_linux_function_app.main.identity[0].principal_id
}

output "function_app_identity_tenant_id" {
  description = "Tenant ID of the Functions App managed identity"
  value       = azurerm_linux_function_app.main.identity[0].tenant_id
}

output "storage_account_name" {
  description = "Name of the storage account used by Functions App"
  value       = azurerm_storage_account.functions.name
}

output "storage_account_primary_key" {
  description = "Primary access key for Functions storage account"
  value       = azurerm_storage_account.functions.primary_access_key
  sensitive   = true
}
