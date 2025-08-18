output "key_vault_id" {
  description = "ID of the Key Vault"
  value       = azurerm_key_vault.reportmate.id
}

output "key_vault_name" {
  description = "Name of the Key Vault"
  value       = azurerm_key_vault.reportmate.name
}

output "key_vault_uri" {
  description = "URI of the Key Vault"
  value       = azurerm_key_vault.reportmate.vault_uri
}
