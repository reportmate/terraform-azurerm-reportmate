# Random suffix for unique resource names
# Remove random ID since we're using predictable naming
# resource "random_id" "networking_suffix" {
#   byte_length = 4
# }

# Front Door Profile
resource "azurerm_cdn_frontdoor_profile" "main" {
  name                = var.frontdoor_name
  resource_group_name = var.resource_group_name
  sku_name            = "Standard_AzureFrontDoor"

  tags = var.tags
}

# Front Door Origin Group
resource "azurerm_cdn_frontdoor_origin_group" "main" {
  name                     = "reportmate-origin-group"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id
  session_affinity_enabled = false

  load_balancing {
    additional_latency_in_milliseconds = 50
    sample_size                        = 4
    successful_samples_required        = 3
  }

  health_probe {
    interval_in_seconds = 30
    path                = "/"
    protocol            = "Https"
    request_type        = "GET"
  }
}

# Front Door Origin Group for API
resource "azurerm_cdn_frontdoor_origin_group" "api" {
  name                     = "reportmate-api-origin-group"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id
  session_affinity_enabled = false

  load_balancing {
    additional_latency_in_milliseconds = 50
    sample_size                        = 4
    successful_samples_required        = 3
  }

  health_probe {
    interval_in_seconds = 30
    path                = "/api/health"
    protocol            = "Https"
    request_type        = "GET"
  }
}

# Front Door Origin
resource "azurerm_cdn_frontdoor_origin" "main" {
  name                          = "reportmate-origin"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.main.id
  enabled                       = true

  certificate_name_check_enabled = false  # Disable for container apps
  host_name                      = var.frontend_fqdn
  http_port                      = 80
  https_port                     = 443
  origin_host_header             = var.frontend_fqdn
  priority                       = 1
  weight                         = 1000

  lifecycle {
    ignore_changes = [
      host_name,
      origin_host_header
    ]
  }
}

# Front Door API Origin
resource "azurerm_cdn_frontdoor_origin" "api" {
  name                          = "reportmate-api-origin"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.api.id
  enabled                       = true

  certificate_name_check_enabled = true
  host_name                      = var.function_app_hostname
  http_port                      = 80
  https_port                     = 443
  origin_host_header             = var.function_app_hostname
  priority                       = 1
  weight                         = 1000

  lifecycle {
    ignore_changes = [
      host_name,
      origin_host_header
    ]
  }
}

# Front Door Endpoint
resource "azurerm_cdn_frontdoor_endpoint" "main" {
  name                     = "reportmate-endpoint"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id
  enabled                  = true

  tags = var.tags
}

# Front Door Route
resource "azurerm_cdn_frontdoor_route" "main" {
  name                          = "reportmate-route"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.main.id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.main.id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.main.id]
  enabled                       = true

  forwarding_protocol    = "HttpsOnly"
  https_redirect_enabled = true
  patterns_to_match      = ["/*"]
  supported_protocols    = ["Http", "Https"]

  cdn_frontdoor_custom_domain_ids = [azurerm_cdn_frontdoor_custom_domain.main.id]
  link_to_default_domain          = false
}

# Front Door API Route
resource "azurerm_cdn_frontdoor_route" "api" {
  name                          = "reportmate-api-route"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.main.id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.api.id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.api.id]
  enabled                       = true

  forwarding_protocol    = "HttpsOnly"
  https_redirect_enabled = true
  patterns_to_match      = ["/api/*"]
  supported_protocols    = ["Http", "Https"]

  cdn_frontdoor_custom_domain_ids = [azurerm_cdn_frontdoor_custom_domain.main.id]
  link_to_default_domain          = false
}

# Custom Domain
resource "azurerm_cdn_frontdoor_custom_domain" "main" {
  name                     = "reportmate-custom-domain"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id
  dns_zone_id              = null
  host_name                = var.custom_domain_name

  tls {
    certificate_type    = "ManagedCertificate"
  }
}
