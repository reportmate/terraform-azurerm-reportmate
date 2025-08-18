#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy ReportMate Authentication Infrastructure
    
.DESCRIPTION
    This script deploys the Azure AD App Registration and authentication infrastructure
    for ReportMate using Terraform. It handles the complete setup including secret
    management and configuration generation.
    
.PARAMETER Environment
    Target environment (dev, staging, prod)
    
.PARAMETER Domain
    Custom domain name for the application (e.g., reportmate.ecuad.ca)
    
.PARAMETER TenantId
    Azure AD Tenant ID (optional, will be detected automatically)
    
.PARAMETER SkipApproval
    Skip Terraform approval prompts (use with caution)
    
.EXAMPLE
    .\deploy-auth.ps1 -Environment prod -Domain reportmate.ecuad.ca
    
.EXAMPLE
    .\deploy-auth.ps1 -Environment dev -SkipApproval
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("dev", "staging", "prod")]
    [string]$Environment,
    
    [Parameter(Mandatory=$false)]
    [string]$Domain,
    
    [Parameter(Mandatory=$false)]
    [string]$TenantId,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipApproval
)

# Script configuration
$ErrorActionPreference = "Stop"
$VerbosePreference = "Continue"

Write-Host "🚀 ReportMate Authentication Infrastructure Deployment" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Validate prerequisites
Write-Host "📋 Checking Prerequisites..." -ForegroundColor Yellow

$hasAzCli = Get-Command az -ErrorAction SilentlyContinue
$hasTerraform = Get-Command terraform -ErrorAction SilentlyContinue

if (-not $hasAzCli) {
    Write-Error "Azure CLI is not installed. Please install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
}

if (-not $hasTerraform) {
    Write-Error "Terraform is not installed. Please install from: https://www.terraform.io/downloads.html"
}

Write-Host "  ✅ Azure CLI: Available" -ForegroundColor Green
Write-Host "  ✅ Terraform: Available" -ForegroundColor Green

# Check Azure login
Write-Host "🔐 Checking Azure Authentication..." -ForegroundColor Yellow
try {
    $accountInfo = az account show 2>$null | ConvertFrom-Json
    if (-not $accountInfo) {
        Write-Host "  ❌ Not logged in to Azure" -ForegroundColor Red
        Write-Host "  Please run: az login" -ForegroundColor Yellow
        exit 1
    }
    
    Write-Host "  ✅ Logged in as: $($accountInfo.user.name)" -ForegroundColor Green
    Write-Host "  ✅ Subscription: $($accountInfo.name)" -ForegroundColor Green
    
    if (-not $TenantId) {
        $TenantId = $accountInfo.tenantId
    }
    
} catch {
    Write-Error "Failed to check Azure authentication: $_"
}

# Set up environment-specific configuration
Write-Host "⚙️  Configuring Environment: $Environment" -ForegroundColor Yellow

$resourceGroup = "reportmate-$Environment-rg"
$location = "East US"

switch ($Environment) {
    "dev" {
        $authProviders = @("azure-ad", "credentials")
        $allowedDomains = @("ecuad.ca", "gmail.com")
        $enableKeyVault = $false
        $autoConsent = $true
        $requireRoleAssignment = $false
    }
    "staging" {
        $authProviders = @("azure-ad")
        $allowedDomains = @("ecuad.ca")
        $enableKeyVault = $true
        $autoConsent = $false
        $requireRoleAssignment = $true
    }
    "prod" {
        $authProviders = @("azure-ad")
        $allowedDomains = @("ecuad.ca")
        $enableKeyVault = $true
        $autoConsent = $false
        $requireRoleAssignment = $true
    }
}

# Create terraform.tfvars file
Write-Host "📝 Creating Terraform Configuration..." -ForegroundColor Yellow

$tfvarsContent = @"
# Auto-generated configuration for $Environment environment
# Generated on: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

# Required Configuration
resource_group_name = "$resourceGroup"
location           = "$location"
environment        = "$Environment"

# Database Configuration (placeholder)
db_password = "TempPassword123!"  # Will be prompted during deployment

# Authentication Configuration
auth_sign_in_audience       = "AzureADMyOrg"
auth_providers             = ["$($authProviders -join '", "')"]
default_auth_provider      = "azure-ad"
allowed_auth_domains       = ["$($allowedDomains -join '", "')"]
require_email_verification = false
enable_key_vault           = $($enableKeyVault.ToString().ToLower())

# Domain Configuration
enable_custom_domain = $($Domain -ne "")
custom_domain_name   = "$Domain"

# Security Settings
# These will be set based on environment in the module

# Tags
tags = {
  Environment = "$Environment"
  Project     = "ReportMate"
  ManagedBy   = "Terraform"
  DeployedBy  = "$($env:USERNAME)"
  DeployedAt  = "$(Get-Date -Format "yyyy-MM-dd")"
}
"@

