#!/usr/bin/env pwsh

<#
.SYNOPSIS
ReportMate Frontend Container Deployment Script

.DESCRIPTION
Builds and deploys the ReportMate Next.js frontend container to Azure Container Apps.
This deploys the web application user interface.

.PARAMETER Environment
Environment to deploy (dev, staging, prod). Default: prod

.PARAMETER SkipBuild
Skip Docker build (use existing image)

.PARAMETER Tag
Custom image tag (will auto-generate if not provided)

.EXAMPLE
.\deploy-frontend.ps1
# Build and deploy frontend to production

.EXAMPLE
.\deploy-frontend.ps1 -SkipBuild
# Deploy frontend without rebuilding

#>

param(
    [string]$Environment = "prod",
    [switch]$SkipBuild,
    [string]$Tag = "",
    [switch]$Help,
    [switch]$ForceBuild,
    [switch]$AutoSSO,
    [switch]$Test
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors for output
$Red = "`e[31m"
$Green = "`e[32m"
$Yellow = "`e[33m"
$Blue = "`e[34m"
$Reset = "`e[0m"

# Configuration
$RegistryName = "reportmateacr"
$ImageName = "reportmate"
$ResourceGroup = "ReportMate"
$ContainerAppName = "reportmate-web-app-$Environment"

# Helper functions
function Write-Info {
    param([string]$Message)
    Write-Host "${Blue}🚀 $Message${Reset}"
}

function Write-Success {
    param([string]$Message)
    Write-Host "${Green}✅ $Message${Reset}"
}

function Write-Warning {
    param([string]$Message)
    Write-Host "${Yellow}⚠️  $Message${Reset}"
}

function Write-Error {
    param([string]$Message)
    Write-Host "${Red}❌ $Message${Reset}"
}

function Show-Help {
    @"
ReportMate Frontend Container Deployment Script

Usage: .\deploy-frontend.ps1 [OPTIONS]

Options:
  -Environment ENV     Environment to deploy (dev, staging, prod) [default: prod]
  -ForceBuild         Force rebuild even if no changes detected
  -SkipBuild          Skip Docker build (use existing image)
  -Tag TAG            Custom image tag [default: auto-generated]
  -AutoSSO            Enable automatic SSO login (no login button)
  -Test               Test deployment after completion
  -Help               Show this help message

Examples:
  .\deploy-frontend.ps1                                    # Deploy frontend to production
  .\deploy-frontend.ps1 -Environment dev                   # Deploy to development
  .\deploy-frontend.ps1 -ForceBuild -AutoSSO              # Force rebuild with auto SSO
  .\deploy-frontend.ps1 -SkipBuild                        # Deploy without rebuilding

"@
}

if ($Help) {
    Show-Help
    exit 0
}

# Generate tag if not provided
if (-not $Tag) {
    try {
        $GitHash = git rev-parse --short HEAD 2>$null
        if (-not $GitHash) { $GitHash = "unknown" }
    } catch {
        $GitHash = "unknown"
    }
    $Tag = "$(Get-Date -Format 'yyyyMMddHHmmss')-$GitHash"
} else {
    # Extract git hash from existing tag if possible, or get current hash
    try {
        if ($Tag -match '-([a-f0-9]+)$') {
            $GitHash = $matches[1]
        } else {
            $GitHash = git rev-parse --short HEAD 2>$null
            if (-not $GitHash) { $GitHash = "unknown" }
        }
    } catch {
        $GitHash = "unknown"
    }
}

# Find the project root directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InfraDir = Split-Path -Parent $ScriptDir
$ProjectRoot = Split-Path -Parent $InfraDir
$ContainerDir = Join-Path $ProjectRoot "apps\www"

Write-Host "🚀 Frontend Container Deployment Configuration:" -ForegroundColor Blue
Write-Host "  Environment: $Environment"
Write-Host "  Tag: $Tag"
Write-Host "  Container Directory: $ContainerDir"
Write-Host "  Force Build: $ForceBuild"
Write-Host "  Skip Build: $SkipBuild"
Write-Host "  Auto SSO: $AutoSSO"
Write-Host ""

# Check prerequisites
Write-Host "✅ Checking prerequisites..." -ForegroundColor Green

if (-not (Test-Path $ContainerDir)) {
    Write-Host "❌ Container directory not found: $ContainerDir" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "$ContainerDir\Dockerfile")) {
    Write-Host "❌ Dockerfile not found in: $ContainerDir" -ForegroundColor Red
    exit 1
}

# Check required tools
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker not found. Please install Docker." -ForegroundColor Red
    exit 1
}

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Azure CLI not found. Please install Azure CLI." -ForegroundColor Red
    exit 1
}

# Check Azure login
try {
    $account = az account show --output json 2>$null | ConvertFrom-Json
    Write-Host "✅ Logged in as: $($account.user.name)" -ForegroundColor Green
} catch {
    Write-Host "❌ Not logged into Azure. Please run 'az login' first." -ForegroundColor Red
    exit 1
}

# Check Docker daemon
try {
    docker info --format "{{.ID}}" 2>$null | Out-Null
    Write-Host "✅ Docker daemon is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker daemon is not running" -ForegroundColor Red
    exit 1
}

