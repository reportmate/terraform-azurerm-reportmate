#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Restores local environment files from Azure Key Vault secrets.
    Use this script when setting up ReportMate on a new machine.

.DESCRIPTION
    This script retrieves all secrets from the ReportMate Key Vault and generates:
    - apps/www/.env.local (for local Next.js development - highest priority)
    - apps/www/.env.development (for Next.js development mode)
    - infrastructure/terraform.tfvars (for Terraform deployments)
    
.PARAMETER VaultName
    The name of the Azure Key Vault. Default: reportmate-kv

.PARAMETER GenerateTfvars
    Also generate terraform.tfvars file. Default: $true

.PARAMETER GenerateEnvLocal
    Also generate .env.local file. Default: $true

.PARAMETER GenerateEnvDevelopment
    Also generate .env.development file. Default: $true

.PARAMETER Backup
    Create .bak backups of existing files before overwriting. Default: $false

.EXAMPLE
    .\setup-local-env.ps1
    
.EXAMPLE
    .\setup-local-env.ps1 -VaultName "reportmate-kv-dev"

.PARAMETER NoBackup
    Skip creating .bak backups of existing files. Default: backups are created automatically.

.EXAMPLE
    .\setup-local-env.ps1
    
.EXAMPLE
    .\setup-local-env.ps1 -VaultName "reportmate-kv-dev"

.EXAMPLE
    .\setup-local-env.ps1 -GenerateTfvars:$false

.EXAMPLE
    .\setup-local-env.ps1 -NoBackup
#>

param(
    [string]$VaultName = "reportmate-kv",
    [bool]$GenerateTfvars = $true,
    [bool]$GenerateEnvLocal = $true,
    [bool]$GenerateEnvDevelopment = $true,
    [switch]$NoBackup,
    [switch]$ShowSecrets
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }

# Backup helper function - automatically backs up existing files before overwriting
function Backup-FileIfExists {
    param([string]$FilePath)
    if (Test-Path $FilePath) {
        $backupPath = "$FilePath.bak"
        Copy-Item -Path $FilePath -Destination $backupPath -Force
        Write-Warn "Backed up existing file to: $backupPath"
        return $true
    }
    return $false
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Magenta
Write-Host " ReportMate Environment Restore Script" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Write-Host ""

# Check Azure CLI login
Write-Info "Checking Azure CLI authentication..."
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Err "Not logged into Azure CLI. Please run 'az login' first."
    exit 1
}
Write-Success "Logged in as: $($account.user.name) (Subscription: $($account.name))"

# Get script directory and repo root
$ScriptDir = $PSScriptRoot
$RepoRoot = Split-Path (Split-Path $ScriptDir -Parent) -Parent

Write-Info "Repository root: $RepoRoot"
Write-Info "Key Vault: $VaultName"
Write-Host ""

# Retrieve all secrets from Key Vault
Write-Info "Retrieving secrets from Key Vault..."

$secrets = @{}
$secretNames = @(
    "db-password",
    "postgres-server-name",
    "db-username",
    "db-name",
    "azure-ad-client-id",
    "azure-ad-tenant-id",
    "client-passphrase",
    "custom-domain-name",
    "nextauth-secret",
    "devops-group-object-id",
    "storage-connection-string",
    "webpubsub-connection-string",
    "appinsights-connection-string",
    "api-base-url",
    "frontend-url"
)

foreach ($name in $secretNames) {
    try {
        $value = az keyvault secret show --vault-name $VaultName --name $name --query value -o tsv 2>$null
        if ($value) {
            $secrets[$name] = $value
            if ($ShowSecrets) {
                Write-Success "Retrieved: $name = $value"
            } else {
                Write-Success "Retrieved: $name"
            }
        }
    } catch {
        Write-Warn "Secret not found: $name"
    }
}

Write-Host ""
Write-Info "Retrieved $($secrets.Count) secrets from Key Vault"
Write-Host ""

# Build DATABASE_URL
$dbPassword = $secrets["db-password"]
$dbServer = $secrets["postgres-server-name"]
$dbUser = $secrets["db-username"]
$dbName = $secrets["db-name"]