$tfvarsPath = "terraform.tfvars"
$tfvarsContent | Out-File -FilePath $tfvarsPath -Encoding UTF8
Write-Host "  ✅ Created: $tfvarsPath" -ForegroundColor Green

# Initialize Terraform
Write-Host "🏗️  Initializing Terraform..." -ForegroundColor Yellow
try {
    terraform init
    Write-Host "  ✅ Terraform initialized successfully" -ForegroundColor Green
} catch {
    Write-Error "Failed to initialize Terraform: $_"
}

# Plan deployment
Write-Host "📋 Planning Deployment..." -ForegroundColor Yellow
try {
    if ($SkipApproval) {
        terraform plan -out=tfplan
    } else {
        terraform plan
    }
    Write-Host "  ✅ Terraform plan completed" -ForegroundColor Green
} catch {
    Write-Error "Failed to plan Terraform deployment: $_"
}

# Confirm deployment
if (-not $SkipApproval) {
    Write-Host ""
    $confirm = Read-Host "🚀 Deploy the authentication infrastructure? (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Host "❌ Deployment cancelled" -ForegroundColor Red
        exit 0
    }
}

# Apply deployment
Write-Host "🚀 Deploying Infrastructure..." -ForegroundColor Yellow
try {
    if ($SkipApproval) {
        terraform apply tfplan
    } else {
        terraform apply -auto-approve
    }
    Write-Host "  ✅ Infrastructure deployed successfully!" -ForegroundColor Green
} catch {
    Write-Error "Failed to deploy infrastructure: $_"
}

# Extract outputs
Write-Host "📤 Extracting Configuration..." -ForegroundColor Yellow

try {
    $authAppId = terraform output -raw auth_application_id
    $authTenantId = terraform output -raw auth_tenant_id
    $authSigninUrl = terraform output -raw auth_signin_url
    
    Write-Host ""
    Write-Host "🎉 Deployment Complete!" -ForegroundColor Green
    Write-Host "======================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Azure AD Application Details:" -ForegroundColor Cyan
    Write-Host "  Application ID: $authAppId" -ForegroundColor White
    Write-Host "  Tenant ID: $authTenantId" -ForegroundColor White
    Write-Host "  Sign-in URL: $authSigninUrl" -ForegroundColor White
    Write-Host ""
    
    # Show setup instructions
    $setupInstructions = terraform output -raw auth_setup_instructions
    Write-Host $setupInstructions -ForegroundColor Yellow
    
} catch {
    Write-Warning "Could not extract all outputs. Run 'terraform output' to see results."
}

# Generate environment file
Write-Host "📝 Generating Environment Configuration..." -ForegroundColor Yellow

try {
    $envVars = terraform output -json auth_environment_variables | ConvertFrom-Json
    
    $envContent = @"
# ReportMate Authentication Environment Variables
# Generated for $Environment environment on $(Get-Date)

# NextAuth Configuration
NEXTAUTH_SECRET=$($envVars.NEXTAUTH_SECRET)
NEXTAUTH_URL=$($Domain ? "https://$Domain" : "http://localhost:3000")

# Azure AD Configuration
AZURE_AD_CLIENT_ID=$($envVars.AZURE_AD_CLIENT_ID)
AZURE_AD_CLIENT_SECRET=$($envVars.AZURE_AD_CLIENT_SECRET)
AZURE_AD_TENANT_ID=$($envVars.AZURE_AD_TENANT_ID)

# Authentication Settings
AUTH_PROVIDERS=$($envVars.AUTH_PROVIDERS)
DEFAULT_AUTH_PROVIDER=$($envVars.DEFAULT_AUTH_PROVIDER)
ALLOWED_DOMAINS=$($envVars.ALLOWED_DOMAINS)
REQUIRE_EMAIL_VERIFICATION=$($envVars.REQUIRE_EMAIL_VERIFICATION)
"@

    $envFile = ".env.$Environment"
    $envContent | Out-File -FilePath $envFile -Encoding UTF8
    Write-Host "  ✅ Created: $envFile" -ForegroundColor Green
    
} catch {
    Write-Warning "Could not generate environment file. Extract manually with: terraform output auth_environment_variables"
}

Write-Host ""
Write-Host "📚 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Grant admin consent in Azure Portal (if not automated)" -ForegroundColor White
Write-Host "2. Assign users to application roles" -ForegroundColor White
Write-Host "3. Copy environment variables to your web application" -ForegroundColor White
Write-Host "4. Test the authentication flow" -ForegroundColor White
Write-Host ""

if ($enableKeyVault) {
    Write-Host "🔑 Secrets are stored in Azure Key Vault for enhanced security" -ForegroundColor Green
    try {
        $keyVaultName = terraform output -raw key_vault_name
        Write-Host "Key Vault: $keyVaultName" -ForegroundColor White
    } catch {
        Write-Host "Key Vault name not available in outputs" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "✨ ReportMate Authentication Infrastructure is ready!" -ForegroundColor Green
