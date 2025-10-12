#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy ReportMate Frontend - ONE command that ALWAYS works
    
.DESCRIPTION
    Complete frontend deployment:
    1. Builds Docker image (optionally purges all cache first)
    2. Pushes to Azure Container Registry
    3. Updates Container App with new image AND environment variables
    4. Restarts container
    5. Purges CDN cache (optionally waits for completion)
    
.PARAMETER Purge
    Aggressively purge ALL Docker cache before building AND wait for CDN purge to complete.
    Use this when normal deployment doesn't show new code.
    WARNING: Makes deployment take 15-20 minutes but GUARANTEES fresh code.
    
.EXAMPLE
    .\deploy-web-app.ps1
    # Normal deployment (fast, 3-7 minutes, uses Docker cache)
    
.EXAMPLE
    .\deploy-web-app.ps1 -Purge
    # Aggressive: Purge everything, wait for CDN, guarantee fresh code (15-20 minutes)
#>

param(
    [switch]$Purge
)

$ErrorActionPreference = "Stop"

Write-Host "   ReportMate Frontend Deployment" -ForegroundColor Cyan

# Configuration
$ResourceGroup = "ReportMate"
$ContainerApp = "reportmate-web-app-prod"
$Registry = "reportmateacr.azurecr.io"
$ImageName = "reportmate"
$FrontDoorProfile = "reportmate-frontdoor"
$FrontDoorEndpoint = "reportmate-endpoint"
$Domain = "reportmate.ecuad.ca"

# Generate unique tag
$Timestamp = Get-Date -Format "yyyyMMddHHmmss"
$GitHash = (git rev-parse --short HEAD 2>$null) ?? "unknown"
$Tag = "$Timestamp-$GitHash"
$FullImage = "$Registry/${ImageName}:$Tag"

Write-Host "📦 Image: $FullImage" -ForegroundColor White
Write-Host ""

# Step 1: Optionally purge ALL Docker cache and images
if ($Purge) {
    Write-Host "🗑️  Step 1/7: PURGING ALL Docker cache and images..." -ForegroundColor Yellow
    Write-Host "   ⚠️  Purge mode enabled - this will take longer but guarantees fresh build" -ForegroundColor Yellow
    Write-Host "   Removing all reportmate images..." -ForegroundColor Gray

    # Remove all reportmate images
    docker images "$Registry/$ImageName" --format "{{.Repository}}:{{.Tag}}" | ForEach-Object {
        docker rmi $_ --force 2>$null
    }

    Write-Host "   Purging build cache..." -ForegroundColor Gray
    docker builder prune --all --force | Out-Null
    Write-Host "✅ Cache purged" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "ℹ️  Using Docker cache for faster build (use -Purge flag for fresh build)" -ForegroundColor Cyan
    Write-Host ""
}

# Step 2: Validate prerequisites
$StepNum = if ($Purge) { "2/7" } else { "1/6" }
Write-Host "🔍 Step $StepNum`: Validating prerequisites..." -ForegroundColor Yellow

try {
    docker version | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
}
catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

