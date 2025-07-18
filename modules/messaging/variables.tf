# Messaging Module Variables

variable "resource_group_name" {
  type        = string
  description = "Name of the resource group"
}

variable "location" {
  type        = string
  description = "Azure region"
}

variable "web_pubsub_name" {
  type        = string
  description = "Name of the Web PubSub service"
}

variable "web_pubsub_sku" {
  type        = string
  description = "Web PubSub SKU"
  default     = "Standard_S1"
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to resources"
  default     = {}
}
