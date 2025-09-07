# ReportMate Infrastructure

# This file serves as the main entry point for the ReportMate infrastructure
# Components are organized into separate files for better maintainability:
#
# Resource Group
resource "azurerm_resource_group" "rg" {
  name     = "ReportMate"
  location = "Canada Central"
  tags = {
    GitOps = "Terraformed"
  }
}

# - database.tf       - PostgreSQL database
# - functions.tf      - Azure Functions
# - storage.tf        - Storage account and queues
# - messaging.tf      - Web PubSub (SignalR)
# - monitoring.tf     - Application Insights
# - containers.tf     - Container registry and apps
# - identity.tf       - Role-based access control
# - variables.tf      - Input variables
# - outputs.tf        - Output values
#
# Infrastructure components are defined in their respective files.
# All outputs are consolidated in outputs.tf for easy reference.

