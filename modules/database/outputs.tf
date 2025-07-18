output "postgres_fqdn" {
  value       = azurerm_postgresql_flexible_server.pg.fqdn
  description = "FQDN of the PostgreSQL server"
}

output "postgres_name" {
  value       = azurerm_postgresql_flexible_server.pg.name
  description = "Name of the PostgreSQL server"
}

output "database_name" {
  value       = azurerm_postgresql_flexible_server_database.db.name
  description = "Name of the database"
}

output "connection_string" {
  value       = "postgresql://${var.db_username}:${var.db_password}@${azurerm_postgresql_flexible_server.pg.fqdn}:5432/${var.db_name}?sslmode=require"
  description = "PostgreSQL connection string"
  sensitive   = true
}
