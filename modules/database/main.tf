# PostgreSQL Flexible Server for storing osquery results
resource "azurerm_postgresql_flexible_server" "pg" {
  name                = var.postgres_server_name != "" ? var.postgres_server_name : "reportmate-database-${random_id.db_suffix.hex}"
  resource_group_name = var.resource_group_name
  location            = var.location

  administrator_login    = var.db_username
  administrator_password = var.db_password

  version                       = "16"
  storage_mb                    = var.db_storage_mb
  zone                          = "1"
  sku_name                      = var.db_sku_name
  public_network_access_enabled = true

  authentication {
    password_auth_enabled = true
  }

  tags = var.tags
}

# Random suffix to ensure unique database server name
resource "random_id" "db_suffix" {
  byte_length = 4
}

# Firewall rule to allow Azure services
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name             = "allow_azure"
  server_id        = azurerm_postgresql_flexible_server.pg.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# Firewall rule to allow specified IP addresses
resource "azurerm_postgresql_flexible_server_firewall_rule" "allowed_ips" {
  count            = length(var.allowed_ips) > 0 && var.allowed_ips[0] != "0.0.0.0/0" ? length(var.allowed_ips) : 0
  name             = "allow_ip_${count.index}"
  server_id        = azurerm_postgresql_flexible_server.pg.id
  start_ip_address = split("/", var.allowed_ips[count.index])[0]
  end_ip_address   = split("/", var.allowed_ips[count.index])[0]
}

# Allow all IPs if specified (for public access)
resource "azurerm_postgresql_flexible_server_firewall_rule" "public_access" {
  count            = contains(var.allowed_ips, "0.0.0.0/0") ? 1 : 0
  name             = "allow_all"
  server_id        = azurerm_postgresql_flexible_server.pg.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "255.255.255.255"
}

# Database
resource "azurerm_postgresql_flexible_server_database" "db" {
  name      = var.db_name
  server_id = azurerm_postgresql_flexible_server.pg.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

# Database schema initialization via API endpoint (when available)
resource "null_resource" "database_init_api" {
  depends_on = [
    azurerm_postgresql_flexible_server_database.db,
    azurerm_postgresql_flexible_server_firewall_rule.azure_services,
    azurerm_postgresql_flexible_server_firewall_rule.public_access
  ]

  triggers = {
    database_id = azurerm_postgresql_flexible_server_database.db.id
    always_run = timestamp()  # Always run to ensure schema is up to date
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo "Database created successfully"
      echo "FQDN: ${azurerm_postgresql_flexible_server.pg.fqdn}"
      echo "Database: ${var.db_name}"
      echo ""
      echo "To initialize the database schema, run one of the following:"
      echo ""
      echo "Option 1 - Via API (after Functions are deployed):"
      echo "curl 'https://YOUR_FUNCTION_APP.azurewebsites.net/api/test-db?init=true'"
      echo ""
      echo "Option 2 - Via psql client:"
      echo "PGPASSWORD='${var.db_password}' psql -h '${azurerm_postgresql_flexible_server.pg.fqdn}' -U '${var.db_username}' -d '${var.db_name}' -f '../../schemas/database.sql'"
      echo ""
      echo "Note: Database initialization will happen automatically when the API receives its first data."
    EOT
  }
}
