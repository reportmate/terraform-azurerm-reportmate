output "front_door_endpoint" {
  description = "Front Door endpoint URL"
  value       = "https://${azurerm_cdn_frontdoor_endpoint.reportmate.host_name}"
}

output "front_door_profile_name" {
  description = "Name of the Front Door profile"
  value       = azurerm_cdn_frontdoor_profile.reportmate.name
}

output "custom_domain_validation_token" {
  description = "Custom domain validation token (if custom domain is used)"
  value       = var.custom_domain != null ? azurerm_cdn_frontdoor_custom_domain.reportmate[0].validation_token : null
}
