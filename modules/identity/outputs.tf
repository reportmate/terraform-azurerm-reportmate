output "managed_identity_id" {
  value       = local.identity.id
  description = "ID of the managed identity the services run as"

  precondition {
    condition     = var.create_managed_identity || var.existing_managed_identity_id != null
    error_message = "Set existing_managed_identity_id, or leave create_managed_identity on."
  }
}

output "managed_identity_client_id" {
  value       = local.identity.client_id
  description = "Client ID of the managed identity the services run as"
}

output "managed_identity_principal_id" {
  value       = local.identity.principal_id
  description = "Principal ID of the managed identity the services run as"
}

output "managed_identity_name" {
  value       = local.identity.name
  description = "Name of the managed identity the services run as"
}
