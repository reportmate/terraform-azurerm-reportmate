# Deploy Azure Functions - ReportMate
# Packages dependencies into .python_packages and deploys with ZIP

param(
    [string]$APP = "reportmate-api",
    [string]$RG = "ReportMate",
    [string]$SRC_DIR = "api"
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting vendored deployment for $APP..." -ForegroundColor Green

# Setup variables
$STAGE = "dist/functionapp"
$TIMESTAMP = Get-Date -Format 'yyyyMMddHHmmss'
$ZIP = "dist/$APP.$TIMESTAMP.zip"

# Clean and create staging directory
Write-Host "📁 Setting up staging directory..." -ForegroundColor Yellow
Remove-Item -Path dist -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path "$STAGE/.python_packages/lib/site-packages" -Force | Out-Null

# Copy function app code
Write-Host "📋 Copying function app code..." -ForegroundColor Yellow
Copy-Item -Path "$SRC_DIR\*" -Destination "$STAGE\" -Recurse -Force

# Install dependencies to vendored location
Write-Host "📦 Installing dependencies to .python_packages..." -ForegroundColor Yellow
py -m pip install -r "$STAGE\requirements.txt" --target "$STAGE\.python_packages\lib\site-packages"

if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Package installation failed"
    exit 1
}

# Create deployment ZIP
Write-Host "🗜️  Creating deployment package..." -ForegroundColor Yellow
Push-Location "$STAGE"
try {
    Compress-Archive -Path "*" -DestinationPath "..\$($APP).$TIMESTAMP.zip" -Force
    Write-Host "✅ Created: $($APP).$TIMESTAMP.zip" -ForegroundColor Green
} finally {
    Pop-Location
}

# Ensure remote build is disabled (critical for vendored deps)
Write-Host "⚙️  Configuring function app settings..." -ForegroundColor Yellow
az functionapp config appsettings set --name $APP --resource-group $RG --settings SCM_DO_BUILD_DURING_DEPLOYMENT=false ENABLE_ORYX_BUILD=false --output none

# Deploy to Azure
Write-Host "🌩️  Deploying to Azure Functions..." -ForegroundColor Yellow
az functionapp deployment source config-zip --name $APP --resource-group $RG --src $ZIP

if ($LASTEXITCODE -eq 0) {
    Write-Host "🎉 Deployment completed successfully!" -ForegroundColor Green
    Write-Host "🔗 Test endpoints:" -ForegroundColor Cyan
    Write-Host "   Health: https://$APP.azurewebsites.net/api/health" -ForegroundColor Cyan  
    Write-Host "   Debug:  https://$APP.azurewebsites.net/api/debug" -ForegroundColor Cyan
    Write-Host "   Devices: https://$APP.azurewebsites.net/api/devices" -ForegroundColor Cyan
} else {
    Write-Error "❌ Deployment failed"
    exit 1
}

Write-Host "✨ Azure Functions deployment complete!" -ForegroundColor Green
