# Web PubSub for the dashboard's live event stream.
#
# Do not remove this because metrics show no connections. That has been
# concluded once already, and it was wrong: the dashboard was negotiating
# against the public API URL instead of the same-origin proxy that carries the
# internal secret, so the auth-gated negotiate endpoint returned 401 to every
# browser and the client fell back to polling without surfacing anything. The
# service was working the whole time.
#
# Clients never build the WebSocket URL themselves — the API's /negotiate
# endpoint returns it along with a short-lived access token, and the hub it
# points at is "events" (api/dependencies.py). An env var duplicating that URL
# used to live on the frontend container and named a hub, "fleet", that does not
# exist; it was removed rather than corrected, because negotiate is the only
# thing that should be naming the hub.
#
# Standard is required, not incidental: Free caps at 20 connections and 20k
# messages/day. The Standard unit includes 1M messages/day, comfortably above
# current broadcast volume.
resource "azurerm_web_pubsub" "main" {
  name                          = var.web_pubsub_name
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
