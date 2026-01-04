variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "function_app_name" {
  description = "Name of the Azure Functions App"
  type        = string
  default     = "reportmate-functions"
}

variable "sku_name" {
  description = "SKU for the App Service Plan (Y1=Consumption, B1=Basic, S1=Standard, P1V2=Premium)"
  type        = string
  default     = "Y1"

  validation {
    condition     = contains(["Y1", "B1", "B2", "B3", "S1", "S2", "S3", "P1V2", "P2V2", "P3V2"], var.sku_name)
    error_message = "SKU must be a valid App Service Plan tier"
  }
}

variable "api_base_url" {
  description = "Base URL for ReportMate API (for storage alerts function)"
  type        = string
}

variable "client_passphrases" {
  description = "API passphrase for authentication"
  type        = string
  sensitive   = true
}

variable "teams_webhook_url" {
  description = "Microsoft Teams incoming webhook URL for alerts"
  type        = string
  default     = ""
  sensitive   = true
}

variable "app_insights_connection_string" {
  description = "Application Insights connection string for monitoring"
  type        = string
  sensitive   = true
}

variable "key_vault_id" {
  description = "Optional Key Vault ID for secrets access"
  type        = string
  default     = null
}

variable "additional_app_settings" {
  description = "Additional application settings for the Function App"
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
