output "storage_account_name" {
  description = "Name of the storage account"
  value       = azurerm_storage_account.reportmate.name
}

output "storage_account_id" {
  description = "ID of the storage account"
  value       = azurerm_storage_account.reportmate.id
}

output "storage_connection_string" {
  description = "Connection string for the storage account"
  value       = azurerm_storage_account.reportmate.primary_connection_string
  sensitive   = true
}

output "storage_account_primary_access_key" {
  description = "Primary access key for the storage account"
  value       = azurerm_storage_account.reportmate.primary_access_key
  sensitive   = true
}
