output "front_door_endpoint" {
  description = "Front Door endpoint URL"
  value       = "https://${azurerm_cdn_frontdoor_endpoint.main.host_name}"
}

output "front_door_profile_name" {
  description = "Name of the Front Door profile"
  value       = azurerm_cdn_frontdoor_profile.main.name
}

output "custom_domain_validation_token" {
  description = "Custom domain validation token"
  value       = azurerm_cdn_frontdoor_custom_domain.main.validation_token
}
