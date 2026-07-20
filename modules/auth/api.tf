# ---------------------------------------------------------------------------
# ReportMate API — protected-resource app registration (OIDC bearer auth)
# ---------------------------------------------------------------------------
# This is the API *resource* the FastAPI backend validates bearer tokens
# against, kept separate from reportmate_web (the interactive web *client*).
# Operators obtain a token for this resource the same way they do for any Azure
# resource -- e.g.
#
#     az account get-access-token --resource api://<api_client_id>
#
# -- and the API maps the token's app roles (ReportMate.Read/Ingest/Admin) onto
# its read/ingest/admin scopes. Services use client-credential (app-only) tokens
# for the same audience.
#
# Everything here is gated by var.enable_oidc_api (default false), so the module
# is a no-op until ECU turns OIDC on -- matching the API code, which ignores
# bearer tokens until ENABLE_OIDC_AUTH is set. Enabling it is what actually
# creates the Entra objects.

locals {
  # Stable GUIDs so re-applies never churn the registration.
  oidc_role_read_id     = "a1a10001-0000-4000-8000-000000000001"
  oidc_role_ingest_id   = "a1a10002-0000-4000-8000-000000000002"
  oidc_role_admin_id    = "a1a10003-0000-4000-8000-000000000003"
  oidc_scope_as_user_id = "b2b20001-0000-4000-8000-000000000001"

  # Azure CLI first-party client id -- pre-authorized below so an operator can
  # mint a delegated token with `az account get-access-token` without a separate
  # consent prompt.
  azure_cli_client_id = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
}

resource "azuread_application" "reportmate_api" {
  count            = var.enable_oidc_api ? 1 : 0
  display_name     = "${var.app_display_name} API"
  owners           = concat([data.azuread_client_config.current.object_id], length(var.app_owners) > 0 ? data.azuread_users.app_owners[0].object_ids : [])
  sign_in_audience = var.sign_in_audience

  api {
    # Emit v2.0 access tokens so `iss` is the v2 issuer and the claims match
    # what the API validator expects (aud = App ID URI / client id, roles claim).
    requested_access_token_version = 2

    # Delegated scope for interactive callers (operators via az, the dashboard).
    # Assigned users' app roles still arrive in the `roles` claim; this scope is
    # what lets a public client request a token for this API at all.
    oauth2_permission_scope {
      id                         = local.oidc_scope_as_user_id
      value                      = "access_as_user"
      type                       = "User"
      enabled                    = true
      admin_consent_display_name = "Access the ReportMate API"
      admin_consent_description  = "Allow the app to access the ReportMate API as the signed-in user."
      user_consent_display_name  = "Access the ReportMate API"
      user_consent_description   = "Allow the app to access the ReportMate API on your behalf."
    }
  }

  # App roles map 1:1 onto the API's least-privilege scopes. allowed_member_types
  # includes "Application" (client-credential / service tokens) and "User"
  # (assigned users/groups, whose delegated tokens then carry the `roles` claim).
  # admin is a superset in the API, so an admin token also reads and ingests.
  app_role {
    id                   = local.oidc_role_read_id
    allowed_member_types = ["Application", "User"]
    value                = "ReportMate.Read"
    display_name         = "ReportMate.Read"
    description          = "Read fleet and device data (GET)."
    enabled              = true
  }

  app_role {
    id                   = local.oidc_role_ingest_id
    allowed_member_types = ["Application", "User"]
    value                = "ReportMate.Ingest"
    display_name         = "ReportMate.Ingest"
    description          = "Submit device telemetry (POST)."
    enabled              = true
  }

  app_role {
    id                   = local.oidc_role_admin_id
    allowed_member_types = ["Application", "User"]
    value                = "ReportMate.Admin"
    display_name         = "ReportMate.Admin"
    description          = "Full access: mutations, deletes, and admin endpoints."
    enabled              = true
  }

  tags = var.azuread_tags
}

# Tenant policy blocks api://<friendly-name> URIs, so pin api://<client_id> the
# same way reportmate_web does (identifier_uris can't reference the app's own
# client id at create time).
resource "null_resource" "reportmate_api_identifier_uri" {
  count      = var.enable_oidc_api ? 1 : 0
  depends_on = [azuread_application.reportmate_api]

  provisioner "local-exec" {
    command    = "az ad app update --id ${azuread_application.reportmate_api[0].client_id} --identifier-uris api://${azuread_application.reportmate_api[0].client_id}"
    on_failure = continue
  }
}

resource "azuread_service_principal" "reportmate_api" {
  count                        = var.enable_oidc_api ? 1 : 0
  client_id                    = azuread_application.reportmate_api[0].client_id
  app_role_assignment_required = true # only assigned principals can obtain a token
  owners                       = [data.azuread_client_config.current.object_id]

  tags = ["ReportMate", "API", "OIDC"]
}

# Pre-authorize the Azure CLI on the delegated scope so operators can run
# `az account get-access-token --resource api://<client_id>` without a separate
# consent step.
resource "azuread_application_pre_authorized" "azure_cli" {
  count                 = var.enable_oidc_api ? 1 : 0
  application_object_id = azuread_application.reportmate_api[0].object_id
  authorized_app_id     = local.azure_cli_client_id
  permission_ids        = [local.oidc_scope_as_user_id]
}

# Role assignments: map Entra principals (users, groups, or service principals)
# to API scopes. Each var is a list of object ids, empty by default, so nothing
# is granted until ECU configures it.
resource "azuread_app_role_assignment" "api_readers" {
  count               = var.enable_oidc_api ? length(var.oidc_reader_principal_ids) : 0
  app_role_id         = local.oidc_role_read_id
  principal_object_id = var.oidc_reader_principal_ids[count.index]
  resource_object_id  = azuread_service_principal.reportmate_api[0].object_id
}

resource "azuread_app_role_assignment" "api_ingesters" {
  count               = var.enable_oidc_api ? length(var.oidc_ingest_principal_ids) : 0
  app_role_id         = local.oidc_role_ingest_id
  principal_object_id = var.oidc_ingest_principal_ids[count.index]
  resource_object_id  = azuread_service_principal.reportmate_api[0].object_id
}

resource "azuread_app_role_assignment" "api_admins" {
  count               = var.enable_oidc_api ? length(var.oidc_admin_principal_ids) : 0
  app_role_id         = local.oidc_role_admin_id
  principal_object_id = var.oidc_admin_principal_ids[count.index]
  resource_object_id  = azuread_service_principal.reportmate_api[0].object_id
}

# Store the API client id in Key Vault for reference / manual token minting.
resource "azurerm_key_vault_secret" "oidc_api_client_id" {
  count        = var.enable_oidc_api && var.enable_key_vault ? 1 : 0
  depends_on   = [time_sleep.wait_for_rbac]
  name         = "oidc-api-client-id"
  value        = azuread_application.reportmate_api[0].client_id
  key_vault_id = var.key_vault_id

  tags = var.tags
}
