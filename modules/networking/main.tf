# Front Door Profile
resource "azurerm_cdn_frontdoor_profile" "reportmate" {
  name                = "reportmate-fd-${var.suffix}"
  resource_group_name = var.resource_group_name
  sku_name           = "Standard_AzureFrontDoor"

  tags = var.tags
}

# Front Door Origin Group
resource "azurerm_cdn_frontdoor_origin_group" "reportmate" {
  name                 = "reportmate-origin-group"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.reportmate.id
  session_affinity_enabled = false

  load_balancing {
    additional_latency_in_milliseconds = 50
    sample_size                       = 4
    successful_samples_required       = 3
  }

  health_probe {
    interval_in_seconds = 100
    path               = "/api/health"
    protocol           = "Https"
    request_type       = "HEAD"
  }
}

# Front Door Origin
resource "azurerm_cdn_frontdoor_origin" "reportmate" {
  name                          = "reportmate-origin"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.reportmate.id
  enabled                      = true

  certificate_name_check_enabled = true
  host_name                     = var.function_app_hostname
  http_port                     = 80
  https_port                    = 443
  origin_host_header            = var.function_app_hostname
  priority                      = 1
  weight                        = 1000
}

# Front Door Endpoint
resource "azurerm_cdn_frontdoor_endpoint" "reportmate" {
  name                 = "reportmate-endpoint-${var.suffix}"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.reportmate.id
  enabled             = true

  tags = var.tags
}

# Front Door Route
resource "azurerm_cdn_frontdoor_route" "reportmate" {
  name                          = "reportmate-route"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.reportmate.id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.reportmate.id
  cdn_frontdoor_origin_ids     = [azurerm_cdn_frontdoor_origin.reportmate.id]
  enabled                      = true

  forwarding_protocol    = "HttpsOnly"
  https_redirect_enabled = true
  patterns_to_match     = ["/*"]
  supported_protocols   = ["Http", "Https"]

  cdn_frontdoor_custom_domain_ids = var.custom_domain != null ? [azurerm_cdn_frontdoor_custom_domain.reportmate[0].id] : []
  link_to_default_domain         = var.custom_domain == null ? true : false
}

# Custom Domain (optional)
resource "azurerm_cdn_frontdoor_custom_domain" "reportmate" {
  count = var.custom_domain != null ? 1 : 0

  name                     = "reportmate-custom-domain"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.reportmate.id
  dns_zone_id             = null
  host_name               = var.custom_domain

  tls {
    certificate_type    = "ManagedCertificate"
    minimum_tls_version = "TLS12"
  }
}
