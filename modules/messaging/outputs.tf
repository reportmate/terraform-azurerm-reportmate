output "web_pubsub_id" {
  value       = azurerm_web_pubsub.main.id
  description = "ID of the Web PubSub service"
}

output "web_pubsub_hostname" {
  value       = azurerm_web_pubsub.main.hostname
  description = "Hostname of the Web PubSub service"
}

output "web_pubsub_connection_string" {
  value       = azurerm_web_pubsub.main.primary_connection_string
  description = "Primary connection string of the Web PubSub service"
  sensitive   = true
}
