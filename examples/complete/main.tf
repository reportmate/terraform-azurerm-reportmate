# Example usage of the ReportMate Terraform module

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

module "reportmate" {
  source = "../"  # In real usage: source = "your-org/reportmate/azurerm"
  
  resource_group_name      = "reportmate-example"
  location                = "East US"
  database_admin_username  = "reportmate_admin"
  database_admin_password  = var.database_password
  
  custom_domain = "api.example.com"  # optional
  
  tags = {
    Environment = "development"
    Project     = "ReportMate"
    Owner       = "DevOps Team"
  }
}

# Variables
variable "database_password" {
  description = "Database administrator password"
  type        = string
  sensitive   = true
}

# Outputs
output "api_url" {
  description = "ReportMate API URL"
  value       = module.reportmate.front_door_endpoint
}

output "function_app_url" {
  description = "Direct Function App URL"
  value       = module.reportmate.function_app_url
}
