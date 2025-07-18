module "reportmate" {
  source = "reportmate/reportmate/azurerm"

  # Required variables
  resource_group_name = "reportmate-production"
  location            = "East US"
  db_password         = var.db_password

  # Production environment configuration
  environment = "prod"
  deploy_dev  = false
  deploy_prod = true

  # Custom domain configuration
  enable_custom_domain = true
  custom_domain_name   = "reportmate.example.com"

  # Use official container image
  container_image = "ghcr.io/reportmate/reportmate-app-web:latest"

  # Production features
  enable_machine_groups = true
  enable_business_units = true

  # Enhanced monitoring and storage
  log_retention_days     = 90
  app_insights_daily_cap = 50
  db_sku_name            = "GP_Standard_D2s_v3"
  db_storage_mb          = 65536

  tags = {
    Environment = "production"
    Project     = "ReportMate"
    Example     = "production"
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

output "frontdoor_endpoint" {
  value = module.reportmate.frontdoor_endpoint
}

output "frontdoor_validation_token" {
  value = module.reportmate.frontdoor_validation_token
}
