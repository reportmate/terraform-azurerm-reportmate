# PostgreSQL Flexible Server for storing osquery results
resource "azurerm_postgresql_flexible_server" "pg" {
  name                = var.postgres_server_name != "" ? var.postgres_server_name : "reportmate-database-${random_id.db_suffix.hex}"
  resource_group_name = var.resource_group_name
  location            = var.location

  administrator_login    = var.db_username
  administrator_password = var.db_password

  version                       = "16"
  storage_mb                    = var.db_storage_mb
  sku_name                      = var.db_sku_name
  public_network_access_enabled = true

  # Grow storage automatically rather than hitting the read-only lock Azure
  # applies at capacity. At the observed ~1.0 GiB/day this server reaches 95% of
  # 256 GB around 2027-01-26 -- two months before the April reporting window --
  # and every fleet write stops. This was enabled by hand during the 2026-07-16
  # remediation but never committed, so a later apply turned it back off.
  auto_grow_enabled = true

  backup_retention_days        = var.db_backup_retention_days
  geo_redundant_backup_enabled = var.db_geo_redundant_backup

  authentication {
    password_auth_enabled = true
  }

  tags = var.tags

  lifecycle {
    prevent_destroy = true

    # Once auto-grow owns the storage size, Azure moves it without Terraform.
    # Without this the next plan reads the grown size as drift and tries to
    # shrink it back to db_storage_mb, which the service rejects outright --
    # PostgreSQL flexible server storage can only ever increase. db_storage_mb
    # therefore sets the floor at create time and is inert afterwards.
    ignore_changes = [zone, storage_mb]
  }
}

# Random suffix to ensure unique database server name
resource "random_id" "db_suffix" {
  byte_length = 4
}

# Connection ceiling for the server. The API sizes its per-replica pools against
# this number (see api_db_pool_max in the containers module), so it belongs in
# code rather than sitting at whatever the server happens to report.
#
# max_connections is a static parameter: changing it restarts the server. The
# default here matches the value already running, so a plan is a no-op until
# someone deliberately raises it — do that in a maintenance window, not
# alongside an unrelated apply.
resource "azurerm_postgresql_flexible_server_configuration" "max_connections" {
  name      = "max_connections"
  server_id = azurerm_postgresql_flexible_server.pg.id
  value     = tostring(var.db_max_connections)
}

# Firewall rule to allow Azure services
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name             = "allow_azure"
  server_id        = azurerm_postgresql_flexible_server.pg.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# Client ranges other than the catch-all, which is handled by public_access below.
# Filtering into a local rather than indexing var.allowed_ips directly matters:
# Terraform evaluates both sides of &&, so the previous
# `length(...) > 0 && var.allowed_ips[0] != "0.0.0.0/0"` raised "Invalid index"
# on an empty list, and a list whose first element was the catch-all silently
# produced no rules for the remaining entries.
locals {
  explicit_client_ips = [for ip in var.allowed_ips : ip if ip != "0.0.0.0/0"]
}

# Firewall rule to allow specified IP addresses
resource "azurerm_postgresql_flexible_server_firewall_rule" "allowed_ips" {
  count            = length(local.explicit_client_ips)
  name             = "allow_ip_${count.index}"
  server_id        = azurerm_postgresql_flexible_server.pg.id
  start_ip_address = split("/", local.explicit_client_ips[count.index])[0]
  end_ip_address   = split("/", local.explicit_client_ips[count.index])[0]
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

  # Prevent accidental database destruction
  lifecycle {
    prevent_destroy = true
  }
}

# Database schema initialization via API endpoint (after functions deployment)
resource "null_resource" "database_init_api" {
  depends_on = [
    azurerm_postgresql_flexible_server_database.db,
    azurerm_postgresql_flexible_server_firewall_rule.azure_services,
    azurerm_postgresql_flexible_server_firewall_rule.public_access
  ]

  triggers = {
    database_id = azurerm_postgresql_flexible_server_database.db.id
    # Only run once, unless manually triggered
    run_once = "initial_setup"
  }

  provisioner "local-exec" {
    command = <<-EOF
      echo "Database Infrastructure Ready"
      echo "================================================================"
      echo "[SUCCESS] PostgreSQL Server: ${azurerm_postgresql_flexible_server.pg.fqdn}"
      echo "[SUCCESS] Database: ${var.db_name}"
      echo "[SUCCESS] Username: ${var.db_username}"
      echo "[SUCCESS] Firewall Rules: Configured"
      echo ""
      echo "Next Steps:"
      echo "1. Deploy Containers: terraform apply (containers module)"
      echo "2. Initialize Schema: curl '<API_URL>/api/v1/init-db?init=true'"
      echo "3. Validate Setup: pwsh infrastructure/scripts/check.ps1"
      echo ""
      echo "For complete bootstrap, run: pwsh infrastructure/scripts/bootstrap.ps1"
      echo "================================================================"
    EOF
  }
}