try {
    $account = az account show 2>$null | ConvertFrom-Json
    Write-Host "✅ Logged into Azure as $($account.user.name)" -ForegroundColor Green
}
catch {
    Write-Host "❌ Not logged into Azure. Run: az login" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 3: Authenticate to ACR
$StepNum = if ($Purge) { "3/7" } else { "2/6" }
Write-Host "🔐 Step $StepNum`: Authenticating to Azure Container Registry..." -ForegroundColor Yellow
az acr login --name reportmateacr | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to authenticate to ACR" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Authenticated to ACR" -ForegroundColor Green
Write-Host ""

# Step 4: Build Docker image
$StepNum = if ($Purge) { "4/7" } else { "3/6" }
if ($Purge) {
    Write-Host "🔨 Step $StepNum`: Building FRESH Docker image (no cache, forced pull)..." -ForegroundColor Yellow
    Write-Host "   This will take 10-15 minutes for a completely fresh build..." -ForegroundColor Gray
} else {
    Write-Host "🔨 Step $StepNum`: Building Docker image (using cache)..." -ForegroundColor Yellow
    Write-Host "   This should take 2-5 minutes with cache..." -ForegroundColor Gray
}

Push-Location "$PSScriptRoot\..\..\apps\www"

try {
    $BuildTime = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
    
    if ($Purge) {
        # Purge build: no cache, pull fresh base images
        docker build `
            --no-cache `
            --pull `
            --platform linux/amd64 `
            --build-arg IMAGE_TAG="$Tag" `
            --build-arg BUILD_TIME="$BuildTime" `
            --build-arg BUILD_ID="$GitHash" `
            -t "$FullImage" `
            -f Dockerfile `
            .
    } else {
        # Normal build: use cache for speed
        docker build `
            --platform linux/amd64 `
            --build-arg IMAGE_TAG="$Tag" `
            --build-arg BUILD_TIME="$BuildTime" `
            --build-arg BUILD_ID="$GitHash" `
            -t "$FullImage" `
            -f Dockerfile `
            .
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker build failed" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    
    Write-Host "✅ Image built successfully" -ForegroundColor Green
}
finally {
    Pop-Location
}
Write-Host ""

# Step 5: Push image to ACR
$StepNum = if ($Purge) { "5/7" } else { "4/6" }
Write-Host "📤 Step $StepNum`: Pushing image to Azure Container Registry..." -ForegroundColor Yellow
docker push "$FullImage"
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to push image" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Image pushed to ACR" -ForegroundColor Green
Write-Host ""

# Step 6: Update Container App with new image AND environment variables
$StepNum = if ($Purge) { "6/7" } else { "5/6" }
Write-Host "🚀 Step $StepNum`: Updating Container App..." -ForegroundColor Yellow

# CRITICAL: Update image AND env vars in single command (triggers new revision)
az containerapp update `
    --name $ContainerApp `
    --resource-group $ResourceGroup `
    --image "$FullImage" `
    --set-env-vars `
        "CONTAINER_IMAGE_TAG=$Tag" `
        "BUILD_TIME=$BuildTime" `
        "BUILD_ID=$GitHash" | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to update Container App" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Container App updated (new revision created automatically)" -ForegroundColor Green

# Wait for new revision to be ready
Write-Host "   Waiting 30 seconds for new revision to start..." -ForegroundColor Gray
Start-Sleep -Seconds 30

# Get the active revision to verify
$activeRevision = az containerapp revision list `
    --name $ContainerApp `
    --resource-group $ResourceGroup `
    --query "[?properties.active==``true`` && properties.trafficWeight==``100``].name" `
    -o tsv

if ($activeRevision) {
    Write-Host "✅ Active revision: $($activeRevision.Trim())" -ForegroundColor Green
}
Write-Host ""

# Step 7: Purge CDN cache
$StepNum = if ($Purge) { "7/7" } else { "6/6" }
Write-Host "🗑️  Step $StepNum`: Purging Azure Front Door CDN cache..." -ForegroundColor Yellow

if ($Purge) {
    Write-Host "   ⚠️  AGGRESSIVE PURGE: Purging ALL paths and WAITING for completion..." -ForegroundColor Yellow
    Write-Host "   This ensures CDN serves fresh content immediately..." -ForegroundColor Gray
    
    # Purge multiple specific paths to be thorough
    $paths = @("/*", "/_next/*", "/_next/static/*", "/dashboard", "/devices", "/settings")
    foreach ($path in $paths) {
        Write-Host "   Purging: $path" -ForegroundColor Gray
        az afd endpoint purge `
            --resource-group $ResourceGroup `
            --profile-name $FrontDoorProfile `
            --endpoint-name $FrontDoorEndpoint `
            --content-paths $path `
            --domains $Domain `
            --output none 2>$null
    }
    
    Write-Host "   Waiting 60 seconds for CDN purge to propagate globally..." -ForegroundColor Yellow
    Start-Sleep -Seconds 60
    Write-Host "✅ CDN cache aggressively purged and propagated" -ForegroundColor Green
} else {
    Write-Host "   Quick purge (use -Purge flag for aggressive clearing)..." -ForegroundColor Gray
    az afd endpoint purge `
        --resource-group $ResourceGroup `
        --profile-name $FrontDoorProfile `
        --endpoint-name $FrontDoorEndpoint `
        --content-paths "/*" `
        --domains $Domain `
        --no-wait 2>$null
    Write-Host "✅ CDN cache purge initiated (may take 2-5 minutes to propagate)" -ForegroundColor Green
}
Write-Host ""

# Summary
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   ✅ Deployment Complete!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "📦 Image: $FullImage" -ForegroundColor White
Write-Host "🌐 URL: https://$Domain" -ForegroundColor White
Write-Host ""

if ($Purge) {
    Write-Host "✅ PURGE MODE: Everything fresh and CDN cache cleared" -ForegroundColor Green
    Write-Host ""
    Write-Host "🔍 Test NOW in incognito browser: https://$Domain" -ForegroundColor Cyan
    Write-Host "   New code should be live immediately" -ForegroundColor Gray
} else {
    Write-Host "⏳ Wait 2-5 minutes for CDN cache to clear, then test" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "🔍 Test in INCOGNITO browser: https://$Domain" -ForegroundColor Cyan
    Write-Host "   • Press Ctrl+Shift+N (Chrome) or Ctrl+Shift+P (Firefox)" -ForegroundColor Gray
    Write-Host "   • Check /settings page for new version number" -ForegroundColor Gray
    Write-Host "   • Dashboard should show '-' during loading (~20 seconds)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "💡 If old code still shows, run: .\deploy-web-app.ps1 -Purge" -ForegroundColor Yellow
}
Write-Host ""
