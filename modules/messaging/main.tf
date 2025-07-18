# Web PubSub (SignalR) for real-time event streaming
resource "azurerm_web_pubsub" "main" {
  name                          = "${var.web_pubsub_name}-${random_id.pubsub_suffix.hex}"
  resource_group_name           = var.resource_group_name
  location                      = var.location
  sku                           = var.web_pubsub_sku
  capacity                      = 1
  public_network_access_enabled = true

  tags = var.tags
}

# Random suffix to ensure unique Web PubSub name
resource "random_id" "pubsub_suffix" {
  byte_length = 4
}
