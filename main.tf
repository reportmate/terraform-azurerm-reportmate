# ReportMate Infrastructure - Main Module
# This module provisions a complete ReportMate infrastructure on Azure

# Resource Group
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location

  tags = merge(var.tags, {
    ManagedBy = "Terraform"
    Module    = "ReportMate"
  })
}

# Database Module
module "database" {
  source = "./modules/database"

  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  postgres_server_name = "reportmate-database"
  db_username   = var.db_username
  db_password   = var.db_password
  db_name       = var.db_name
  db_sku_name   = var.db_sku_name
  db_storage_mb = var.db_storage_mb

  allowed_ips = var.allowed_ips
  tags        = var.tags
}

# Storage Module
module "storage" {
  source = "./modules/storage"

  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  storage_account_name = var.storage_account_name
  use_exact_name       = true
  storage_tier         = var.storage_tier
  storage_replication  = var.storage_replication

  tags = var.tags
}

# Messaging Module
module "messaging" {
  source = "./modules/messaging"

  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  web_pubsub_name = var.web_pubsub_name
  web_pubsub_sku  = var.web_pubsub_sku

  tags = var.tags
}

# Monitoring Module
module "monitoring" {
  source = "./modules/monitoring"

  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  app_insights_name      = var.app_insights_name
  log_analytics_name     = var.log_analytics_name
  log_retention_days     = var.log_retention_days
  app_insights_daily_cap = var.app_insights_daily_cap

  tags = var.tags
}

# Identity Module
module "identity" {
  source = "./modules/identity"

  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  managed_identity_name         = var.managed_identity_name
  enable_pipeline_permissions   = var.enable_pipeline_permissions
  pipeline_service_principal_id = var.pipeline_service_principal_id

  # Dependencies
  storage_account_id = module.storage.storage_account_id
  web_pubsub_id      = module.messaging.web_pubsub_id
  app_insights_id    = module.monitoring.app_insights_id

  tags = var.tags
}

# Functions Module (Azure Functions API)
module "functions" {
  source = "./modules/functions"

  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  function_app_name = var.function_app_name
  service_plan_name = var.service_plan_name
  python_version    = var.python_version

  # Dependencies
  storage_account_name       = module.storage.storage_account_name
  storage_account_access_key = module.storage.storage_account_access_key
  storage_connection_string  = module.storage.storage_connection_string
  queue_name                 = module.storage.queue_name
  managed_identity_id        = module.identity.managed_identity_id
  managed_identity_client_id = module.identity.managed_identity_client_id

  # Database connection
  database_url = "postgresql://${var.db_username}:${var.db_password}@${module.database.postgres_fqdn}:5432/${var.db_name}?sslmode=require"

  # Messaging
  web_pubsub_connection_string = module.messaging.web_pubsub_connection_string

  # Monitoring
  app_insights_connection_string = module.monitoring.app_insights_connection_string
  app_insights_key               = module.monitoring.app_insights_key
  log_analytics_workspace_id     = module.monitoring.log_analytics_workspace_id
  log_analytics_workspace_key    = module.monitoring.log_analytics_workspace_key

  # Configuration
  client_passphrases    = var.client_passphrases
  enable_machine_groups = var.enable_machine_groups
  enable_business_units = var.enable_business_units
  enable_code_deployment = true  # Enable automatic code deployment

  tags = var.tags
}

# Containers Module
module "containers" {
  source = "./modules/containers"

  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  container_registry_name = var.container_registry_name
  use_custom_registry     = var.use_custom_registry
  container_image         = var.container_image
  environment             = var.environment
  deploy_dev              = var.deploy_dev
  deploy_prod             = var.deploy_prod

  # Dependencies
  managed_identity_id            = module.identity.managed_identity_id
  managed_identity_principal_id  = module.identity.managed_identity_principal_id
  database_url                   = "postgresql://${var.db_username}:${var.db_password}@${module.database.postgres_fqdn}:5432/${var.db_name}?sslmode=require"
  web_pubsub_hostname            = module.messaging.web_pubsub_hostname
  function_app_hostname          = module.functions.function_app_hostname
  app_insights_connection_string = module.monitoring.app_insights_connection_string
  log_analytics_workspace_id     = module.monitoring.log_analytics_id

  tags = var.tags
}

# Networking Module (Front Door)
module "networking" {
  count = var.enable_custom_domain && var.custom_domain_name != "" ? 1 : 0

  source = "./modules/networking"

  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  frontdoor_name     = var.frontdoor_name
  custom_domain_name = var.custom_domain_name
  environment        = var.environment

  # Dependencies
  frontend_fqdn         = module.containers.frontend_fqdn
  function_app_hostname = module.functions.function_app_hostname

  tags = var.tags
}

