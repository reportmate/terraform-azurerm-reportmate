variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "function_app_hostname" {
  description = "Hostname of the Function App"
  type        = string
}

variable "custom_domain" {
  description = "Custom domain for the API (optional)"
  type        = string
  default     = null
}

variable "suffix" {
  description = "Random suffix for unique naming"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
