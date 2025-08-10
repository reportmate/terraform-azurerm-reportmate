# Random suffix for unique resource names
resource "random_id" "container_suffix" {
  byte_length = 4
}

# Container Registry (optional - only if using custom registry)
resource "azurerm_container_registry" "acr" {
  count               = var.use_custom_registry ? 1 : 0
  name                = var.container_registry_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = false # Use managed identity instead

  tags = var.tags
}

# Container Apps Environment
resource "azurerm_container_app_environment" "main" {
  name                       = "reportmate-env"
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

# Development Container App
resource "azurerm_container_app" "container_dev" {
  count                        = var.deploy_dev || var.environment == "dev" || var.environment == "both" ? 1 : 0
  name                         = "reportmate-container-dev"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  # Assign managed identity to Container App (only if using custom registry)
  dynamic "identity" {
    for_each = var.use_custom_registry ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [var.managed_identity_id]
    }
  }

  lifecycle {
    ignore_changes = [
      container_app_environment_id  # Ignore case sensitivity changes in Azure resource IDs
    ]
  }

  template {
    container {
      name   = "container"
      image  = var.use_custom_registry ? "${azurerm_container_registry.acr[0].login_server}/reportmate:latest" : var.container_image
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "NODE_ENV"
        value = "development"
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
        value = "https://${var.function_app_hostname}"
      }

      env {
        name  = "NEXT_PUBLIC_DEBUG"
        value = "true"
      }

      env {
        name  = "PORT"
        value = "3000"
      }

      # Add startup and liveness probes for dev too
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
    }

    min_replicas = 0 # Allow scaling to zero for dev
    max_replicas = 2 # Lower max replicas for dev
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

  # Use managed identity for ACR authentication (only if using custom registry)
  dynamic "registry" {
    for_each = var.use_custom_registry ? [1] : []
    content {
      server   = azurerm_container_registry.acr[0].login_server
      identity = var.managed_identity_id
    }
  }

  tags = merge(var.tags, {
    Environment = "development"
  })
}

# Production Container App
resource "azurerm_container_app" "container_prod" {
  count                        = var.deploy_prod || var.environment == "prod" || var.environment == "both" ? 1 : 0
  name                         = "reportmate-container-prod"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  # Assign managed identity to Container App (only if using custom registry)
  dynamic "identity" {
    for_each = var.use_custom_registry ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [var.managed_identity_id]
    }
  }

  lifecycle {
    ignore_changes = [
      container_app_environment_id  # Ignore case sensitivity changes in Azure resource IDs
    ]
  }

  template {
    container {
      name   = "container"
      image  = var.use_custom_registry ? "${azurerm_container_registry.acr[0].login_server}/reportmate:latest" : var.container_image
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
        value = "https://${var.function_app_hostname}"
      }

      env {
        name  = "PORT"
        value = "3000"
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

  # Use managed identity for ACR authentication (only if using custom registry)
  dynamic "registry" {
    for_each = var.use_custom_registry ? [1] : []
    content {
      server   = azurerm_container_registry.acr[0].login_server
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
