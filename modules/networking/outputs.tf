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

output "ssl_certificate_setup" {
  value = {
    status = "SSL Certificate Configuration Deployed"
    custom_domain = var.custom_domain_name
    frontdoor_endpoint = azurerm_cdn_frontdoor_endpoint.main.host_name
    dns_validation_token = azurerm_cdn_frontdoor_custom_domain.main.validation_token
    next_steps = [
      "1. Add CNAME record: reportmate -> ${azurerm_cdn_frontdoor_endpoint.main.host_name}",
      "2. Add TXT record: _dnsauth.reportmate -> ${azurerm_cdn_frontdoor_custom_domain.main.validation_token}",
      "3. Wait 45 minutes for SSL certificate issuance",
      "4. Verify https://${var.custom_domain_name} works without certificate errors"
    ]
  }
}
