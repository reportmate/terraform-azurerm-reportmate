# Random suffix for unique resource names
resource "random_id" "container_suffix" {
  byte_length = 4
}

# Extract image name and tag from container_image variable
locals {
  # Extract image name and tag from the full image path
  # e.g., "reportmateacr.azurecr.io/reportmate-web:latest" -> "reportmate-web:latest"
  image_name_tag = var.use_custom_registry ? (
    length(split("/", var.container_image)) > 1 ? 
    split("/", var.container_image)[length(split("/", var.container_image)) - 1] : 
    var.container_image
  ) : var.container_image

  # Compute site URL values - use custom domain if enabled, otherwise derive from container environment
  # Note: We can't use the container app's own FQDN here (self-reference), so we use the environment pattern
  
  # Site URL: custom domain takes priority, then compute from environment default domain
  site_hostname = var.enable_custom_domain && var.custom_domain_name != "" ? var.custom_domain_name : (
    var.default_site_url != "" ? var.default_site_url : "${var.frontend_container_name}.${azurerm_container_app_environment.main.default_domain}"
  )
  site_url = "https://${local.site_hostname}"
}

# Container Registry (optional - only if using custom registry)
resource "azurerm_container_registry" "acr" {
  count               = var.use_custom_registry ? 1 : 0
  name                = var.container_registry_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = true  # Required for maintenance job authentication

  tags = var.tags
}

# Container Apps Environment
resource "azurerm_container_app_environment" "main" {
  name                       = var.container_environment_name
  resource_group_name        = var.resource_group_name
  location                   = var.location
  log_analytics_workspace_id = var.log_analytics_workspace_id

  lifecycle {
    ignore_changes = [
      log_analytics_workspace_id  # Ignore case sensitivity changes in Azure resource IDs
    ]
  }

  tags = var.tags
}

# =================================================================
# FRONTEND WEB APP CONTAINER - Next.js Application (Production)
# NOTE: The full production container is defined below as frontend_prod_main
# =================================================================

# =================================================================
# FRONTEND WEB APP CONTAINER - Next.js Application (Production)
# Complete production setup with authentication and Key Vault integration
# =================================================================

