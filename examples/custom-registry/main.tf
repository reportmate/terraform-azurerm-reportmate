module "reportmate" {
  source = "../../"

  # Required variables
  resource_group_name = "reportmate-custom"
  location            = "East US"
  db_password         = var.db_password

  # Use custom container registry
  use_custom_registry     = true
  container_registry_name = "mycompany-reportmate-acr"
  container_image         = "mycompany-reportmate-acr.azurecr.io/reportmate:custom-v1.0"

  # Deploy both environments
  environment = "both"
  deploy_dev  = true
  deploy_prod = true

  # Enable all features
  enable_machine_groups = true
  enable_business_units = true

  tags = {
    Environment = "custom"
    Project     = "ReportMate"
    Example     = "custom-registry"
  }
}

variable "db_password" {
  type        = string
  description = "PostgreSQL admin password"
  sensitive   = true
}

output "frontend_dev_url" {
  value = module.reportmate.frontend_dev_url
}

output "frontend_prod_url" {
  value = module.reportmate.frontend_prod_url
}

output "api_url" {
  value = module.reportmate.api_url
}

output "container_registry_login_server" {
  value = module.reportmate.container_registry_login_server
}
