#!/usr/bin/env pwsh

<#
.SYNOPSIS
Add user as owner of ReportMate Azure AD application

.DESCRIPTION
This script adds the current user or specified user as an owner of the ReportMate 
Azure AD application, which grants permissions to manage the application.

.PARAMETER ApplicationId
The Application (Client) ID of the ReportMate Azure AD app registration

.PARAMETER UserPrincipalName
The User Principal Name (email) of the user to add as owner (optional, defaults to current user)

.PARAMETER CurrentUserObjectId
The Object ID of the current user (will be detected automatically)

.EXAMPLE
.\add-app-owner.ps1

.EXAMPLE
.\add-app-owner.ps1 -UserPrincipalName "admin@ecuad.ca"
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ApplicationId,
    
    [Parameter(Mandatory=$false)]
    [string]$UserPrincipalName,
    
    [Parameter(Mandatory=$false)]
    [string]$CurrentUserObjectId
)

$ErrorActionPreference = "Stop"

Write-Host "👑 ReportMate Application Owner Management" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Get current user info
Write-Host "Getting current user information..." -ForegroundColor Yellow
try {
    $currentUser = az ad signed-in-user show | ConvertFrom-Json
    $currentUserEmail = $currentUser.userPrincipalName
    $currentUserObjectId = $currentUser.id
    $currentUserDisplayName = $currentUser.displayName
    
    Write-Host "✅ Current user: $currentUserDisplayName ($currentUserEmail)" -ForegroundColor Green
    Write-Host "✅ User Object ID: $currentUserObjectId" -ForegroundColor Green
    
} catch {
    Write-Error "Failed to get current user information: $_"
}

# Get Application ID from Terraform if not provided
if (-not $ApplicationId) {
    Write-Host "Getting Application ID from Terraform output..." -ForegroundColor Yellow
    
    if (Test-Path "main.tf") {
        try {
            $ApplicationId = terraform output -raw auth_application_id 2>$null
            if ($ApplicationId) {
                Write-Host "✅ Found Application ID: $ApplicationId" -ForegroundColor Green
            }
        } catch {
            Write-Warning "Could not get Application ID from Terraform output"
        }
    }
    
    if (-not $ApplicationId) {
        $ApplicationId = "8e809e42-7949-45e0-bca6-57e34e3a4139"  # Default ReportMate App ID
        Write-Host "✅ Using default Application ID: $ApplicationId" -ForegroundColor Green
    }
}

# Determine target user
if (-not $UserPrincipalName) {
    $UserPrincipalName = $currentUserEmail
    $targetUserObjectId = $currentUserObjectId
    Write-Host "✅ Target user: Current user ($UserPrincipalName)" -ForegroundColor Green
} else {
    Write-Host "Getting target user information..." -ForegroundColor Yellow
    try {
        $targetUser = az ad user show --id $UserPrincipalName | ConvertFrom-Json
        $targetUserObjectId = $targetUser.id
        Write-Host "✅ Target user: $($targetUser.displayName) ($UserPrincipalName)" -ForegroundColor Green
        Write-Host "✅ Target Object ID: $targetUserObjectId" -ForegroundColor Green
    } catch {
        Write-Error "Could not find user: $UserPrincipalName"
    }
}

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  Application ID: $ApplicationId" -ForegroundColor White
Write-Host "  Target User: $UserPrincipalName" -ForegroundColor White
Write-Host "  User Object ID: $targetUserObjectId" -ForegroundColor White
Write-Host ""