# URL encode the password for DATABASE_URL
$encodedPassword = [System.Uri]::EscapeDataString($dbPassword)
$databaseUrl = "postgresql://${dbUser}:${encodedPassword}@${dbServer}.postgres.database.azure.com:5432/${dbName}?sslmode=require"

# Get API URL (from Key Vault or default)
$apiBaseUrl = if ($secrets["api-base-url"]) { 
    $secrets["api-base-url"] 
} else { 
    "https://reportmate-functions-api.blackdune-79551938.canadacentral.azurecontainerapps.io" 
}

# Generate .env.local for Next.js
if ($GenerateEnvLocal) {
    Write-Info "Generating apps/www/.env.local..."
    
    $envLocalPath = Join-Path $RepoRoot "apps\www\.env.local"
    if (-not $NoBackup) { Backup-FileIfExists -FilePath $envLocalPath }
    $envLocalContent = @"
# =================================================================
# ReportMate Local Development Environment
# Auto-generated from Azure Key Vault on $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# Key Vault: $VaultName
# =================================================================

# Environment Settings
NEXT_PUBLIC_AUTO_SSO=false
NEXT_PUBLIC_ENVIRONMENT=development
NEXT_PUBLIC_DOMAIN=localhost:3000

# Backend API Configuration (FastAPI container)
API_BASE_URL=$apiBaseUrl
NEXT_PUBLIC_API_BASE_URL=$apiBaseUrl

# SignalR/WebPubSub Configuration
NEXT_PUBLIC_ENABLE_SIGNALR=true
NEXT_PUBLIC_WPS_URL=wss://reportmate-signalr.webpubsub.azure.com/client/hubs/fleet

# Database Configuration
DATABASE_URL=$databaseUrl

# API Authentication (for localhost testing against production FastAPI)
REPORTMATE_PASSPHRASE=$($secrets["client-passphrase"])

# NextAuth Configuration
NEXTAUTH_SECRET=$($secrets["nextauth-secret"])
NEXTAUTH_URL=http://localhost:3000

# Azure AD Authentication
AZURE_AD_CLIENT_ID=$($secrets["azure-ad-client-id"])
AZURE_AD_TENANT_ID=$($secrets["azure-ad-tenant-id"])
"@

    $envLocalContent | Out-File -FilePath $envLocalPath -Encoding utf8 -Force
    Write-Success "Created: $envLocalPath"
}

# Generate .env.development for Next.js development mode
if ($GenerateEnvDevelopment) {
    Write-Info "Generating apps/www/.env.development..."
    
    $envDevPath = Join-Path $RepoRoot "apps\www\.env.development"
    if (-not $NoBackup) { Backup-FileIfExists -FilePath $envDevPath }
    $envDevContent = @"
# =================================================================
# ReportMate Development Environment
# Auto-generated from Azure Key Vault on $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# Key Vault: $VaultName
# 
# This file is loaded when NODE_ENV=development (pnpm dev)
# .env.local takes priority over this file if both exist
# =================================================================

# Environment Settings
NODE_ENV=development
NEXT_PUBLIC_AUTO_SSO=false
NEXT_PUBLIC_ENVIRONMENT=development
NEXT_PUBLIC_DOMAIN=localhost:3000

# Backend API Configuration (FastAPI container)
API_BASE_URL=$apiBaseUrl
NEXT_PUBLIC_API_BASE_URL=$apiBaseUrl

# SignalR/WebPubSub Configuration
NEXT_PUBLIC_ENABLE_SIGNALR=true
NEXT_PUBLIC_WPS_URL=wss://reportmate-signalr.webpubsub.azure.com/client/hubs/fleet

# Database Configuration
DATABASE_URL=$databaseUrl

# API Authentication (for localhost testing against production FastAPI)
REPORTMATE_PASSPHRASE=$($secrets["client-passphrase"])

# NextAuth Configuration
NEXTAUTH_SECRET=$($secrets["nextauth-secret"])
NEXTAUTH_URL=http://localhost:3000

# Azure AD Authentication
AZURE_AD_CLIENT_ID=$($secrets["azure-ad-client-id"])
AZURE_AD_TENANT_ID=$($secrets["azure-ad-tenant-id"])
"@

    $envDevContent | Out-File -FilePath $envDevPath -Encoding utf8 -Force
    Write-Success "Created: $envDevPath"
}

