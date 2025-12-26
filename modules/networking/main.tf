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
    interval_in_seconds = 60
    path                = "/"
    protocol            = "Https"
    request_type        = "GET"
  }
}

# NOTE: Removed dedicated API Origin Group and Route
# All traffic now goes through the frontend container, which proxies to the API
# with proper authentication headers. This ensures:
# 1. Frontend adds X-Internal-Secret header for container-to-container auth
# 2. No unauthenticated direct access to API endpoints
# 3. Single point of entry for all requests

# Front Door Origin (points to frontend container - all traffic goes through here)
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
}

# Front Door Rule Set for Header Forwarding
resource "azurerm_cdn_frontdoor_rule_set" "main" {
  name                     = "HeaderForwardingRules"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id
}

# Note: Header forwarding rule removed due to Azure Front Door restrictions
# on modifying X-Forwarded-Host and X-Forwarded-Proto headers

# Front Door Endpoint
resource "azurerm_cdn_frontdoor_endpoint" "main" {
  name                     = "reportmate-endpoint"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id
  enabled                  = true

  tags = var.tags
}

# Front Door Route (single route handles all traffic via frontend)
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
  cdn_frontdoor_rule_set_ids      = [azurerm_cdn_frontdoor_rule_set.main.id]
  link_to_default_domain          = true
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