# Check current owners
Write-Host "Checking current application owners..." -ForegroundColor Yellow
try {
    $app = az ad app show --id $ApplicationId | ConvertFrom-Json
    Write-Host "✅ Application found: $($app.displayName)" -ForegroundColor Green
    
    # Try to get owners
    try {
        $owners = az ad app owner list --id $ApplicationId | ConvertFrom-Json
        
        if ($owners -and $owners.Count -gt 0) {
            Write-Host "Current owners:" -ForegroundColor Cyan
            foreach ($owner in $owners) {
                $isCurrentUser = $owner.id -eq $targetUserObjectId
                $marker = if ($isCurrentUser) { " (YOU)" } else { "" }
                Write-Host "  - $($owner.displayName) ($($owner.userPrincipalName))$marker" -ForegroundColor White
            }
            
            # Check if user is already an owner
            $alreadyOwner = $owners | Where-Object { $_.id -eq $targetUserObjectId }
            if ($alreadyOwner) {
                Write-Host "✅ User is already an owner!" -ForegroundColor Green
                Write-Host ""
                Write-Host "The permission issue might be due to:" -ForegroundColor Yellow
                Write-Host "1. Conditional access policies requiring additional authentication" -ForegroundColor White
                Write-Host "2. Need for Application Administrator role for specific actions" -ForegroundColor White
                Write-Host "3. Tenant-level permission restrictions" -ForegroundColor White
                Write-Host ""
                Write-Host "Try refreshing your browser or re-authenticating to the Azure Portal." -ForegroundColor Cyan
                exit 0
            }
        } else {
            Write-Host "⚠️  No owners found or unable to list owners" -ForegroundColor Yellow
        }
    } catch {
        Write-Warning "Could not list current owners (this is normal if you don't have permissions yet)"
    }
    
} catch {
    Write-Error "Application not found or access denied: $_"
}

# Add user as owner
Write-Host "Adding user as application owner..." -ForegroundColor Yellow

try {
    # Method 1: Add owner using az ad app owner add
    Write-Host "Attempting to add owner..." -ForegroundColor Yellow
    
    az ad app owner add --id $ApplicationId --owner-object-id $targetUserObjectId
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Successfully added user as application owner!" -ForegroundColor Green
    } else {
        throw "Failed to add owner using Azure CLI"
    }
    
} catch {
    Write-Warning "Failed to add owner via Azure CLI: $_"
    Write-Host ""
    Write-Host "Manual steps to add application owner:" -ForegroundColor Yellow
    Write-Host "1. Open Azure Portal: https://portal.azure.com" -ForegroundColor White
    Write-Host "2. Go to Azure Active Directory > App registrations" -ForegroundColor White
    Write-Host "3. Find 'ReportMate' application (ID: $ApplicationId)" -ForegroundColor White
    Write-Host "4. Go to 'Owners' in the left menu" -ForegroundColor White
    Write-Host "5. Click 'Add owners'" -ForegroundColor White
    Write-Host "6. Search for and add: $UserPrincipalName" -ForegroundColor White
    Write-Host ""
    Write-Host "Alternative: Ask your Global Administrator to run:" -ForegroundColor Yellow
    Write-Host "az ad app owner add --id $ApplicationId --owner-object-id $targetUserObjectId" -ForegroundColor Cyan
    
    exit 1
}

# Verify ownership
Write-Host ""
Write-Host "Verifying ownership..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

try {
    $owners = az ad app owner list --id $ApplicationId | ConvertFrom-Json
    $isOwner = $owners | Where-Object { $_.id -eq $targetUserObjectId }
    
    if ($isOwner) {
        Write-Host "✅ Ownership verified successfully!" -ForegroundColor Green
        Write-Host "✅ User $UserPrincipalName is now an owner of the ReportMate application" -ForegroundColor Green
    } else {
        Write-Warning "Ownership could not be verified immediately. Changes may take a few minutes to propagate."
    }
    
} catch {
    Write-Warning "Could not verify ownership status"
}

Write-Host ""
Write-Host "🎉 Application Ownership Process Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Refresh your browser and re-open the Azure Portal" -ForegroundColor White
Write-Host "2. Navigate back to the ReportMate application" -ForegroundColor White
Write-Host "3. You should now have full management permissions" -ForegroundColor White
Write-Host "4. If issues persist, you may need Application Administrator role" -ForegroundColor White
Write-Host ""

# Provide direct link
Write-Host "Direct link to ReportMate application in Azure Portal:" -ForegroundColor Cyan
$portalUrl = "https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Overview/appId/$ApplicationId"
Write-Host $portalUrl -ForegroundColor Blue
Write-Host ""
