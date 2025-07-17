# ReportMate Azure Infrastructure Terraform Module
# This module deploys a complete ReportMate infrastructure on Azure

terraform {
  required_version = ">= 1.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }
}

# Resource Group
resource "azurerm_resource_group" "reportmate" {
  name     = var.resource_group_name
  location = var.location

  tags = var.tags
}

# Random suffix for unique resource names
resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

# Database Module
module "database" {
  source = "./modules/database"

  resource_group_name = azurerm_resource_group.reportmate.name
  location           = azurerm_resource_group.reportmate.location
  database_name      = var.database_name
  admin_username     = var.database_admin_username
  admin_password     = var.database_admin_password
  suffix            = random_string.suffix.result
  tags              = var.tags
}

# Storage Module
module "storage" {
  source = "./modules/storage"

  resource_group_name = azurerm_resource_group.reportmate.name
  location           = azurerm_resource_group.reportmate.location
  suffix            = random_string.suffix.result
  tags              = var.tags
}

# Monitoring Module
module "monitoring" {
  source = "./modules/monitoring"

  resource_group_name = azurerm_resource_group.reportmate.name
  location           = azurerm_resource_group.reportmate.location
  suffix            = random_string.suffix.result
  tags              = var.tags
}

# Functions Module
module "functions" {
  source = "./modules/functions"

  resource_group_name          = azurerm_resource_group.reportmate.name
  location                    = azurerm_resource_group.reportmate.location
  database_connection_string  = module.database.connection_string
  storage_account_name        = module.storage.storage_account_name
  storage_connection_string   = module.storage.storage_connection_string
  application_insights_key    = module.monitoring.application_insights_instrumentation_key
  suffix                     = random_string.suffix.result
  tags                       = var.tags
}

# Networking Module (Front Door)
module "networking" {
  source = "./modules/networking"

  resource_group_name = azurerm_resource_group.reportmate.name
  location           = azurerm_resource_group.reportmate.location
  function_app_hostname = module.functions.function_app_hostname
  custom_domain      = var.custom_domain
  suffix            = random_string.suffix.result
  tags              = var.tags
}
