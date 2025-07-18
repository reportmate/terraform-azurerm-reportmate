# ReportMate Infrastructure Outputs

# API Outputs
output "api_url" {
  description = "URL of the ReportMate API"
  value       = module.api.function_app_url
}

output "api_hostname" {
  description = "Hostname of the ReportMate API"
  value       = module.api.function_app_hostname
}

# Frontend Outputs
output "frontend_url" {
  description = "URL of the ReportMate frontend"
  value       = var.enable_custom_domain && var.custom_domain_name != "" ? "https://${var.custom_domain_name}" : "https://${module.containers.frontend_fqdn}"
}

output "frontend_fqdn" {
  description = "FQDN of the ReportMate frontend"
  value       = module.containers.frontend_fqdn
}

# Database Outputs
output "database_hostname" {
  description = "PostgreSQL server hostname"
  value       = module.database.postgres_fqdn
}

output "database_name" {
  description = "PostgreSQL database name"
  value       = var.db_name
}

# Monitoring Outputs
output "app_insights_name" {
  description = "Application Insights instance name"
  value       = module.monitoring.app_insights_name
}

output "log_analytics_workspace_name" {
  description = "Log Analytics workspace name"
  value       = module.monitoring.log_analytics_workspace_name
}

# Resource Group
output "resource_group_name" {
  description = "Name of the created resource group"
  value       = azurerm_resource_group.rg.name
}

output "resource_group_location" {
  description = "Location of the created resource group"
  value       = azurerm_resource_group.rg.location
}
