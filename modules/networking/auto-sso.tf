# Auto-SSO Rule Set for Front Door
resource "azurerm_cdn_frontdoor_rule_set" "auto_sso" {
  name                     = "AutoSSORedirect"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id
}

# Rule to redirect all non-auth traffic to SSO login
resource "azurerm_cdn_frontdoor_rule" "auto_sso_redirect" {
  depends_on = [azurerm_cdn_frontdoor_origin_group.main, azurerm_cdn_frontdoor_origin.main]

  name                      = "AutoSSORedirect"
  cdn_frontdoor_rule_set_id = azurerm_cdn_frontdoor_rule_set.auto_sso.id
  order                     = 1
  behavior_on_match         = "Continue"

  # Conditions: Match requests that are NOT auth-related and NOT static assets and NOT already authenticated
  conditions {
    request_uri_condition {
      operator         = "BeginsWith"
      negate_condition = true
      match_values     = ["/api/auth", "/auth", "/_next"]
      transforms       = ["Lowercase"]
    }

    request_uri_condition {
      operator         = "Contains"
      negate_condition = true
      match_values     = [".ico", ".png", ".jpg", ".css", ".js", ".json"]
      transforms       = ["Lowercase"]
    }

    cookies_condition {
      cookie_name      = "next-auth.session-token"
      operator         = "Any"
      negate_condition = true
    }
  }

  # Actions: Redirect to SSO login
  actions {
    url_redirect_action {
      redirect_type        = "Found"
      redirect_protocol    = "MatchRequest"
      destination_hostname = var.custom_domain_name
      destination_path     = "/api/auth/signin"
      query_string         = "?callbackUrl={request_uri}"
      destination_fragment = ""
    }
  }
}

# Optional: Rule to handle post-auth redirects
resource "azurerm_cdn_frontdoor_rule" "auth_callback_redirect" {
  depends_on = [azurerm_cdn_frontdoor_origin_group.main, azurerm_cdn_frontdoor_origin.main]

  name                      = "AuthCallbackRedirect"
  cdn_frontdoor_rule_set_id = azurerm_cdn_frontdoor_rule_set.auto_sso.id
  order                     = 2
  behavior_on_match         = "Continue"

  # Conditions: Match successful auth callbacks
  conditions {
    request_uri_condition {
      operator     = "BeginsWith"
      match_values = ["/api/auth/callback"]
      transforms   = ["Lowercase"]
    }
  }

  # Actions: Allow through normally (no redirect)
  actions {
    route_configuration_override_action {
      cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.main.id
      forwarding_protocol          = "HttpsOnly"
      query_string_caching_behavior = "UseQueryString"
      compression_enabled          = true
      cache_behavior               = "HonorOrigin"
    }
  }
}

# Add the rule set to the main route
resource "azurerm_cdn_frontdoor_route" "main_with_auto_sso" {
  name                          = "reportmate-route-with-sso"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.main.id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.main.id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.main.id]
  enabled                       = true

  forwarding_protocol    = "HttpsOnly"
  https_redirect_enabled = true
  patterns_to_match      = ["/*"]
  supported_protocols    = ["Http", "Https"]

  cdn_frontdoor_custom_domain_ids = [azurerm_cdn_frontdoor_custom_domain.main.id]
  cdn_frontdoor_rule_set_ids      = [azurerm_cdn_frontdoor_rule_set.auto_sso.id]
  link_to_default_domain          = false

  # Override the main route
  depends_on = [azurerm_cdn_frontdoor_route.main]
  
  lifecycle {
    replace_triggered_by = [azurerm_cdn_frontdoor_route.main]
  }
}
