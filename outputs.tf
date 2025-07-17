output "resource_group_name" {
  description = "Name of the created resource group"
  value       = azurerm_resource_group.reportmate.name
}

output "database_server_fqdn" {
  description = "Fully qualified domain name of the PostgreSQL server"
  value       = module.database.server_fqdn
}

output "database_connection_string" {
  description = "Connection string for the PostgreSQL database"
  value       = module.database.connection_string
  sensitive   = true
}

output "function_app_url" {
  description = "URL of the Function App"
  value       = module.functions.function_app_url
}

output "function_app_hostname" {
  description = "Hostname of the Function App"
  value       = module.functions.function_app_hostname
}

output "storage_account_name" {
  description = "Name of the storage account"
  value       = module.storage.storage_account_name
}

output "application_insights_instrumentation_key" {
  description = "Application Insights instrumentation key"
  value       = module.monitoring.application_insights_instrumentation_key
  sensitive   = true
}

output "front_door_endpoint" {
  description = "Front Door endpoint URL"
  value       = module.networking.front_door_endpoint
}
