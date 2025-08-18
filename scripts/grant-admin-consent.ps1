#!/usr/bin/env pwsh

<#
.SYNOPSIS
Grant admin consent for ReportMate Azure AD application

.DESCRIPTION
This script grants admin consent for the ReportMate Azure AD application's API permissions.
It requires Global Administrator or Application Administrator privileges.

.PARAMETER ApplicationId
The Application (Client) ID of the ReportMate Azure AD app registration

.PARAMETER TenantId
The Azure AD Tenant ID (optional, will be detected automatically)

.PARAMETER Force
Force consent even if already granted

.EXAMPLE
.\grant-admin-consent.ps1 -ApplicationId "8e809e42-7949-45e0-bca6-57e34e3a4139"

.EXAMPLE
.\grant-admin-consent.ps1 -ApplicationId "8e809e42-7949-45e0-bca6-57e34e3a4139" -Force
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ApplicationId,
    
    [Parameter(Mandatory=$false)]
    [string]$TenantId,
    
    [Parameter(Mandatory=$false)]
    [switch]$Force
)

$ErrorActionPreference = "Stop"

Write-Host "🔐 ReportMate Admin Consent Grant" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Check if logged in to Azure
Write-Host "Checking Azure authentication..." -ForegroundColor Yellow
try {
    $account = az account show 2>$null | ConvertFrom-Json
    if (-not $account) {
        Write-Error "Not logged in to Azure. Please run 'az login' first."
    }
    
    Write-Host "✅ Logged in as: $($account.user.name)" -ForegroundColor Green
    Write-Host "✅ Subscription: $($account.name)" -ForegroundColor Green
    
    if (-not $TenantId) {
        $TenantId = $account.tenantId
    }
    Write-Host "✅ Tenant ID: $TenantId" -ForegroundColor Green
    
} catch {
    Write-Error "Failed to check Azure authentication: $_"
}

# Try to get Application ID from Terraform output if not provided
if (-not $ApplicationId) {
    Write-Host "Attempting to get Application ID from Terraform output..." -ForegroundColor Yellow
    
    # Check if we're in the right directory
    if (Test-Path "main.tf") {
        try {
            $ApplicationId = terraform output -raw auth_application_id 2>$null
            if ($ApplicationId) {
                Write-Host "✅ Found Application ID from Terraform: $ApplicationId" -ForegroundColor Green
            }
        } catch {
            Write-Warning "Could not get Application ID from Terraform output"
        }
    }
    
    if (-not $ApplicationId) {
        Write-Host "Application ID not found. Please provide it manually:" -ForegroundColor Yellow
        $ApplicationId = Read-Host "Enter the Application (Client) ID"
        
        if (-not $ApplicationId) {
            Write-Error "Application ID is required"
        }
    }
}

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  Application ID: $ApplicationId" -ForegroundColor White
Write-Host "  Tenant ID: $TenantId" -ForegroundColor White
Write-Host ""

# Check current consent status
Write-Host "Checking current consent status..." -ForegroundColor Yellow
try {
    $servicePrincipal = az ad sp show --id $ApplicationId 2>$null | ConvertFrom-Json
    
    if (-not $servicePrincipal) {
        Write-Warning "Service Principal not found. Creating one..."
        az ad sp create --id $ApplicationId | Out-Null
        $servicePrincipal = az ad sp show --id $ApplicationId | ConvertFrom-Json
    }
    
    $spObjectId = $servicePrincipal.id
    Write-Host "✅ Service Principal Object ID: $spObjectId" -ForegroundColor Green
    
    # Check for existing permissions
    $permissions = az ad app permission list --id $ApplicationId 2>$null | ConvertFrom-Json
    
    if ($permissions -and $permissions.Count -gt 0) {
        Write-Host "Current API permissions:" -ForegroundColor Cyan
        foreach ($permission in $permissions) {
            $status = if ($permission.consentType -eq "AllPrincipals") { "✅ Granted" } else { "⚠️  Requires consent" }
            Write-Host "  - $($permission.resourceDisplayName): $($permission.scope) ($status)" -ForegroundColor White
        }
    } else {
        Write-Host "No API permissions configured" -ForegroundColor Yellow
    }
    
} catch {
    Write-Warning "Could not check current consent status: $_"
}

