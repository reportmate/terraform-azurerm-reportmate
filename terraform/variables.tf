# =================================================================
# REQUIRED VARIABLES
# =================================================================

variable "resource_group_name" {
  type        = string
  description = "Name of the Azure resource group to create"
}

variable "location" {
  type        = string
  description = "Azure region where resources will be deployed"
}

variable "db_password" {
  type        = string
  description = "PostgreSQL administrator password"
  sensitive   = true
}

# =================================================================
# OPTIONAL VARIABLES
# =================================================================

# Subscription Configuration
variable "subscription_id" {
  type        = string
  description = "Azure subscription ID"
  default     = null
}

# Database Configuration
variable "db_username" {
  type        = string
  description = "PostgreSQL administrator username"
  default     = "reportmate"
}

variable "db_name" {
  type        = string
  description = "Name of the PostgreSQL database"
  default     = "reportmate"
}

variable "db_sku_name" {
  type        = string
  description = "PostgreSQL SKU name"
  default     = "B_Standard_B1ms"
}

variable "db_storage_mb" {
  type        = number
  description = "PostgreSQL storage size in MB"
  default     = 32768
}

variable "allowed_ips" {
  type        = list(string)
  description = "List of IP addresses allowed to access the database"
  default     = ["0.0.0.0/0"]
}

# Storage Configuration
variable "storage_account_name" {
  type        = string
  description = "Name of the storage account (will be made globally unique)"
  default     = "reportmatestorage"
}

variable "storage_tier" {
  type        = string
  description = "Storage account tier"
  default     = "Standard"
}

variable "storage_replication" {
  type        = string
  description = "Storage account replication type"
  default     = "LRS"
}

# Messaging Configuration
variable "web_pubsub_name" {
  type        = string
  description = "Name of the Web PubSub service"
  default     = "reportmate-signalr"
}

variable "web_pubsub_sku" {
  type        = string
  description = "Web PubSub SKU"
  default     = "Standard_S1"
}

# Monitoring Configuration
variable "app_insights_name" {
  type        = string
  description = "Name of the Application Insights instance"
  default     = "reportmate-app-insights"
}

variable "log_analytics_name" {
  type        = string
  description = "Name of the Log Analytics workspace"
  default     = "reportmate-logs"
}

variable "log_retention_days" {
  type        = number
  description = "Log retention period in days"
  default     = 30
}

variable "app_insights_daily_cap" {
  type        = number
  description = "Application Insights daily data cap in GB"
  default     = 10
}

# Identity Configuration
variable "managed_identity_name" {
  type        = string
  description = "Name of the user-assigned managed identity"
  default     = "reportmate-identity"
}

variable "enable_pipeline_permissions" {
  type        = bool
  description = "Enable RBAC permissions for Azure DevOps pipeline service principal"
  default     = false
}

variable "pipeline_service_principal_id" {
  type        = string
  description = "Object ID of the Azure DevOps pipeline service principal"
  default     = ""
}

# Functions Configuration
variable "function_app_name" {
  type        = string
  description = "Name of the Azure Function App"
  default     = "reportmate-api"
}

variable "service_plan_name" {
  type        = string
  description = "Name of the App Service Plan"
  default     = "reportmate-functions"
}

variable "python_version" {
  type        = string
  description = "Python version for Azure Functions"
  default     = "3.12"
}

# Container Configuration
variable "container_registry_name" {
  type        = string
  description = "Name of the Azure Container Registry (will be made globally unique)"
  default     = "reportmateacr"
}

variable "use_custom_registry" {
  type        = bool
  description = "Whether to use a custom container registry instead of the public GitHub registry"
  default     = false
}

variable "container_image" {
  type        = string
  description = "Container image to deploy for the web application"
  default     = "ghcr.io/reportmate/reportmate-app-web:latest"
}

# Environment Configuration
variable "environment" {
  type        = string
  description = "Deployment environment (dev, prod, or both)"
  default     = "prod"
  validation {
    condition     = contains(["dev", "prod", "both"], var.environment)
    error_message = "Environment must be 'dev', 'prod', or 'both'."
  }
}

variable "deploy_dev" {
  type        = bool
  description = "Deploy development container app"
  default     = false
}

variable "deploy_prod" {
  type        = bool
  description = "Deploy production container app"
  default     = true
}

# Networking Configuration
variable "enable_custom_domain" {
  type        = bool
  description = "Enable custom domain configuration with Azure Front Door"
  default     = false
}

variable "custom_domain_name" {
  type        = string
  description = "Custom domain name for the frontend (e.g., reportmate.example.com)"
  default     = ""
}

variable "frontdoor_name" {
  type        = string
  description = "Name of the Azure Front Door profile"
  default     = "reportmate-frontdoor"
}

# Client Authentication Configuration
variable "client_passphrases" {
  type        = string
  description = "Comma-separated list of client passphrases for restricted access"
  default     = ""
  sensitive   = true
}

variable "enable_machine_groups" {
  type        = bool
  description = "Enable per-machine-group passphrase authentication"
  default     = false
}

variable "enable_business_units" {
  type        = bool
  description = "Enable business units for organizational access control"
  default     = false
}

# Tags
variable "tags" {
  type        = map(string)
  description = "A map of tags to assign to the resources"
  default = {
    Environment = "production"
    Project     = "ReportMate"
    ManagedBy   = "Terraform"
  }
}
