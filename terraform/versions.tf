terraform {
  required_version = ">= 1.12"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.33"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }
}