# Check if user has admin privileges
Write-Host ""
Write-Host "Checking admin privileges..." -ForegroundColor Yellow
try {
    $userRoles = az rest --method GET --uri "https://graph.microsoft.com/v1.0/me/memberOf?\$filter=isAssignableToRole eq true" 2>$null | ConvertFrom-Json
    
    $isAdmin = $false
    $adminRoles = @("Global Administrator", "Application Administrator", "Cloud Application Administrator")
    
    if ($userRoles.value) {
        foreach ($role in $userRoles.value) {
            if ($role.displayName -in $adminRoles) {
                $isAdmin = $true
                Write-Host "✅ Admin role detected: $($role.displayName)" -ForegroundColor Green
                break
            }
        }
    }
    
    if (-not $isAdmin) {
        Write-Warning "Admin privileges not detected. You may need Global Administrator or Application Administrator role."
        Write-Host "Proceeding anyway - the command will fail if you don't have sufficient privileges." -ForegroundColor Yellow
    }
    
} catch {
    Write-Warning "Could not check admin privileges. Proceeding anyway."
}

# Grant admin consent
Write-Host ""
if (-not $Force) {
    $confirm = Read-Host "Grant admin consent for the ReportMate application? (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Host "❌ Admin consent cancelled" -ForegroundColor Red
        exit 0
    }
}

Write-Host "Granting admin consent..." -ForegroundColor Yellow

try {
    # Method 1: Try using az ad app permission admin-consent (preferred)
    Write-Host "Attempting admin consent via Azure CLI..." -ForegroundColor Yellow
    
    $result = az ad app permission admin-consent --id $ApplicationId 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Admin consent granted successfully!" -ForegroundColor Green
    } else {
        Write-Warning "Azure CLI method failed. Trying alternative method..."
        
        # Method 2: Direct Graph API call
        Write-Host "Attempting admin consent via Graph API..." -ForegroundColor Yellow
        
        # Get the Microsoft Graph service principal
        $graphSp = az ad sp list --filter "appId eq '00000003-0000-0000-c000-000000000000'" | ConvertFrom-Json
        $graphSpId = $graphSp[0].id
        
        # Grant consent for each required permission
        $consentBody = @{
            clientId = $spObjectId
            consentType = "AllPrincipals"
            resourceId = $graphSpId
            scope = "User.Read email openid profile"
        } | ConvertTo-Json
        
        $consentResult = az rest --method POST --uri "https://graph.microsoft.com/v1.0/oauth2PermissionGrants" --body $consentBody --headers "Content-Type=application/json" 2>$null
        
        if ($consentResult) {
            Write-Host "✅ Admin consent granted via Graph API!" -ForegroundColor Green
        } else {
            throw "Both admin consent methods failed"
        }
    }
    
} catch {
    Write-Error "Failed to grant admin consent: $_"
    Write-Host ""
    Write-Host "Manual consent options:" -ForegroundColor Yellow
    Write-Host "1. Open Azure Portal: https://portal.azure.com" -ForegroundColor White
    Write-Host "2. Go to Azure Active Directory > App registrations" -ForegroundColor White
    Write-Host "3. Find the ReportMate application (ID: $ApplicationId)" -ForegroundColor White
    Write-Host "4. Go to API permissions" -ForegroundColor White
    Write-Host "5. Click 'Grant admin consent for [Your Organization]'" -ForegroundColor White
    Write-Host ""
    Write-Host "Or use the direct consent URL:" -ForegroundColor White
    Write-Host "https://login.microsoftonline.com/$TenantId/adminconsent?client_id=$ApplicationId" -ForegroundColor Cyan
    exit 1
}

# Verify consent was granted
Write-Host ""
Write-Host "Verifying admin consent..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

try {
    $permissions = az ad app permission list --id $ApplicationId | ConvertFrom-Json
    $allConsented = $true
    
    if ($permissions) {
        foreach ($permission in $permissions) {
            if ($permission.consentType -ne "AllPrincipals") {
                $allConsented = $false
                Write-Warning "Permission '$($permission.scope)' still requires consent"
            }
        }
        
        if ($allConsented) {
            Write-Host "✅ All permissions have been granted admin consent!" -ForegroundColor Green
        } else {
            Write-Warning "Some permissions may still require manual consent"
        }
    }
    
} catch {
    Write-Warning "Could not verify consent status"
}

Write-Host ""
Write-Host "🎉 Admin Consent Process Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Test user sign-in at: https://reportmate.ecuad.ca" -ForegroundColor White
Write-Host "2. Verify group membership access control" -ForegroundColor White
Write-Host "3. Monitor authentication logs in Azure Portal" -ForegroundColor White
Write-Host ""

# Generate direct consent URL for reference
$consentUrl = "https://login.microsoftonline.com/$TenantId/adminconsent?client_id=$ApplicationId"
Write-Host "Direct admin consent URL (for reference):" -ForegroundColor Cyan
Write-Host $consentUrl -ForegroundColor Blue
Write-Host ""
