output "container_registry_login_server" {
  value       = var.use_custom_registry ? azurerm_container_registry.acr[0].login_server : null
  description = "Container Registry login server (if using custom registry)"
}

output "container_app_environment_id" {
  value       = azurerm_container_app_environment.main.id
  description = "ID of the Container Apps environment"
}

output "frontend_dev_url" {
  value       = length(azurerm_container_app.container_dev) > 0 ? "https://${azurerm_container_app.container_dev[0].latest_revision_fqdn}" : null
  description = "Development frontend URL (if deployed)"
}

output "frontend_prod_url" {
  value       = length(azurerm_container_app.container_prod) > 0 ? "https://${azurerm_container_app.container_prod[0].latest_revision_fqdn}" : null
  description = "Production frontend URL (if deployed)"
}

output "frontend_fqdn" {
  value       = length(azurerm_container_app.container_prod) > 0 ? azurerm_container_app.container_prod[0].ingress[0].fqdn : (length(azurerm_container_app.container_dev) > 0 ? azurerm_container_app.container_dev[0].ingress[0].fqdn : null)
  description = "Primary frontend FQDN (prod if available, otherwise dev) - stable hostname"
}

output "frontend_url" {
  value       = length(azurerm_container_app.container_prod) > 0 ? "https://${azurerm_container_app.container_prod[0].ingress[0].fqdn}" : (length(azurerm_container_app.container_dev) > 0 ? "https://${azurerm_container_app.container_dev[0].ingress[0].fqdn}" : "No frontend deployed")
  description = "Primary frontend URL (prod if available, otherwise dev) - stable hostname"
}

# API Container App Outputs
output "api_fqdn" {
  value       = azurerm_container_app.api.latest_revision_fqdn
  description = "API Container App FQDN"
}

output "api_url" {
  value       = "https://${azurerm_container_app.api.latest_revision_fqdn}"
  description = "API Container App URL"
}

output "api_container_app_id" {
  value       = azurerm_container_app.api.id
  description = "ID of the API Container App"
}
