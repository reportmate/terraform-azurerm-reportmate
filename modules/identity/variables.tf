# Identity Module Variables

variable "resource_group_name" {
  type        = string
  description = "Name of the resource group"
}

variable "location" {
  type        = string
  description = "Azure region"
}

variable "managed_identity_name" {
  type        = string
  description = "Name of the user-assigned managed identity to create"
}

variable "existing_managed_identity_id" {
  type        = string
  description = "Resource ID of an existing user-assigned managed identity for the services to run as instead of the one this module creates"
  default     = null

  validation {
    condition     = var.existing_managed_identity_id == null || can(regex("^/subscriptions/[^/]+/resourceGroups/[^/]+/providers/Microsoft.ManagedIdentity/userAssignedIdentities/[^/]+$", var.existing_managed_identity_id))
    error_message = "existing_managed_identity_id must be a user-assigned managed identity resource ID."
  }
}

variable "create_managed_identity" {
  type        = bool
  description = "Whether to create the module's own managed identity"
  default     = true
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

# Dependencies for RBAC assignments
variable "storage_account_id" {
  type        = string
  description = "ID of the storage account"
}

variable "app_insights_id" {
  type        = string
  description = "ID of the Application Insights instance"
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to resources"
  default     = {}
}
