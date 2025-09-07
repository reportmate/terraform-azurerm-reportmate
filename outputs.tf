# Core outputs
output "resource_group_name" {
  value = azurerm_resource_group.rg.name
}

# Managed Identity outputs
output "managed_identity_id" {
  value = azurerm_user_assigned_identity.main.id
}

output "managed_identity_client_id" {
  value = azurerm_user_assigned_identity.main.client_id
}

output "managed_identity_principal_id" {
  value = azurerm_user_assigned_identity.main.principal_id
}

# Function App outputs
output "function_app_url" {
  value = "https://${azurerm_linux_function_app.func.default_hostname}"
}

# Database outputs
output "postgres_connection" {
  value       = "postgresql://${var.db_username}:${var.db_password}@${azurerm_postgresql_flexible_server.pg.fqdn}:5432/${azurerm_postgresql_flexible_server_database.db.name}"
  sensitive   = true
}

output "database_fqdn" {
  value = azurerm_postgresql_flexible_server.pg.fqdn
}

# Storage outputs
output "storage_connection_string" {
  value     = azurerm_storage_account.reportmate.primary_connection_string
  sensitive = true
}

# Messaging outputs
output "web_pubsub_endpoint" {
  value = azurerm_web_pubsub.wps.hostname
}

output "web_pubsub_connection_string" {
  value     = azurerm_web_pubsub.wps.primary_connection_string
  sensitive = true
}

# Monitoring outputs
output "application_insights_key" {
  value     = azurerm_application_insights.ai.instrumentation_key
  sensitive = true
}

# Container outputs (from containers.tf)
output "container_registry_login_server" {
  value = azurerm_container_registry.acr.login_server
}

# Development Frontend URL
output "frontend_dev_url" {
  value = length(azurerm_container_app.frontend_dev) > 0 ? "https://${azurerm_container_app.frontend_dev[0].latest_revision_fqdn}" : null
  description = "Development frontend URL (if deployed)"
}

# Production Frontend URL  
output "frontend_prod_url" {
  value = length(azurerm_container_app.frontend_prod) > 0 ? (
    var.enable_custom_domain && var.custom_domain_name != "" ? 
    "https://${var.custom_domain_name}" : 
    "https://${azurerm_container_app.frontend_prod[0].latest_revision_fqdn}"
  ) : null
  description = "Production frontend URL (if deployed) - uses Front Door for custom domains"
}

# Legacy output for backward compatibility
output "frontend_url" {
  value = length(azurerm_container_app.frontend_prod) > 0 ? (
    var.enable_custom_domain && var.custom_domain_name != "" ? 
    "https://${var.custom_domain_name}" : 
    "https://${azurerm_container_app.frontend_prod[0].latest_revision_fqdn}"
  ) : (length(azurerm_container_app.frontend_dev) > 0 ? 
    "https://${azurerm_container_app.frontend_dev[0].latest_revision_fqdn}" : 
    "No frontend deployed"
  )
  description = "Primary frontend URL (prod if available, otherwise dev) - uses Front Door for custom domains"
}

# Front Door specific outputs
output "frontdoor_endpoint" {
  value = var.enable_custom_domain && var.custom_domain_name != "" ? azurerm_cdn_frontdoor_endpoint.frontend[0].host_name : null
  description = "Azure Front Door endpoint hostname"
}

output "frontdoor_validation_token" {
  value = var.enable_custom_domain && var.custom_domain_name != "" ? azurerm_cdn_frontdoor_custom_domain.frontend[0].validation_token : null
  description = "Domain validation token for DNS verification (required for custom domain setup)"
}

# Container App FQDN for DNS configuration
output "container_app_fqdn" {
  value = length(azurerm_container_app.frontend_prod) > 0 ? azurerm_container_app.frontend_prod[0].ingress[0].fqdn : null
  description = "Current Container App ingress FQDN - use this for CNAME record"
}

# DNS setup instructions
output "dns_setup_instructions" {
  value = var.enable_custom_domain && var.custom_domain_name != "" ? {
    cname_record = {
      name  = replace(var.custom_domain_name, ".ecuad.ca", "")
      type  = "CNAME"
      value = azurerm_cdn_frontdoor_endpoint.frontend[0].host_name
    }
    txt_record = {
      name  = "_dnsauth.${replace(var.custom_domain_name, ".ecuad.ca", "")}"
      type  = "TXT"  
      value = azurerm_cdn_frontdoor_custom_domain.frontend[0].validation_token
    }
    instructions = "Add both DNS records, then run 'terraform apply' again after ~45 minutes for certificate issuance"
  } : null
  description = "DNS records required for custom domain and certificate validation"
}
