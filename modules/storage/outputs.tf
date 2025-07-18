output "storage_account_id" {
  value       = azurerm_storage_account.main.id
  description = "ID of the storage account"
}

output "storage_account_name" {
  value       = azurerm_storage_account.main.name
  description = "Name of the storage account"
}

output "storage_account_access_key" {
  value       = azurerm_storage_account.main.primary_access_key
  description = "Primary access key of the storage account"
  sensitive   = true
}

output "storage_connection_string" {
  value       = azurerm_storage_account.main.primary_connection_string
  description = "Primary connection string of the storage account"
  sensitive   = true
}

output "queue_name" {
  value       = azurerm_storage_queue.ingest.name
  description = "Name of the ingestion queue"
}
