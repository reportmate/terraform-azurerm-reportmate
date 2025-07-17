# PostgreSQL Flexible Server
resource "azurerm_postgresql_flexible_server" "reportmate" {
  name                = "reportmate-db-${var.suffix}"
  resource_group_name = var.resource_group_name
  location           = var.location

  administrator_login    = var.admin_username
  administrator_password = var.admin_password

  sku_name   = "B_Standard_B1ms"
  version    = "14"
  storage_mb = 32768

  backup_retention_days        = 7
  geo_redundant_backup_enabled = false

  high_availability {
    mode = "ZoneRedundant"
  }

  tags = var.tags
}

# PostgreSQL Database
resource "azurerm_postgresql_flexible_server_database" "reportmate" {
  name      = var.database_name
  server_id = azurerm_postgresql_flexible_server.reportmate.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

# Firewall rule to allow Azure services
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.reportmate.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}
