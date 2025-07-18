output "managed_identity_id" {
  value       = azurerm_user_assigned_identity.main.id
  description = "ID of the managed identity"
}

output "managed_identity_client_id" {
  value       = azurerm_user_assigned_identity.main.client_id
  description = "Client ID of the managed identity"
}

output "managed_identity_principal_id" {
  value       = azurerm_user_assigned_identity.main.principal_id
  description = "Principal ID of the managed identity"
}

output "managed_identity_name" {
  value       = azurerm_user_assigned_identity.main.name
  description = "Name of the managed identity"
}
