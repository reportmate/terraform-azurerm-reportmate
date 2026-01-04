#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Migrates Key Vault secrets from reportmate-* prefix to shorter names.
    
.DESCRIPTION
    This script performs a safe migration of Key Vault secrets:
    1. Copies secrets from old names to new names (keeping old ones)
    2. Updates container app secret references
    3. Optionally deletes old secrets after verification

.PARAMETER VaultName
    The name of the Azure Key Vault. Default: reportmate-kv

.PARAMETER DryRun
    If specified, only shows what would be done without making changes.

.PARAMETER DeleteOld
    If specified, deletes old secrets after migration. Use with caution!

.EXAMPLE
    .\migrate-secrets.ps1 -DryRun
    
.EXAMPLE
    .\migrate-secrets.ps1
    
.EXAMPLE
    .\migrate-secrets.ps1 -DeleteOld
#>

param(
    [string]$VaultName = "reportmate-kv",
    [switch]$DryRun,
    [switch]$DeleteOld
)

$ErrorActionPreference = "Stop"

function Write-Success { param($msg) Write-Host "[SUCCESS] $msg" -ForegroundColor Green }
function Write-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "========================================" -ForegroundColor Magenta
Write-Host " Key Vault Secret Migration Script" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Write-Host ""

if ($DryRun) {
    Write-Warn "DRY RUN MODE - No changes will be made"
    Write-Host ""
}

# Secret mapping: old name -> new name
$secretMapping = @{
    "reportmate-db-password" = "db-password"
    "reportmate-postgres-server-name" = "postgres-server-name"
    "reportmate-db-username" = "db-username"
    "reportmate-db-name" = "db-name"
    "reportmate-azure-ad-client-id" = "azure-ad-client-id"
    "reportmate-azure-ad-tenant-id" = "azure-ad-tenant-id"
    "reportmate-client-passphrase" = "client-passphrase"
    "reportmate-devops-group-object-id" = "devops-group-object-id"
    "reportmate-custom-domain-name" = "custom-domain-name"
    "reportmate-nextauth-secret" = "nextauth-secret"
    "reportmate-storage-connection-string" = "storage-connection-string"
    "reportmate-webpubsub-connection-string" = "webpubsub-connection-string"
    "reportmate-appinsights-connection-string" = "appinsights-connection-string"
    "reportmate-auth-client-id" = "auth-client-id"
    "reportmate-auth-client-secret" = "auth-client-secret"
    "reportmate-auth-tenant-id" = "auth-tenant-id"
}

# Check Azure CLI login
Write-Info "Checking Azure CLI authentication..."
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Err "Not logged into Azure CLI. Please run 'az login' first."
    exit 1
}
Write-Success "Logged in as: $($account.user.name)"

# Step 1: Copy secrets to new names
Write-Host ""
Write-Info "Step 1: Copying secrets to new names..."
Write-Host ""

$copied = 0
$skipped = 0
$failed = 0

foreach ($oldName in $secretMapping.Keys) {
    $newName = $secretMapping[$oldName]
    
    # Check if old secret exists
    $oldSecret = az keyvault secret show --vault-name $VaultName --name $oldName 2>$null | ConvertFrom-Json
    if (-not $oldSecret) {
        Write-Warn "  Old secret not found: $oldName (skipping)"
        $skipped++
        continue
    }
    
    # Check if new secret already exists
    $newSecret = az keyvault secret show --vault-name $VaultName --name $newName 2>$null | ConvertFrom-Json
    if ($newSecret) {
        Write-Info "  New secret already exists: $newName (skipping)"
        $skipped++
        continue
    }
    
    if ($DryRun) {
        Write-Host "  [DRY RUN] Would copy: $oldName -> $newName" -ForegroundColor Yellow
        $copied++
    } else {
        try {
            # Get the secret value
            $secretValue = az keyvault secret show --vault-name $VaultName --name $oldName --query value -o tsv
            
            # Create new secret with same value
            az keyvault secret set --vault-name $VaultName --name $newName --value $secretValue | Out-Null
            Write-Success "  Copied: $oldName -> $newName"
            $copied++
        } catch {
            Write-Err "  Failed to copy: $oldName -> $newName"
            Write-Err "    Error: $_"
            $failed++
        }
    }
}

Write-Host ""
Write-Info "Step 1 Summary: Copied=$copied, Skipped=$skipped, Failed=$failed"

# Step 2: Update container app secret references (if not dry run)
Write-Host ""
Write-Info "Step 2: Container app secret references need manual update"
Write-Host ""
Write-Warn "The frontend container 'reportmate-web-app-prod' references:"
Write-Host "  - reportmate-nextauth-secret -> nextauth-secret"
Write-Host "  - reportmate-auth-client-secret -> auth-client-secret"
Write-Host ""
Write-Warn "After running this migration, redeploy the frontend container with:"
Write-Host "  cd infrastructure"
Write-Host "  .\scripts\deploy-containers.ps1 -Environment prod -ForceBuild"
Write-Host ""
Write-Info "The deploy script will use the new secret names from Terraform."

# Step 3: Delete old secrets (if requested)
if ($DeleteOld) {
    Write-Host ""
    Write-Warn "Step 3: Deleting old secrets..."
    Write-Host ""
    
    if ($DryRun) {
        foreach ($oldName in $secretMapping.Keys) {
            Write-Host "  [DRY RUN] Would delete: $oldName" -ForegroundColor Yellow
        }
    } else {
        $confirm = Read-Host "Are you sure you want to delete the old secrets? (yes/no)"
        if ($confirm -eq "yes") {
            foreach ($oldName in $secretMapping.Keys) {
                try {
                    az keyvault secret delete --vault-name $VaultName --name $oldName | Out-Null
                    Write-Success "  Deleted: $oldName"
                } catch {
                    Write-Err "  Failed to delete: $oldName"
                }
            }
        } else {
            Write-Info "Skipping deletion."
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " Migration Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Info "Next steps:"
Write-Host "  1. Verify new secrets exist in Key Vault"
Write-Host "  2. Redeploy frontend container to use new secret names"
Write-Host "  3. Test the application thoroughly"
Write-Host "  4. Run this script with -DeleteOld to remove old secrets"
Write-Host ""
