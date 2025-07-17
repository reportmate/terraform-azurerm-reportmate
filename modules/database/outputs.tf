output "server_fqdn" {
  description = "FQDN of the PostgreSQL server"
  value       = azurerm_postgresql_flexible_server.reportmate.fqdn
}

output "server_name" {
  description = "Name of the PostgreSQL server"
  value       = azurerm_postgresql_flexible_server.reportmate.name
}

output "database_name" {
  description = "Name of the database"
  value       = azurerm_postgresql_flexible_server_database.reportmate.name
}

output "connection_string" {
  description = "PostgreSQL connection string"
  value       = "postgresql://${var.admin_username}:${var.admin_password}@${azurerm_postgresql_flexible_server.reportmate.fqdn}:5432/${azurerm_postgresql_flexible_server_database.reportmate.name}?sslmode=require"
  sensitive   = true
}
