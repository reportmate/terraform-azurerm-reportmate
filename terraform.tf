terraform {
  required_version = ">= 1.12.2"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.33.0"
    }
    postgresql = {
      source  = "cyrilgdn/postgresql"
      version = "~> 1.22.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "Terraform"
    storage_account_name = "ecuadgitopsterraform"
    container_name       = "terraform-state"
    key                  = "reportmate.tfstate"
  }
}

provider "azurerm" {
  features {}
  subscription_id = "59d35012-b593-4b2f-bd50-28e666ed12f7"
  
  # Disable automatic resource provider registration to avoid conflicts
  resource_provider_registrations = "none"
}

# =================================================================
# RESOURCE PROVIDER REGISTRATIONS
# =================================================================

# Note: Microsoft.ContainerService and Microsoft.OperationalInsights are automatically
# registered by Terraform. Microsoft.App needs to be imported if it already exists.

# Azure Flexible Server wants user@server for non-AAD logins
locals {
  pg_username = "${var.db_username}@${azurerm_postgresql_flexible_server.pg.name}"
}

provider "postgresql" {
  host            = azurerm_postgresql_flexible_server.pg.fqdn
  port            = 5432
  database        = azurerm_postgresql_flexible_server_database.db.name
  username        = local.pg_username
  password        = var.db_password
  sslmode         = "require"
}
