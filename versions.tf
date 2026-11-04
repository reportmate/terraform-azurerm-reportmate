terraform {
  required_version = ">= 1.5"

  backend "azurerm" {}

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.33"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.1"
    }
    azapi = {
      source  = "Azure/azapi"
      version = "~> 2.0"
    }
  }
}

provider "azurerm" {
  features {}
  # Left null unless supplied, so the provider falls back to ARM_SUBSCRIPTION_ID
  # or the CLI's current context. Never hardcode a subscription here: this module
  # is published, and a literal makes every plan target one specific tenant.
  subscription_id = var.subscription_id
}

provider "azuread" {
}

# Used only to set Function App properties the azurerm Flex Consumption
# resource does not expose. Authenticates the same way azurerm does.
provider "azapi" {
  subscription_id = var.subscription_id
}