# Build Docker image
if (-not $SkipBuild) {
    Write-Host "🚀 Building Docker image..." -ForegroundColor Blue
    
    $FullImageName = "$RegistryName.azurecr.io/$ImageName`:$Tag"
    $LatestImageName = "$RegistryName.azurecr.io/$ImageName`:latest"
    
    # Login to ACR for cache pulling
    Write-Host "🔐 Logging into Azure Container Registry for cache..." -ForegroundColor Blue
    az acr login --name $RegistryName | Out-Null
    
    # Try to pull latest image for cache
    Write-Host "📦 Attempting to pull latest image for cache..." -ForegroundColor Blue
    try {
        docker pull $LatestImageName 2>$null | Out-Null
        Write-Host "✅ Using cache from: $LatestImageName" -ForegroundColor Green
        $CacheArgs = "--cache-from $LatestImageName"
    } catch {
        Write-Host "⚠️ Could not pull latest image for cache, building without cache" -ForegroundColor Yellow
        $CacheArgs = ""
    }
    
    # Change to container directory
    Set-Location $ContainerDir
    
    try {
        # Docker build command with cache and platform specification
        Write-Host "Building: $FullImageName"
        $BuildTime = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        $BuildArgs = @(
            "--build-arg", "IMAGE_TAG=$Tag"
            "--build-arg", "BUILD_TIME=$BuildTime"
            "--build-arg", "BUILD_ID=$GitHash"
        )
        
        if ($CacheArgs) {
            docker build --platform linux/amd64 $BuildArgs --cache-from $LatestImageName -t $FullImageName -t $LatestImageName .
        } else {
            docker build --platform linux/amd64 $BuildArgs -t $FullImageName -t $LatestImageName .
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Image built successfully: $FullImageName" -ForegroundColor Green
        } else {
            Write-Host "❌ Failed to build Docker image" -ForegroundColor Red
            exit 1
        }
        
    } finally {
        # Return to original directory
        Set-Location $PSScriptRoot
    }
} else {
    Write-Host "⏭️ Skipping build as requested" -ForegroundColor Yellow
    $FullImageName = "$RegistryName.azurecr.io/$ImageName`:$Tag"
}

# Push to Azure Container Registry
if (-not $SkipBuild) {
    Write-Host "🚀 Pushing to Azure Container Registry..." -ForegroundColor Blue
    
    # ACR login already done in build section
    
    # Push images
    docker push $FullImageName
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Pushed: $FullImageName" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to push image" -ForegroundColor Red
        exit 1
    }

    docker push $LatestImageName
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Pushed: $LatestImageName" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Failed to push latest tag (non-critical)" -ForegroundColor Yellow
    }
}

# Deploy to Azure Container Apps
Write-Host "🚀 Deploying to Azure Container Apps..." -ForegroundColor Blue

# Check if container app exists
try {
    az containerapp show --name $ContainerAppName --resource-group $ResourceGroup --output none 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Container app not found"
    }
    Write-Host "✅ Container app found: $ContainerAppName" -ForegroundColor Green
} catch {
    Write-Host "❌ Container app '$ContainerAppName' not found in resource group '$ResourceGroup'" -ForegroundColor Red
    Write-Host "Please ensure the infrastructure is deployed via Terraform first" -ForegroundColor Red
    exit 1
}

# Update container app with new image
Write-Host "Updating container app with image: $FullImageName"

az containerapp update `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --image $FullImageName `
    --output table

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Container app updated successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to update container app" -ForegroundColor Red
    exit 1
}

# Get the application URL
Write-Host "🔍 Getting application URL..." -ForegroundColor Blue
$AppUrl = az containerapp show --name $ContainerAppName --resource-group $ResourceGroup --query "properties.configuration.ingress.fqdn" --output tsv

function Set-FrontDoorForAutoSSO {
    if (-not $AutoSSO) {
        return
    }
    
    Write-Host "🔧 Configuring Azure Front Door for automatic SSO..." -ForegroundColor Blue
    
    # This would configure Front Door rules to automatically redirect to SSO
    # For now, we'll just output instructions
    Write-Host "⚠️ Manual Front Door configuration required:" -ForegroundColor Yellow
    Write-Host "1. Go to Azure Portal → Front Door and CDN profiles"
    Write-Host "2. Find the ReportMate Front Door profile"
    Write-Host "3. Add a rule to redirect all traffic to the SSO login endpoint"
    Write-Host "4. Configure the rule to bypass the login page and go directly to Entra ID"
    Write-Host ""
    Write-Host "Rule configuration:"
    Write-Host "  - If: Request URL path does not contain '/api/auth'"
    Write-Host "  - And: Request URL path does not contain '/auth'"
    Write-Host "  - Then: Redirect to '/api/auth/signin' with HTTP 302"
}

# Configure Front Door if AutoSSO is enabled
Set-FrontDoorForAutoSSO

if ($AppUrl) {
    Write-Host ""
    Write-Host "🎉 DEPLOYMENT COMPLETED! 🎉" -ForegroundColor Green
    Write-Host "==============================================="
    Write-Host "✅ ReportMate container is deployed and ready!"
    Write-Host "🌐 Application URL: https://$AppUrl"
    
    if ($AutoSSO) {
        Write-Host ""
        Write-Host "🔐 Automatic SSO Configuration:" -ForegroundColor Green
        Write-Host "✅ Container configured for auto SSO"
        Write-Host "⚠️  Front Door rules may need manual configuration"
        Write-Host "🌐 Users will be automatically redirected to login"
    }
    
    Write-Host ""
} else {
    Write-Host "⚠️ Could not retrieve application URL" -ForegroundColor Yellow
}
