# Monitoring Module Variables

variable "resource_group_name" {
  type        = string
  description = "Name of the resource group"
}

variable "location" {
  type        = string
  description = "Azure region"
}

variable "app_insights_name" {
  type        = string
  description = "Name of the Application Insights instance"
}

variable "log_analytics_name" {
  type        = string
  description = "Name of the Log Analytics workspace"
}

variable "log_retention_days" {
  type        = number
  description = "Log retention period in days"
  default     = 30
}

variable "log_daily_quota_gb" {
  description = "Daily ingestion cap in GB for the Log Analytics workspace. Ingestion pauses for the remainder of the UTC day once reached, so size it above normal volume: this is a runaway backstop, not a shaping tool. -1 disables the cap."
  type        = number
  default     = 2

  validation {
    condition     = var.log_daily_quota_gb == -1 || var.log_daily_quota_gb >= 0.1
    error_message = "log_daily_quota_gb must be -1 (uncapped) or at least 0.1 GB."
  }
}

variable "app_insights_daily_cap" {
  type        = number
  description = "Application Insights daily data cap in GB"
  default     = 1
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to resources"
  default     = {}
}
