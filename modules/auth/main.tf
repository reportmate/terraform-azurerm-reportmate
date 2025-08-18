# Azure AD App Registration for ReportMate Authentication
terraform {
  required_providers {
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.47"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.33"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9"
    }
  }
}

# Get current Azure AD configuration
data "azuread_client_config" "current" {}

# Get Microsoft Graph service principal for API permissions
data "azuread_service_principal" "microsoft_graph" {
  client_id = "00000003-0000-0000-c000-000000000000"
}

# Look up additional owners by email
data "azuread_users" "app_owners" {
  count                = length(var.app_owners) > 0 ? 1 : 0
  user_principal_names = var.app_owners
}

# Generate a random password for the application
resource "random_password" "app_secret" {
  length  = 32
  special = true
}

# Create the Azure AD Application
resource "azuread_application" "reportmate_web" {
  display_name     = var.app_display_name
  identifier_uris  = [] # Will be set after creation using application_id
  owners           = concat([data.azuread_client_config.current.object_id], length(var.app_owners) > 0 ? data.azuread_users.app_owners[0].object_ids : [])
  sign_in_audience = var.sign_in_audience

  # Web application configuration
  web {
    homepage_url  = var.homepage_url
    logout_url    = var.logout_url

    # Redirect URIs for OAuth flows
    redirect_uris = var.redirect_uris

    # Enable ID token issuance
    implicit_grant {
      access_token_issuance_enabled = false
      id_token_issuance_enabled     = true
    }
  }

  # Required resource access (Microsoft Graph permissions)
  required_resource_access {
    resource_app_id = "00000003-0000-0000-c000-000000000000" # Microsoft Graph

    # Delegated permissions
    resource_access {
      id   = "e1fe6dd8-ba31-4d61-89e7-88639da4683d" # User.Read
      type = "Scope"
    }

    resource_access {
      id   = "14dad69e-099b-42c9-810b-d002981feec1" # profile
      type = "Scope"
    }

    resource_access {
      id   = "64a6cdd6-aab1-4aaf-94b8-3cc8405e90d0" # email
      type = "Scope"
    }

    resource_access {
      id   = "37f7f235-527c-4136-accd-4a02d197296e" # openid
      type = "Scope"
    }
  }

  # Optional claims configuration
  optional_claims {
    id_token {
      name                  = "email"
      source                = null
      essential             = false
      additional_properties = []
    }

    id_token {
      name                  = "preferred_username"
      source                = null
      essential             = false
      additional_properties = []
    }

    id_token {
      name                  = "groups"
      source                = null
      essential             = false
      additional_properties = ["emit_as_roles"]
    }
  }

  # App roles for ReportMate
  dynamic "app_role" {
    for_each = var.app_roles
    content {
      allowed_member_types = app_role.value.allowed_member_types
      description          = app_role.value.description
      display_name         = app_role.value.display_name
      enabled              = app_role.value.enabled
      id                   = app_role.value.id
      value                = app_role.value.value
    }
  }

  tags = var.azuread_tags
}

# Update identifier URIs using the application ID (workaround for tenant policy)
resource "null_resource" "update_identifier_uris" {
  depends_on = [azuread_application.reportmate_web]
  
  provisioner "local-exec" {
    command     = "az ad app update --id ${azuread_application.reportmate_web.client_id} --identifier-uris api://${azuread_application.reportmate_web.client_id}"
    on_failure  = continue
  }
}

# Create a service principal for the application
resource "azuread_service_principal" "reportmate_web" {
  client_id                    = azuread_application.reportmate_web.client_id
  app_role_assignment_required = var.app_role_assignment_required
  owners                       = [data.azuread_client_config.current.object_id]

  tags = ["ReportMate", "Authentication"]
}

# Create application password (client secret)
resource "azuread_application_password" "reportmate_web" {
  application_id = azuread_application.reportmate_web.id
  display_name   = "ReportMate Web App Secret"
  end_date       = var.client_secret_expiry
}

# Optional: Grant admin consent for required permissions
resource "azuread_service_principal_delegated_permission_grant" "reportmate_web" {
  count                                = var.grant_admin_consent ? 1 : 0
  service_principal_object_id          = azuread_service_principal.reportmate_web.object_id
  resource_service_principal_object_id = data.azuread_service_principal.microsoft_graph.object_id
  claim_values                         = ["User.Read", "profile", "email", "openid"]
}
# Store secrets in Azure Key Vault
resource "azurerm_key_vault_secret" "app_client_id" {
  count        = var.enable_key_vault ? 1 : 0
  depends_on   = [time_sleep.wait_for_rbac]
  name         = "reportmate-auth-client-id"
  value        = azuread_application.reportmate_web.client_id
  key_vault_id = var.key_vault_id

  tags = var.tags
}

resource "azurerm_key_vault_secret" "app_client_secret" {
  count        = var.enable_key_vault ? 1 : 0
  depends_on   = [time_sleep.wait_for_rbac]
  name         = "reportmate-auth-client-secret"
  value        = azuread_application_password.reportmate_web.value
  key_vault_id = var.key_vault_id

  tags = var.tags
}

resource "azurerm_key_vault_secret" "app_tenant_id" {
  count        = var.enable_key_vault ? 1 : 0
  name         = "reportmate-auth-tenant-id"
  value        = data.azuread_client_config.current.tenant_id
  key_vault_id = var.key_vault_id

  tags = var.tags
}

# Generate NextAuth secret
resource "random_password" "nextauth_secret" {
  length  = 32
  special = true
}

# Wait for RBAC permissions to propagate
resource "time_sleep" "wait_for_rbac" {
  count           = var.enable_key_vault ? 1 : 0
  depends_on      = [var.key_vault_id]
  create_duration = "60s"
}

resource "azurerm_key_vault_secret" "nextauth_secret" {
  count        = var.enable_key_vault ? 1 : 0
  depends_on   = [time_sleep.wait_for_rbac]
  name         = "reportmate-nextauth-secret"
  value        = random_password.nextauth_secret.result
  key_vault_id = var.key_vault_id

  tags = var.tags
}

# Assign authorized groups to the application for sign-in access
# This assigns the group to the "User" role which allows general access
resource "azuread_app_role_assignment" "authorized_groups" {
  count               = length(var.authorized_groups)
  app_role_id         = "0e0e0e0e-1111-2222-3333-444444444444"
  principal_object_id = var.authorized_groups[count.index]
  resource_object_id  = azuread_service_principal.reportmate_web.object_id
}
