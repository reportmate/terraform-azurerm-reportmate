variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "frontdoor_name" {
  description = "Name of the Front Door profile"
  type        = string
  default     = "reportmate-frontdoor"
}

variable "custom_domain_name" {
  description = "Custom domain name for the application"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "frontend_fqdn" {
  description = "FQDN of the frontend container app"
  type        = string
}

variable "function_app_hostname" {
  description = "Hostname of the Function App"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