# Generate terraform.tfvars
if ($GenerateTfvars) {
    Write-Info "Generating infrastructure/terraform.tfvars..."
    
    $tfvarsPath = Join-Path $RepoRoot "infrastructure\terraform.tfvars"
    if (-not $NoBackup) { Backup-FileIfExists -FilePath $tfvarsPath }
    $tfvarsContent = @"
# =================================================================
# ReportMate Infrastructure Configuration - Production Ready
# Auto-generated from Azure Key Vault on $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# Key Vault: $VaultName
# =================================================================

# =================================================================
# REQUIRED VARIABLES
# =================================================================

# Azure Configuration
resource_group_name = "ReportMate"
location           = "Canada Central"

# Database Configuration
db_password          = "$dbPassword"
postgres_server_name = "$dbServer"
db_username          = "$dbUser"
db_name              = "$dbName"

# =================================================================
# OPTIONAL VARIABLES - Production Settings
# =================================================================

# Environment Configuration
environment = "prod"
deploy_dev  = false
deploy_prod = true

# API Container Configuration
frontend_image_tag = "latest"
api_image_tag      = "latest"

# Custom Domain Configuration
enable_custom_domain = true
custom_domain_name   = "$($secrets["custom-domain-name"])"

# Container Configuration
container_image = "reportmateacr.azurecr.io/reportmate:latest"

# Client Authentication
client_passphrases    = "$($secrets["client-passphrase"])"
enable_machine_groups = true
enable_business_units = true

# Pipeline Configuration
enable_pipeline_permissions   = false
pipeline_service_principal_id = ""

# =================================================================
# AUTHENTICATION CONFIGURATION
# =================================================================

# Azure AD Authentication
azure_ad_client_id    = "$($secrets["azure-ad-client-id"])"
azure_ad_tenant_id    = "$($secrets["azure-ad-tenant-id"])"
auth_sign_in_audience = "AzureADMyOrg"
auth_providers        = ["azure-ad"]
default_auth_provider = "azure-ad"

# Security Settings
allowed_auth_domains        = ["ecuad.ca"]
require_email_verification  = false
auth_client_secret_expiry   = "2026-12-31T23:59:59Z"

# Secret Storage
enable_key_vault = true
key_vault_name   = "$VaultName"

# DevOps Group Access
devops_resource_infrasec_group_object_id = "$($secrets["devops-group-object-id"])"

# Tags
tags = {
  Environment = "production"
  Project     = "ReportMate"
  ManagedBy   = "Terraform"
  Owner       = "ECUAD-IT"
  LastUpdated = "$(Get-Date -Format "yyyy-MM-dd")"
}
"@

    $tfvarsContent | Out-File -FilePath $tfvarsPath -Encoding utf8 -Force
    Write-Success "Created: $tfvarsPath"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " Environment Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Info "Files generated:"
if ($GenerateEnvLocal) {
    Write-Host "  - apps/www/.env.local (highest priority)" -ForegroundColor White
}
if ($GenerateEnvDevelopment) {
    Write-Host "  - apps/www/.env.development (development mode)" -ForegroundColor White
}
if ($GenerateTfvars) {
    Write-Host "  - infrastructure/terraform.tfvars" -ForegroundColor White
}
Write-Host ""
Write-Info "Next.js env file priority (highest to lowest):"
Write-Host "  1. .env.local" -ForegroundColor Yellow
Write-Host "  2. .env.development (when NODE_ENV=development)" -ForegroundColor Yellow
Write-Host "  3. .env" -ForegroundColor Yellow
Write-Host ""
Write-Info "Next steps:"
Write-Host "  1. Review the generated files" -ForegroundColor White
Write-Host "  2. Update frontend_image_tag in terraform.tfvars to latest deployed tag" -ForegroundColor White
Write-Host "  3. Run 'cd apps/www && pnpm install && pnpm dev' to start development" -ForegroundColor White
Write-Host ""
