# Random suffix for unique resource names
resource "random_id" "container_suffix" {
  byte_length = 4
}

# Container Registry (optional - only if using custom registry)
resource "azurerm_container_registry" "acr" {
  count               = var.use_custom_registry ? 1 : 0
  name                = "${replace(var.container_registry_name, "-", "")}${random_id.container_suffix.hex}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = false # Use managed identity instead

  tags = var.tags
}

# Log Analytics Workspace for Container Apps
resource "azurerm_log_analytics_workspace" "containers" {
  name                = "reportmate-container-logs-${random_id.container_suffix.hex}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = var.tags
}

# Container Apps Environment
resource "azurerm_container_app_environment" "main" {
  name                       = "reportmate-env-${random_id.container_suffix.hex}"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.containers.id

  tags = var.tags
}

# Development Frontend Container App
resource "azurerm_container_app" "frontend_dev" {
  count                        = var.deploy_dev || var.environment == "dev" || var.environment == "both" ? 1 : 0
  name                         = "reportmate-frontend-dev-${random_id.container_suffix.hex}"
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

  template {
    container {
      name   = "frontend"
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

# Production Frontend Container App
resource "azurerm_container_app" "frontend_prod" {
  count                        = var.deploy_prod || var.environment == "prod" || var.environment == "both" ? 1 : 0
  name                         = "reportmate-frontend-prod-${random_id.container_suffix.hex}"
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

  template {
    container {
      name   = "frontend"
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
