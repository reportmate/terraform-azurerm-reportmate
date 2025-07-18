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
  description = "Name of the user-assigned managed identity"
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

variable "web_pubsub_id" {
  type        = string
  description = "ID of the Web PubSub service"
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