# Production Frontend Container App for ReportMate Next.js Web Dashboard
resource "azurerm_container_app" "frontend_prod_main" {
  count                        = var.deploy_prod || var.environment == "prod" || var.environment == "both" ? 1 : 0
  name                         = var.frontend_container_name
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  # Assign managed identity to Container App for Key Vault access and ACR
  identity {
    type         = "UserAssigned"
    identity_ids = [var.managed_identity_id]
  }

  lifecycle {
    ignore_changes = [
      container_app_environment_id  # Ignore case sensitivity changes in Azure resource IDs
    ]
  }

  template {
    container {
      name   = "container"
      image  = var.use_custom_registry ? "${azurerm_container_registry.acr[0].login_server}/${var.frontend_image_name}:${var.frontend_image_tag}" : "${var.existing_registry_server}/${var.frontend_image_name}:${var.frontend_image_tag}"
      cpu    = 0.5   # More CPU for production
      memory = "1Gi" # More memory for production

      env {
        name  = "NODE_ENV"
        value = "production"
      }

      env {
        name  = "DATABASE_URL"
        value = var.database_url
      }

      env {
        name  = "NEXT_PUBLIC_WPS_URL"
        value = "wss://${var.web_pubsub_hostname}/client/hubs/fleet"
      }

      env {
        name  = "NEXT_PUBLIC_ENABLE_SIGNALR"
        value = "true"
      }

      env {
        name  = "API_BASE_URL"
        value = "https://${azurerm_container_app.api_functions.ingress[0].fqdn}"
      }

      env {
        name  = "NEXT_PUBLIC_API_BASE_URL"
        value = "https://${azurerm_container_app.api_functions.ingress[0].fqdn}"
      }

      env {
        name  = "PORT"
        value = "3000"
      }

      env {
        name  = "HOSTNAME"
        value = "0.0.0.0"
      }

      env {
        name  = "HOST"
        value = local.site_hostname
      }

      env {
        name  = "NEXT_PUBLIC_SITE_URL"
        value = local.site_url
      }

      env {
        name  = "NEXT_PUBLIC_URL"
        value = local.site_url
      }

      # Authentication secrets from Key Vault (if available)
      dynamic "env" {
        for_each = var.key_vault_uri != null && var.auth_secrets != null ? [1] : []
        content {
          name        = "NEXTAUTH_SECRET"
          secret_name = var.auth_secrets.nextauth_secret_name
        }
      }

      dynamic "env" {
        for_each = var.key_vault_uri != null && var.auth_secrets != null ? [1] : []
        content {
          name        = "AZURE_AD_CLIENT_SECRET"
          secret_name = var.auth_secrets.client_secret_name
        }
      }

      # Authentication non-sensitive environment variables
      env {
        name  = "AZURE_AD_CLIENT_ID"
        value = var.auth_client_id
      }

      env {
        name  = "AZURE_AD_TENANT_ID"
        value = var.auth_tenant_id
      }

      env {
        name  = "AUTH_PROVIDERS"
        value = "azure-ad"
      }

      env {
        name  = "DEFAULT_AUTH_PROVIDER"
        value = "azure-ad"
      }

      env {
        name  = "ALLOWED_DOMAINS"
        value = var.allowed_domains
      }

      env {
        name  = "REQUIRE_EMAIL_VERIFICATION"
        value = "false"
      }

      env {
        name  = "NEXTAUTH_URL"
        value = local.site_url
      }

      env {
        name  = "NEXTAUTH_URL_INTERNAL"
        value = local.site_url
      }

      env {
        name  = "AUTH_TRUST_HOST"
        value = "true"
      }

      # Authentication secrets from Key Vault (if available)
      dynamic "env" {
        for_each = var.key_vault_uri != null && var.auth_secrets != null ? [1] : []
        content {
          name        = "NEXTAUTH_SECRET"
          secret_name = var.auth_secrets.nextauth_secret_name
        }
      }

      env {
        name  = "VERCEL_URL"
        value = local.site_hostname
      }

      env {
        name  = "NEXT_PUBLIC_VERCEL_URL"
        value = local.site_hostname
      }

      env {
        name  = "REPORTMATE_PASSPHRASE"
        value = var.client_passphrases
      }

      env {
        name  = "NEXT_PUBLIC_AUTO_SSO"
        value = "false"
      }

      # Version tracking environment variables
      env {
        name  = "CONTAINER_IMAGE_TAG"
        value = var.frontend_image_tag
      }

      env {
        name  = "BUILD_TIME"
        value = formatdate("YYYY-MM-DD'T'hh:mm:ss'Z'", timestamp())
      }

      env {
        name  = "BUILD_ID"
        value = substr(var.frontend_image_tag, length(var.frontend_image_tag) - 7, 7)
      }

      # NEXT_PUBLIC version tracking (exposed to client)
      env {
        name  = "NEXT_PUBLIC_VERSION"
        value = var.frontend_image_tag
      }

      env {
        name  = "NEXT_PUBLIC_BUILD_ID"
        value = substr(var.frontend_image_tag, length(var.frontend_image_tag) - 7, 7)
      }

      env {
        name  = "NEXT_PUBLIC_BUILD_TIME"
        value = formatdate("YYYY-MM-DD'T'hh:mm:ss'Z'", timestamp())
      }

      # Azure Managed Identity Client ID (for Key Vault access)
      env {
        name  = "AZURE_CLIENT_ID"
        value = var.managed_identity_client_id
      }

      # Add startup and liveness probes
      startup_probe {
        transport = "HTTP"
        port      = 3000
        path      = "/"
        
        failure_count_threshold = 3
        initial_delay           = 10
        interval_seconds        = 10
        timeout                 = 5
      }

      liveness_probe {
        transport = "HTTP"
        port      = 3000
        path      = "/"
        
        failure_count_threshold = 3
        initial_delay           = 30
        interval_seconds        = 30
        timeout                 = 5
      }

      readiness_probe {
        transport = "HTTP"
        port      = 3000
        path      = "/"
        
        failure_count_threshold = 3
        interval_seconds        = 10
        timeout                 = 5
        success_count_threshold = 1
      }
    }

    min_replicas = 1 # Always keep at least one instance for prod
    max_replicas = 5 # Higher max replicas for prod
  }

  ingress {
    allow_insecure_connections = false
    external_enabled           = true
    target_port                = 3000

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  # Key Vault secrets configuration
  dynamic "secret" {
    for_each = var.key_vault_uri != null && var.auth_secrets != null ? [
      {
        name     = var.auth_secrets.nextauth_secret_name
        identity = var.managed_identity_id
        key_vault_secret_id = "${var.key_vault_uri}secrets/${var.auth_secrets.nextauth_secret_name}"
      },
      {
        name     = var.auth_secrets.client_secret_name
        identity = var.managed_identity_id
        key_vault_secret_id = "${var.key_vault_uri}secrets/${var.auth_secrets.client_secret_name}"
      }
    ] : []
    
    content {
      name                = secret.value.name
      identity            = secret.value.identity
      key_vault_secret_id = secret.value.key_vault_secret_id
    }
  }

  # Use managed identity for ACR authentication
  # When use_custom_registry = true, use the created ACR
  # When use_custom_registry = false, use the existing registry server
  dynamic "registry" {
    for_each = var.use_custom_registry ? [1] : []
    content {
      server   = azurerm_container_registry.acr[0].login_server
      identity = var.managed_identity_id
    }
  }

  dynamic "registry" {
    for_each = var.use_custom_registry ? [] : [1]
    content {
      server   = var.existing_registry_server
      identity = var.managed_identity_id
    }
  }

  tags = merge(var.tags, {
    Environment = "production"
  })
}

# ACR Role Assignments (only if using custom registry)
resource "azurerm_role_assignment" "container_acr_pull" {
  count                            = var.use_custom_registry ? 1 : 0
  scope                            = azurerm_container_registry.acr[0].id
  role_definition_name             = "AcrPull"
  principal_id                     = var.managed_identity_principal_id

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [azurerm_container_registry.acr]
}

resource "azurerm_role_assignment" "container_acr_push" {
  count                            = var.use_custom_registry ? 1 : 0
  scope                            = azurerm_container_registry.acr[0].id
  role_definition_name             = "AcrPush"
  principal_id                     = var.managed_identity_principal_id

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [azurerm_container_registry.acr]
}

# =================================================================
# API FUNCTIONS CONTAINER - FastAPI Application
# =================================================================
# CRITICAL CONFIGURATION WARNING
# external_enabled MUST be TRUE for Windows/Mac clients to check in!
# If set to false:
#   - Windows/Mac devices get 404 errors and cannot check in
#   - Frontend continues working (internal network), masking the issue
#   - Devices stop reporting for days/weeks before anyone notices
# See: infrastructure/modules/containers/TERRAFORM_DRIFT_EXTERNAL_ACCESS.md
# =================================================================

# API Functions Container App for ReportMate FastAPI Backend
resource "azurerm_container_app" "api_functions" {
  name                         = var.api_container_name
  resource_group_name          = var.resource_group_name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"

  # Assign managed identity to Container App
  identity {
    type         = "UserAssigned"
    identity_ids = [var.managed_identity_id]
  }

  # External ingress for API endpoints
  # external_enabled MUST be true - do not change!
  ingress {
    external_enabled = true  # MUST be true for Windows/Mac client check-ins
    target_port      = 8000
    transport        = "auto"
    
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }

    # CORS configuration for browser-side API calls (SignalR negotiate, etc.)
    # Required for frontend to make direct browser requests to API
    # Note: Frontend URL constructed from environment default domain to avoid circular dependency
    cors {
      allow_credentials_enabled = true
      allowed_headers           = ["*"]
      allowed_methods           = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
      allowed_origins = compact([
        # Frontend container app URL (uses environment default domain pattern)
        "https://${var.frontend_container_name}.${azurerm_container_app_environment.main.default_domain}",
        # Custom domain (if enabled)
        var.enable_custom_domain && var.custom_domain_name != "" ? "https://${var.custom_domain_name}" : null,
      ])
      exposed_headers    = []
      max_age_in_seconds = 3600
    }
  }

  # Use managed identity for ACR authentication
  registry {
    server   = var.use_custom_registry ? azurerm_container_registry.acr[0].login_server : var.existing_registry_server
    identity = var.managed_identity_id
  }

  # Database connection as secure secret
  secret {
    name  = "db-url"
    value = "postgresql://${var.database_username}:${urlencode(var.database_password)}@${var.database_host}:5432/${var.database_name}?sslmode=require"
  }

  template {
    container {
      name   = "api"
      image  = var.use_custom_registry ? "${azurerm_container_registry.acr[0].login_server}/${var.api_image_name}:${var.api_image_tag}" : "${var.existing_registry_server}/${var.api_image_name}:${var.api_image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      # Database connection from secure secret
      env {
        name        = "DATABASE_URL"
        secret_name = "db-url"
      }

      # Application Insights connection
      env {
        name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        value = var.app_insights_connection_string
      }

      # Web PubSub connection for SignalR
      env {
        name  = "EVENTS_CONNECTION"
        value = var.web_pubsub_connection
      }

      # Client passphrase for Windows client authentication
      env {
        name  = "REPORTMATE_PASSPHRASE"
        value = var.client_passphrases
      }

      # Environment indicator
      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      # Disable authentication for API (passphrase-only auth for Windows clients)
      env {
        name  = "DISABLE_AUTH"
        value = "true"
      }
    }

    # Scaling configuration (always keep at least 1 instance)
    min_replicas = 1
    max_replicas = 5
  }

  # Workaround for Azure's API cache returning old resource group casing
  lifecycle {
    ignore_changes = [
      container_app_environment_id  # Ignore changes to environment ID due to Azure API cache
    ]
  }

  tags = merge(var.tags, {
    Purpose = "API"
  })
}
