module "reportmate" {
  source = "reportmate/reportmate/azurerm"

  # Required variables
  resource_group_name = "reportmate-basic"
  location            = "East US"
  db_password         = var.db_password

  # Use development environment for basic deployment
  environment = "dev"
  deploy_dev  = true
  deploy_prod = false

  # Use official container image (default)
  container_image = "ghcr.io/reportmate/reportmate-app-web:latest"

  # Optional: Enable machine groups
  enable_machine_groups = true

  tags = {
    Environment = "development"
    Project     = "ReportMate"
    Example     = "basic"
  }
}

variable "db_password" {
  type        = string
  description = "PostgreSQL admin password"
  sensitive   = true
}

output "frontend_url" {
  value = module.reportmate.frontend_url
}

output "api_url" {
  value = module.reportmate.api_url
}

output "database_fqdn" {
  value = module.reportmate.database_fqdn
}
