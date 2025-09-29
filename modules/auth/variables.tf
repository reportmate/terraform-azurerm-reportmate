variable "app_display_name" {
  description = "Display name for the Entra ID application"
  type        = string
  default     = "ReportMate"
}

variable "app_identifier_uri" {
  description = "Identifier URI for the application"
  type        = string
  default     = "reportmate-web"
}

variable "homepage_url" {
  description = "Homepage URL for the application"
  type        = string
}

variable "logout_url" {
  description = "Logout URL for the application"
  type        = string
}

variable "redirect_uris" {
  description = "List of redirect URIs for OAuth flows"
  type        = list(string)
  default     = []
}

variable "sign_in_audience" {
  description = "Who can sign in to the application"
  type        = string
  default     = "AzureADMyOrg"
  validation {
    condition = contains([
      "AzureADMyOrg",
      "AzureADMultipleOrgs", 
      "AzureADandPersonalMicrosoftAccount",
      "PersonalMicrosoftAccount"
    ], var.sign_in_audience)
    error_message = "Sign in audience must be one of: AzureADMyOrg, AzureADMultipleOrgs, AzureADandPersonalMicrosoftAccount, PersonalMicrosoftAccount."
  }
}

variable "app_role_assignment_required" {
  description = "Whether users must be assigned to the app to access it"
  type        = bool
  default     = true
}

variable "client_secret_expiry" {
  description = "Expiry date for the client secret (RFC3339 format)"
  type        = string
  default     = null # Will default to 2 years from creation
}

variable "grant_admin_consent" {
  description = "Whether to automatically grant admin consent for required permissions"
  type        = bool
  default     = false
}

variable "app_owners" {
  description = "List of additional owner email addresses for the Entra ID application"
  type        = list(string)
  default     = []
}

variable "enable_key_vault" {
  description = "Whether to store secrets in Key Vault"
  type        = bool
  default     = false
}

variable "key_vault_id" {
  description = "ID of the Key Vault to store secrets in (optional)"
  type        = string
  default     = null
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "azuread_tags" {
  description = "Tags for Entra ID resources (as list of strings)"
  type        = list(string)
  default     = ["ReportMate", "Authentication"]
}

variable "app_roles" {
  description = "Application roles to create"
  type = list(object({
    allowed_member_types = list(string)
    description          = string
    display_name         = string
    enabled              = bool
    id                   = string
    value                = string
  }))
  default = [
    {
      allowed_member_types = ["User"]
      description          = "ReportMate User - General access to the application"
      display_name         = "User"
      enabled              = true
      id                   = "0e0e0e0e-1111-2222-3333-444444444444"
      value                = "user"
    },
    {
      allowed_member_types = ["User"]
      description          = "ReportMate Administrator - Full access to all features"
      display_name         = "Administrator"
      enabled              = true
      id                   = "1b19509b-32b1-4e9f-b71d-4dc9cd1d4c1e"
      value                = "admin"
    },
    {
      allowed_member_types = ["User"]
      description          = "ReportMate Faculty - Access to view and manage devices in their scope"
      display_name         = "Faculty"
      enabled              = true
      id                   = "2c29610c-43c2-5f0f-c82e-5ed9de2e5d2f"
      value                = "faculty"
    },
    {
      allowed_member_types = ["User"]
      description          = "ReportMate Staff - Access to view device information"
      display_name         = "Staff"
      enabled              = true
      id                   = "3d39721d-54d3-6010-d93f-6fe0ef3f6e30"
      value                = "staff"
    },
    {
      allowed_member_types = ["User"]
      description          = "ReportMate Student - Limited access to view personal device information"
      display_name         = "Student"
      enabled              = true
      id                   = "4e4a832e-65e4-7121-ea40-70f1f04f7f41"
      value                = "student"
    }
  ]
}

variable "allowed_domains" {
  description = "List of allowed email domains for authentication"
  type        = list(string)
  default     = ["example.com"]
}

variable "require_email_verification" {
  description = "Whether to require email verification for certain providers"
  type        = bool
  default     = false
}

variable "auth_providers" {
  description = "List of enabled authentication providers"
  type        = list(string)
  default     = ["azure-ad"]
  validation {
    condition = alltrue([
      for provider in var.auth_providers : contains([
        "azure-ad",
        "google", 
        "credentials"
      ], provider)
    ])
    error_message = "Auth providers must be one of: azure-ad, google, credentials."
  }
}

variable "default_auth_provider" {
  description = "Default authentication provider"
  type        = string
  default     = "azure-ad"
}

variable "authorized_groups" {
  description = "List of Entra ID group IDs that are authorized to sign in to the application"
  type        = list(string)
  default     = []
}
