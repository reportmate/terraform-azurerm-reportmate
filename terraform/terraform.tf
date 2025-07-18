terraform {
  required_version = ">= 1.12.2"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.33.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
  
  # Disable automatic resource provider registration to avoid conflicts
  resource_provider_registrations = "none"
}