# Authentication Module

This Terraform module creates the Azure AD App Registration and authentication infrastructure for web applications.

## Features

- ✅ Azure AD App Registration with proper OAuth configuration
- ✅ Service Principal creation and management
- ✅ Client secret generation and rotation
- ✅ Role-based access control with predefined roles
- ✅ Key Vault integration for secret storage
- ✅ NextAuth secret generation
- ✅ Admin consent automation (optional)
- ✅ Proper redirect URI configuration

## Usage

### Basic Usage

```hcl
module "app_auth" {
  source = "./modules/auth"
  
  homepage_url = "https://your-app.example.com"
  logout_url   = "https://your-app.example.com/auth/signout"
  
  redirect_uris = [
    "https://your-app.example.com/api/auth/callback/azure-ad",
    "http://localhost:3000/api/auth/callback/azure-ad"  # For development
  ]
  
  environment = "production"
  key_vault_id = module.key_vault.id
  
  tags = ["MyApp", "Authentication", "Production"]
}
```

### Advanced Configuration

```hcl
module "app_auth" {
  source = "./modules/auth"
  
  # Application Configuration
  app_display_name     = "My Application"
  homepage_url         = "https://your-app.example.com"
  logout_url          = "https://your-app.example.com/auth/signout"
  sign_in_audience    = "AzureADMyOrg"
  
  # OAuth Configuration
  redirect_uris = [
    "https://your-app.example.com/api/auth/callback/azure-ad",
    "https://staging.your-app.example.com/api/auth/callback/azure-ad",
    "http://localhost:3000/api/auth/callback/azure-ad"
  ]
  
  # Security Settings
  app_role_assignment_required = true
  grant_admin_consent         = false  # Set to true for automated consent
  
  # Authentication Providers
  auth_providers        = ["azure-ad"]
  default_auth_provider = "azure-ad"
  allowed_domains      = ["your-domain.com"]
  require_email_verification = false
  
  # Secret Management
  key_vault_id = module.key_vault.id
  client_secret_expiry = "2026-12-31T23:59:59Z"
  
  # Environment and Tagging
  environment = "production"
  tags = ["MyApp", "Authentication", "Production"]
}
```

## App Roles

The module creates the following predefined roles:

| Role | Value | Description |
|------|-------|-------------|
| Administrator | `admin` | Full access to all features |
| Manager | `manager` | Access to view and manage resources in their scope |
| User | `user` | Access to view information |
| Viewer | `viewer` | Limited access to view basic information |

You can customize roles by providing the `app_roles` variable:

```hcl
app_roles = [
  {
    allowed_member_types = ["User"]
    description          = "Custom Role Description"
    display_name         = "Custom Role"
    enabled              = true
    id                   = "custom-uuid-here"
    value                = "custom-role"
  }
]
```

## Outputs

| Name | Description | Sensitive |
|------|-------------|-----------|
| `application_id` | Azure AD Application (Client) ID | No |
| `tenant_id` | Azure AD Tenant ID | No |
| `client_secret_value` | Client secret for authentication | Yes |
| `nextauth_secret` | Generated NextAuth secret | Yes |
| `environment_variables` | All environment variables for the web app | Yes |
| `setup_instructions` | Human-readable setup instructions | No |

## Environment Variables

After applying this module, use these outputs to configure your web application:

```bash
# From Terraform outputs
NEXTAUTH_SECRET=$(terraform output -raw nextauth_secret)
AZURE_AD_CLIENT_ID=$(terraform output -raw application_id)
AZURE_AD_CLIENT_SECRET=$(terraform output -raw client_secret_value)
AZURE_AD_TENANT_ID=$(terraform output -raw tenant_id)

# Static configuration
NEXTAUTH_URL=https://your-app.example.com
AUTH_PROVIDERS=azure-ad
DEFAULT_AUTH_PROVIDER=azure-ad
ALLOWED_DOMAINS=your-domain.com
REQUIRE_EMAIL_VERIFICATION=false
```

## Key Vault Integration

When `key_vault_id` is provided, the module stores all secrets in Azure Key Vault:

- `app-auth-client-id`
- `app-auth-client-secret` 
- `app-auth-tenant-id`
- `app-nextauth-secret`

## Post-Deployment Steps

1. **Grant Admin Consent** (if not automated):
   ```bash
   # Get the application ID from Terraform output
   APP_ID=$(terraform output -raw application_id)
   
   # Open Azure Portal to grant consent
   echo "Grant admin consent at:"
   echo "https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnApi/appId/$APP_ID"
   ```

2. **Assign Users to Roles**:
   - Go to Azure Portal > Azure Active Directory > Enterprise Applications
   - Find your application name
   - Go to Users and groups > Add user/group
   - Assign appropriate roles to users

3. **Test Authentication**:
   ```bash
   # Verify the redirect URI works
   curl -I https://your-app.example.com/api/auth/callback/azure-ad
   ```

## Security Considerations

- **Client Secret Rotation**: Set `client_secret_expiry` to rotate secrets regularly
- **Role Assignment**: Enable `app_role_assignment_required` to control access
- **Domain Restrictions**: Configure `allowed_domains` to limit access
- **Key Vault**: Use Key Vault for production secret storage
- **Admin Consent**: Manually grant consent in production for security

## Development vs Production

### Development
```hcl
module "reportmate_auth_dev" {
  source = "./modules/auth"
  
  app_display_name = "ReportMate (Dev)"
  homepage_url     = "http://localhost:3000"
  logout_url       = "http://localhost:3000/auth/signout"
  
  redirect_uris = [
    "http://localhost:3000/api/auth/callback/azure-ad"
  ]
  
  app_role_assignment_required = false  # Allow all users in dev
  grant_admin_consent         = true   # Auto-consent in dev
  environment                 = "dev"
}
```

### Production
```hcl
module "reportmate_auth_prod" {
  source = "./modules/auth"
  
  app_display_name = "ReportMate"
  homepage_url     = "https://reportmate.yourdomain.com"
  logout_url       = "https://reportmate.yourdomain.com/auth/signout"
  
  redirect_uris = [
    "https://reportmate.yourdomain.com/api/auth/callback/azure-ad"
  ]
  
  app_role_assignment_required = true   # Require role assignment
  grant_admin_consent         = false  # Manual consent for security
  key_vault_id               = module.key_vault.id
  environment                = "production"
}
```

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure your Terraform service principal has `Application.ReadWrite.All` permission
2. **Redirect URI Mismatch**: Verify redirect URIs match exactly between Terraform and your app
3. **Admin Consent Required**: Grant consent manually if `grant_admin_consent = false`

### Useful Commands

```bash
# View all outputs
terraform output

# Get sensitive values
terraform output -raw client_secret_value
terraform output -raw nextauth_secret

# View setup instructions
terraform output -raw setup_instructions
```

## Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.0 |
| azuread | ~> 2.47 |
| azurerm | ~> 3.0 |
| random | ~> 3.1 |

## Providers

| Name | Version |
|------|---------|
| azuread | ~> 2.47 |
| azurerm | ~> 3.0 |
| random | ~> 3.1 |
