# Storage account and queue for osquery data ingestion
resource "azurerm_storage_account" "main" {
  name                     = var.use_exact_name ? var.storage_account_name : "${replace(var.storage_account_name, "-", "")}${random_id.storage_suffix.hex}"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = var.storage_tier
  account_replication_type = var.storage_replication

  tags = var.tags
}

# Random suffix to ensure unique storage account name
resource "random_id" "storage_suffix" {
  byte_length = 4
}

# Queue for osquery data ingestion
resource "azurerm_storage_queue" "ingest" {
  name               = "osquery-ingest"
  storage_account_id = azurerm_storage_account.main.id
}
