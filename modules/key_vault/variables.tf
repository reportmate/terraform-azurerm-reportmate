variable "key_vault_name" {
  description = "Name of the Key Vault"
  type        = string
}

variable "location" {
  description = "Azure region for the Key Vault"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "sku_name" {
  description = "Key Vault SKU name"
  type        = string
  default     = "standard"
}

variable "default_network_action" {
  description = "Default network access action"
  type        = string
  default     = "Allow"
}

variable "allowed_ips" {
  description = "List of allowed IP addresses"
  type        = list(string)
  default     = []
}

variable "enable_purge_protection" {
  description = "Enable purge protection"
  type        = bool
  default     = true
}

variable "soft_delete_retention_days" {
  description = "Soft delete retention period in days"
  type        = number
  default     = 7
}

variable "managed_identity_principal_id" {
  description = "Principal ID of the managed identity to grant access"
  type        = string
  default     = null
}

variable "devops_resource_infrasec_group_object_id" {
  description = "Object ID of the DevOps Resource InfraSec group for Key Vault access"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
