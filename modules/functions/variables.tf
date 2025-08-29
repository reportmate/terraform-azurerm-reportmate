# API Module Variables

variable "resource_group_name" {
  type        = string
  description = "Name of the Azure resource group"
}

variable "location" {
  type        = string
  description = "Azure region for deployment"
}

variable "function_app_name" {
  type        = string
  description = "Name of the Azure Function App"
  default     = "reportmate-api"
}

variable "service_plan_name" {
  type        = string
  description = "Name of the App Service Plan"
  default     = "reportmate-api-plan"
}

variable "sku_name" {
  type        = string
  description = "SKU name for the App Service Plan"
  default     = "Y1"  # Consumption plan
}

variable "python_version" {
  type        = string
  description = "Python version for Azure Functions"
  default     = "3.12"
}

variable "enable_code_deployment" {
  type        = bool
  description = "Whether to automatically deploy API code"
  default     = false
}

variable "allowed_origins" {
  type        = list(string)
  description = "CORS allowed origins"
  default     = ["*"]
}

# Dependencies
variable "storage_account_name" {
  type        = string
  description = "Storage account name for functions"
}

variable "storage_account_access_key" {
  type        = string
  description = "Storage account access key"
  sensitive   = true
}

variable "storage_connection_string" {
  type        = string
  description = "Storage account connection string"
  sensitive   = true
}

variable "queue_name" {
  type        = string
  description = "Storage queue name"
}

variable "managed_identity_id" {
  type        = string
  description = "Managed identity resource ID"
}

variable "managed_identity_client_id" {
  type        = string
  description = "Managed identity client ID"
}

variable "database_url" {
  type        = string
  description = "PostgreSQL database connection string"
  sensitive   = true
}

variable "web_pubsub_connection_string" {
  type        = string
  description = "Web PubSub connection string"
  sensitive   = true
}

variable "app_insights_connection_string" {
  type        = string
  description = "Application Insights connection string"
  sensitive   = true
}

variable "app_insights_key" {
  type        = string
  description = "Application Insights instrumentation key"
  sensitive   = true
}

variable "log_analytics_workspace_id" {
  type        = string
  description = "Log Analytics workspace ID"
}

variable "log_analytics_workspace_key" {
  type        = string
  description = "Log Analytics workspace key"
  sensitive   = true
}

variable "client_passphrases" {
  type        = string
  description = "Client passphrases for authentication"
  default     = ""
  sensitive   = true
}

variable "api_key" {
  type        = string
  description = "API key for client authentication"
  default     = ""
  sensitive   = true
}

variable "enable_machine_groups" {
  type        = bool
  description = "Enable machine groups"
  default     = false
}

variable "enable_business_units" {
  type        = bool
  description = "Enable business units"
  default     = false
}

variable "tags" {
  type        = map(string)
  description = "Resource tags"
  default     = {}
}
