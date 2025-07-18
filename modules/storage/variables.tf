# Storage Module Variables

variable "resource_group_name" {
  type        = string
  description = "Name of the resource group"
}

variable "location" {
  type        = string
  description = "Azure region"
}

variable "storage_account_name" {
  type        = string
  description = "Base name of the storage account (will be made globally unique)"
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

variable "tags" {
  type        = map(string)
  description = "Tags to apply to resources"
  default     = {}
}
