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

variable "app_insights_daily_cap" {
  type        = number
  description = "Application Insights daily data cap in GB"
  default     = 10
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to resources"
  default     = {}
}
