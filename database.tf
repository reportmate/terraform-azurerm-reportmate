# PostgreSQL Flexible Server for storing osquery results
resource "azurerm_postgresql_flexible_server" "pg" {
  name                   = "reportmate-database"
  resource_group_name    = azurerm_resource_group.rg.name
  location               = azurerm_resource_group.rg.location

  administrator_login    = var.db_username
  administrator_password = var.db_password

  version                = "16"
  storage_mb             = 32768
  zone                   = "1"  # Use zone 1 for Canada Central
  sku_name               = "B_Standard_B1ms"
  public_network_access_enabled = true

  authentication {
    password_auth_enabled = true
  }

  # Temporarily removed ignore_changes to force password sync
  # lifecycle {
  #   ignore_changes = [
  #     administrator_password
  #   ]
  # }
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name              = "allow_azure"
  server_id         = azurerm_postgresql_flexible_server.pg.id
  start_ip_address  = "0.0.0.0"
  end_ip_address    = "0.0.0.0"
}

# Allow Azure Container Apps outbound IPs (broad range for Canada Central)
resource "azurerm_postgresql_flexible_server_firewall_rule" "container_apps" {
  name              = "allow_container_apps"
  server_id         = azurerm_postgresql_flexible_server.pg.id
  start_ip_address  = "0.0.0.0"
  end_ip_address    = "255.255.255.255"
}

resource "azurerm_postgresql_flexible_server_database" "db" {
  name      = "reportmate"
  server_id = azurerm_postgresql_flexible_server.pg.id
  collation = "en_US.utf8"
  charset   = "utf8"

  # lifecycle {
  #   prevent_destroy = true
  # }
}

# Optionally allow your local IP for dev access:
# variable "my_ip" {
#   description = "Public IP for local dev box"
#   type        = string
#   default     = "203.0.113.27"   # replace with your IP
# }
#
# resource "azurerm_postgresql_flexible_server_firewall_rule" "me" {
#   name              = "allow_me"
#   server_id         = azurerm_postgresql_flexible_server.pg.id
#   start_ip_address  = var.my_ip
#   end_ip_address    = var.my_ip
# }
