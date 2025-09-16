# Container Registry
resource "azurerm_container_registry" "acr" {
  name                = "reportmateacr"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = false  # Use managed identity instead of admin credentials
}

# Log Analytics Workspace for Container Apps
resource "azurerm_log_analytics_workspace" "logs" {
  name                = "reportmate-logs"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

# Container Apps Environment
resource "azurerm_container_app_environment" "env" {
  name                = "reportmate-env"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  
  log_analytics_workspace_id = azurerm_log_analytics_workspace.logs.id

  # Workaround for Azure's API cache returning old resource group casing in workspace ID
  lifecycle {
    ignore_changes = [
      log_analytics_workspace_id  # Ignore changes to workspace ID due to Azure API cache
    ]
  }

  depends_on = [
    azurerm_log_analytics_workspace.logs
  ]
}

# Development Frontend Container App
resource "azurerm_container_app" "frontend_dev" {
  count                        = var.deploy_dev || var.environment == "dev" || var.environment == "both" ? 1 : 0
  name                         = "reportmate-frontend-dev"
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"

  # Assign managed identity to Container App
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.main.id]
  }

  template {
    container {
      name   = "frontend"
      image  = "${azurerm_container_registry.acr.login_server}/reportmate:latest"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "NODE_ENV"
        value = "development"
      }

      env {
        name  = "DATABASE_URL"
        value = "postgresql://${var.db_username}:${var.db_password}@${azurerm_postgresql_flexible_server.pg.fqdn}:5432/${azurerm_postgresql_flexible_server_database.db.name}?sslmode=require"
      }

      env {
        name  = "NEXT_PUBLIC_WPS_URL"
        value = "wss://${azurerm_web_pubsub.wps.hostname}/client/hubs/fleet"
      }

      env {
        name  = "NEXT_PUBLIC_ENABLE_SIGNALR"
        value = "true"
      }

      env {
        name  = "NEXT_PUBLIC_API_BASE_URL"
        value = "https://${azurerm_linux_function_app.func.default_hostname}"
      }

      env {
        name  = "API_BASE_URL"
        value = "https://${azurerm_linux_function_app.func.default_hostname}"
      }

      # Development-specific environment variables
      env {
        name  = "NEXT_PUBLIC_DEBUG"
        value = "true"
      }
    }

    min_replicas = 0  # Allow scaling to zero for dev
    max_replicas = 2  # Lower max replicas for dev
  }

  ingress {
    allow_insecure_connections = false
    external_enabled          = true
    target_port              = 3000

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  # Use managed identity for ACR authentication
  registry {
    server   = azurerm_container_registry.acr.login_server
    identity = azurerm_user_assigned_identity.main.id
  }

  # Note: revision_suffix is managed automatically by Azure Container Apps

  tags = {
    Environment = "development"
  }
}

# Production Frontend Container App
resource "azurerm_container_app" "frontend_prod" {
  count                        = var.deploy_prod || var.environment == "prod" || var.environment == "both" ? 1 : 0
  name                         = "reportmate-frontend-prod"
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"

  # Assign managed identity to Container App
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.main.id]
  }

  template {
    container {
      name   = "frontend"
      image  = "${azurerm_container_registry.acr.login_server}/reportmate:latest"
      cpu    = 0.5   # More CPU for production
      memory = "1Gi" # More memory for production

      env {
        name  = "NODE_ENV"
        value = "production"
      }

      env {
        name  = "DATABASE_URL"
        value = "postgresql://${var.db_username}:${var.db_password}@${azurerm_postgresql_flexible_server.pg.fqdn}:5432/${azurerm_postgresql_flexible_server_database.db.name}?sslmode=require"
      }

      env {
        name  = "NEXT_PUBLIC_WPS_URL"
        value = "wss://${azurerm_web_pubsub.wps.hostname}/client/hubs/fleet"
      }

      env {
        name  = "NEXT_PUBLIC_ENABLE_SIGNALR"
        value = "true"
      }

      env {
        name  = "NEXT_PUBLIC_API_BASE_URL"
        value = "https://${azurerm_linux_function_app.func.default_hostname}"
      }

      env {
        name  = "API_BASE_URL"
        value = "https://${azurerm_linux_function_app.func.default_hostname}"
      }
    }

    min_replicas = 1  # Always keep at least one instance for prod
    max_replicas = 5  # Higher max replicas for prod
  }

  ingress {
    allow_insecure_connections = false
    external_enabled          = true
    target_port              = 3000

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  # Use managed identity for ACR authentication
  registry {
    server   = azurerm_container_registry.acr.login_server
    identity = azurerm_user_assigned_identity.main.id
  }

  # Workaround for Azure's API cache returning old resource group casing
  # This prevents infinite recreation loops due to platform-level caching issues
  lifecycle {
    ignore_changes = [
      container_app_environment_id  # Ignore changes to environment ID due to Azure API cache
    ]
  }

  # Note: revision_suffix is managed automatically by Azure Container Apps

  tags = {
    Environment = "production"
  }
}

# Managed Certificate for Custom Domain
# Note: Azure Container Apps can automatically manage certificates for custom domains
# The certificate will be automatically provisioned once the custom domain is verified
