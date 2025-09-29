# Entra ID Application Information
output "application_id" {
  description = "The Application (Client) ID of the Entra ID app"
  value       = azuread_application.reportmate_web.client_id
}

output "application_object_id" {
  description = "The Object ID of the Entra ID application"
  value       = azuread_application.reportmate_web.object_id
}

output "service_principal_id" {
  description = "The Object ID of the service principal"
  value       = azuread_service_principal.reportmate_web.object_id
}

output "service_principal_application_id" {
  description = "The Application ID of the service principal"
  value       = azuread_service_principal.reportmate_web.client_id
}

# Tenant Information
output "tenant_id" {
  description = "The Entra ID Tenant ID"
  value       = data.azuread_client_config.current.tenant_id
}

# Authentication Configuration
output "client_secret_id" {
  description = "The ID of the client secret"
  value       = azuread_application_password.reportmate_web.key_id
}

output "client_secret_value" {
  description = "The client secret value (sensitive)"
  value       = azuread_application_password.reportmate_web.value
  sensitive   = true
}

output "nextauth_secret" {
  description = "Generated NextAuth secret (sensitive)"
  value       = random_password.nextauth_secret.result
  sensitive   = true
}

# Application URLs
output "application_homepage_url" {
  description = "The homepage URL of the application"
  value       = var.homepage_url
}

output "application_logout_url" {
  description = "The logout URL of the application"
  value       = var.logout_url
}

output "redirect_uris" {
  description = "List of configured redirect URIs"
  value       = var.redirect_uris
}

# Environment Variables for Application
output "environment_variables" {
  description = "Environment variables needed for the web application"
  value = {
    NEXTAUTH_SECRET           = random_password.nextauth_secret.result
    AZURE_AD_CLIENT_ID        = azuread_application.reportmate_web.client_id
    AZURE_AD_CLIENT_SECRET    = azuread_application_password.reportmate_web.value
    AZURE_AD_TENANT_ID        = data.azuread_client_config.current.tenant_id
    AUTH_PROVIDERS            = join(",", var.auth_providers)
    DEFAULT_AUTH_PROVIDER     = var.default_auth_provider
    ALLOWED_DOMAINS           = join(",", var.allowed_domains)
    REQUIRE_EMAIL_VERIFICATION = tostring(var.require_email_verification)
  }
  sensitive = true
}

# Key Vault Secret Names (if Key Vault is configured)
output "key_vault_secret_names" {
  description = "Names of secrets stored in Key Vault"
  value = var.key_vault_id != null ? {
    client_id     = "reportmate-auth-client-id"
    client_secret = "reportmate-auth-client-secret"
    tenant_id     = "reportmate-auth-tenant-id"
    nextauth_secret = "reportmate-nextauth-secret"
  } : null
}

# App Role Information
output "app_roles" {
  description = "Configured application roles"
  value = {
    for role in var.app_roles : role.value => {
      id           = role.id
      display_name = role.display_name
      description  = role.description
    }
  }
}

# OAuth Configuration Details
output "oauth_configuration" {
  description = "OAuth configuration details for documentation"
  value = {
    authorization_endpoint = "https://login.microsoftonline.com/${data.azuread_client_config.current.tenant_id}/oauth2/v2.0/authorize"
    token_endpoint        = "https://login.microsoftonline.com/${data.azuread_client_config.current.tenant_id}/oauth2/v2.0/token"
    userinfo_endpoint     = "https://graph.microsoft.com/oidc/userinfo"
    issuer               = "https://login.microsoftonline.com/${data.azuread_client_config.current.tenant_id}/v2.0"
    jwks_uri             = "https://login.microsoftonline.com/${data.azuread_client_config.current.tenant_id}/discovery/v2.0/keys"
  }
}

# Container App Environment Variables (formatted for az containerapp update)
output "container_app_env_vars" {
  description = "Environment variables formatted for Azure Container App"
  value = [
    {
      name  = "NEXTAUTH_SECRET"
      value = random_password.nextauth_secret.result
    },
    {
      name  = "AZURE_AD_CLIENT_ID"
      value = azuread_application.reportmate_web.client_id
    },
    {
      name  = "AZURE_AD_CLIENT_SECRET"
      value = azuread_application_password.reportmate_web.value
    },
    {
      name  = "AZURE_AD_TENANT_ID"
      value = data.azuread_client_config.current.tenant_id
    },
    {
      name  = "AUTH_PROVIDERS"
      value = join(",", var.auth_providers)
    },
    {
      name  = "DEFAULT_AUTH_PROVIDER"
      value = var.default_auth_provider
    },
    {
      name  = "ALLOWED_DOMAINS"
      value = join(",", var.allowed_domains)
    },
    {
      name  = "REQUIRE_EMAIL_VERIFICATION"
      value = tostring(var.require_email_verification)
    }
  ]
}

# Setup Instructions
output "setup_instructions" {
  description = "Instructions for completing the setup"
  value = <<-EOT
    
    Entra ID App Registration Created Successfully!
    
    Application Details:
    - Application ID: ${azuread_application.reportmate_web.client_id}
    - Tenant ID: ${data.azuread_client_config.current.tenant_id}
    - Display Name: ${var.app_display_name}
    
    Next Steps:
    1. Grant admin consent for API permissions in Azure Portal
    2. Assign users to application roles as needed
    3. Configure environment variables in your web application
    4. Test authentication flow
    
    Important URLs:
    - Homepage: ${var.homepage_url}
    - Sign-in: ${var.homepage_url}/auth/signin
    - Callback: ${var.redirect_uris[0]}
    
    App Roles Created:
    ${join("\n    ", [for role in var.app_roles : "- ${role.display_name} (${role.value}): ${role.description}"])}
    
  EOT
}
