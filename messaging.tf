# Web PubSub (SignalR) for real-time event streaming
resource "azurerm_web_pubsub" "wps" {
  name                = "reportmate-signalr"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Standard_S1"
  capacity            = 1
  public_network_access_enabled = true
}
