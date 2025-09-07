# Azure Front Door for stable custom domain
# This provides a stable endpoint that routes traffic to the Container App
# Eliminates the need to update CNAME records when Container Apps are redeployed

resource "azurerm_cdn_frontdoor_profile" "main" {
  count               = var.enable_custom_domain && var.custom_domain_name != "" ? 1 : 0
  name                = "reportmate-frontdoor"
  resource_group_name = azurerm_resource_group.rg.name
  sku_name            = "Standard_AzureFrontDoor"

  tags = {
    Environment = var.environment
    LastDeployment = formatdate("YYYY-MM-DD-hhmm", timestamp())
  }
}

# Frontend origin group for Container Apps
resource "azurerm_cdn_frontdoor_origin_group" "frontend" {
  count                    = var.enable_custom_domain && var.custom_domain_name != "" ? 1 : 0
  name                     = "frontend-origin-group"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main[0].id

  health_probe {
    path                = "/"
    protocol            = "Https"
    request_type        = "HEAD"
    interval_in_seconds = 60
  }

  load_balancing {
    sample_size                 = 4
    successful_samples_required = 3
  }
}

# API origin group for Azure Functions
resource "azurerm_cdn_frontdoor_origin_group" "api" {
  count                    = var.enable_custom_domain && var.custom_domain_name != "" ? 1 : 0
  name                     = "api-origin-group"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main[0].id

  health_probe {
    path                = "/api/health"
    protocol            = "Https"
    request_type        = "GET"
    interval_in_seconds = 60
  }

  load_balancing {
    sample_size                 = 4
    successful_samples_required = 3
  }
}

# Frontend origin pointing to Container App
resource "azurerm_cdn_frontdoor_origin" "frontend" {
  count                           = var.enable_custom_domain && var.custom_domain_name != "" ? 1 : 0
  cdn_frontdoor_origin_group_id   = azurerm_cdn_frontdoor_origin_group.frontend[0].id
  name                            = "frontend-origin"
  host_name                       = azurerm_container_app.frontend_prod[0].ingress[0].fqdn
  origin_host_header              = azurerm_container_app.frontend_prod[0].ingress[0].fqdn
  https_port                      = 443
  certificate_name_check_enabled  = true
}

# API origin pointing to Azure Functions
resource "azurerm_cdn_frontdoor_origin" "api" {
  count                           = var.enable_custom_domain && var.custom_domain_name != "" ? 1 : 0
  cdn_frontdoor_origin_group_id   = azurerm_cdn_frontdoor_origin_group.api[0].id
  name                            = "api-origin"
  host_name                       = azurerm_linux_function_app.func.default_hostname
  origin_host_header              = azurerm_linux_function_app.func.default_hostname
  https_port                      = 443
  certificate_name_check_enabled  = true
}

# Custom domain endpoint
resource "azurerm_cdn_frontdoor_endpoint" "frontend" {
  count                    = var.enable_custom_domain && var.custom_domain_name != "" ? 1 : 0
  name                     = "reportmate-frontend"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main[0].id
  
  tags = {
    Environment = var.environment
    DeploymentTrigger = formatdate("YYYY-MM-DD-hhmm", timestamp())
  }
}

# Custom domain
resource "azurerm_cdn_frontdoor_custom_domain" "frontend" {
  count                    = var.enable_custom_domain && var.custom_domain_name != "" ? 1 : 0
  name                     = "reportmate-custom-domain"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main[0].id
  host_name                = var.custom_domain_name

  tls {
    certificate_type = "ManagedCertificate"
  }
}

# API route for /api/* traffic
resource "azurerm_cdn_frontdoor_route" "api" {
  count                            = var.enable_custom_domain && var.custom_domain_name != "" ? 1 : 0
  name                             = "api-route"
  cdn_frontdoor_endpoint_id        = azurerm_cdn_frontdoor_endpoint.frontend[0].id
  cdn_frontdoor_origin_group_id    = azurerm_cdn_frontdoor_origin_group.api[0].id
  cdn_frontdoor_origin_ids         = [azurerm_cdn_frontdoor_origin.api[0].id]
  cdn_frontdoor_custom_domain_ids  = [azurerm_cdn_frontdoor_custom_domain.frontend[0].id]
  patterns_to_match                = ["/api/*"]
  supported_protocols              = ["Http", "Https"]
  forwarding_protocol              = "HttpsOnly"
  https_redirect_enabled           = true
  link_to_default_domain           = true
  enabled                          = true
}

# Default route for all other traffic (frontend)
resource "azurerm_cdn_frontdoor_route" "frontend_default" {
  count                            = var.enable_custom_domain && var.custom_domain_name != "" ? 1 : 0
  name                             = "frontend-default-route"
  cdn_frontdoor_endpoint_id        = azurerm_cdn_frontdoor_endpoint.frontend[0].id
  cdn_frontdoor_origin_group_id    = azurerm_cdn_frontdoor_origin_group.frontend[0].id
  cdn_frontdoor_origin_ids         = [azurerm_cdn_frontdoor_origin.frontend[0].id]
  cdn_frontdoor_custom_domain_ids  = [azurerm_cdn_frontdoor_custom_domain.frontend[0].id]
  patterns_to_match                = ["/*"]
  supported_protocols              = ["Http", "Https"]
  forwarding_protocol              = "HttpsOnly"
  https_redirect_enabled           = true
  link_to_default_domain           = true
  enabled                          = true
}


