# ReportMate Infrastructure Outputs

# API Outputs
output "api_url" {
  description = "URL of the ReportMate API"
  value       = module.functions.function_app_url
}

output "api_hostname" {
  description = "Hostname of the ReportMate API"
  value       = module.functions.function_app_hostname
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

# =================================================================
# AUTHENTICATION OUTPUTS
# =================================================================

output "auth_application_id" {
  description = "Azure AD Application (Client) ID"
  value       = module.auth.application_id
}

output "auth_tenant_id" {
  description = "Azure AD Tenant ID"
  value       = module.auth.tenant_id
}

output "auth_signin_url" {
  description = "Sign-in URL for the application"
  value       = "${var.enable_custom_domain && var.custom_domain_name != "" ? "https://${var.custom_domain_name}" : module.containers.frontend_url}/auth/signin"
}

output "auth_environment_variables" {
  description = "Environment variables for web application authentication"
  value       = module.auth.environment_variables
  sensitive   = true
}

output "auth_setup_instructions" {
  description = "Instructions for completing the authentication setup"
  value       = module.auth.setup_instructions
}

output "auth_app_roles" {
  description = "Configured application roles"
  value       = module.auth.app_roles
}

# Key Vault outputs (if enabled)
output "key_vault_name" {
  description = "Name of the Key Vault (if enabled)"
  value       = var.enable_key_vault ? module.key_vault[0].key_vault_name : null
}

output "key_vault_uri" {
  description = "URI of the Key Vault (if enabled)"
  value       = var.enable_key_vault ? module.key_vault[0].key_vault_uri : null
}

output "auth_key_vault_secrets" {
  description = "Names of authentication secrets stored in Key Vault"
  value       = module.auth.key_vault_secret_names
}
