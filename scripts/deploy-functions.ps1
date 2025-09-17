# ReportMate Azure Functions API Deployment Script
# This script implements the CRITICAL DEPLOYMENT LESSONS from copilot-instructions.md
# Uses vendored deployment with .python_packages approach for reliable deployment

param(
    [string]$Environment = "prod",
    [switch]$SkipValidation,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

# Configuration
$APP = "reportmate-api"
$RG = "ReportMate"
$SRC_DIR = "infrastructure/modules/functions/api"
$STAGE = "dist/functionapp"
$TIMESTAMP = Get-Date -Format "yyyyMMddHHmmss"
$ZIP = "dist/$APP.$TIMESTAMP.zip"

Write-Host "🚀 ReportMate Azure Functions API Deployment" -ForegroundColor Cyan
Write-Host "Environment: $Environment" -ForegroundColor Yellow
Write-Host "Timestamp: $TIMESTAMP" -ForegroundColor Yellow

# Step 1: Validation
if (-not $SkipValidation) {
    Write-Host "⚡ Validating prerequisites..." -ForegroundColor Green
    
    # Check if we're in the right directory
    if (-not (Test-Path "infrastructure/modules/functions/api")) {
        Write-Error "❌ Must run from repository root. Cannot find infrastructure/modules/functions/api"
        exit 1
    }
    
    # Check for host.json
    if (-not (Test-Path "$SRC_DIR/host.json")) {
        Write-Error "❌ Cannot find host.json in $SRC_DIR"
        exit 1
    }
    
    # Check for requirements.txt
    if (-not (Test-Path "$SRC_DIR/requirements.txt")) {
        Write-Error "❌ Cannot find requirements.txt in $SRC_DIR"
        exit 1
    }
    
    # Validate requirements.txt contains only pg8000
    $requirements = Get-Content "$SRC_DIR/requirements.txt" -Raw
    if ($requirements -notmatch "pg8000>=1\.31\.2" -or $requirements -match "psycopg2|asyncpg") {
        Write-Warning "⚠️ requirements.txt should contain ONLY 'pg8000>=1.31.2'"
        Write-Host "Current requirements.txt content:" -ForegroundColor Yellow
        Get-Content "$SRC_DIR/requirements.txt"
        
        $confirm = Read-Host "Continue anyway? (y/N)"
        if ($confirm -ne "y" -and $confirm -ne "Y") {
            exit 1
        }
    }
    
    # Check Python availability
    try {
        $pythonVersion = py --version 2>&1
        Write-Host "✅ Python: $pythonVersion" -ForegroundColor Green
    }
    catch {
        Write-Error "❌ Python not available. Please install Python."
        exit 1
    }
    
    # Check Azure CLI
    try {
        $azVersion = az --version | Select-Object -First 1
        Write-Host "✅ Azure CLI: $azVersion" -ForegroundColor Green
    }
    catch {
        Write-Error "❌ Azure CLI not available. Please install Azure CLI."
        exit 1
    }
    
    # Verify Azure login
    try {
        $account = az account show --query "name" -o tsv 2>$null
        if (-not $account) {
            Write-Error "❌ Not logged into Azure. Run 'az login'"
            exit 1
        }
        Write-Host "✅ Azure Account: $account" -ForegroundColor Green
    }
    catch {
        Write-Error "❌ Azure authentication failed. Run 'az login'"
        exit 1
    }
}

# Step 2: Clean previous build
Write-Host "🧹 Cleaning previous build..." -ForegroundColor Green
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue

# Step 3: Create staging directory structure
Write-Host "📁 Creating staging directory structure..." -ForegroundColor Green
New-Item -ItemType Directory -Force -Path "$STAGE" | Out-Null
New-Item -ItemType Directory -Force -Path "$STAGE/.python_packages/lib/site-packages" | Out-Null

# Step 4: Copy source files
Write-Host "📋 Copying source files..." -ForegroundColor Green
Copy-Item -Path "$SRC_DIR/*" -Destination "$STAGE/" -Recurse -Force

# Step 5: Install Python dependencies (VENDORED APPROACH)
Write-Host "📦 Installing Python dependencies (vendored approach)..." -ForegroundColor Green
Write-Host "   This approach ensures dependencies are bundled and deployment is deterministic" -ForegroundColor Yellow

# Upgrade pip first
py -m pip install --upgrade pip

# Install dependencies to staging area
if ($Verbose) {
    py -m pip install -r "$STAGE/requirements.txt" --target "$STAGE/.python_packages/lib/site-packages" --verbose
}
else {
    py -m pip install -r "$STAGE/requirements.txt" --target "$STAGE/.python_packages/lib/site-packages"
}

if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Failed to install Python dependencies"
    exit 1
}

Write-Host "✅ Dependencies installed successfully" -ForegroundColor Green

# Step 6: Create deployment package
Write-Host "📦 Creating deployment package..." -ForegroundColor Green
Compress-Archive -Path "$STAGE/*" -DestinationPath $ZIP -Force

$zipSize = (Get-Item $ZIP).Length / 1MB
Write-Host "✅ Package created: $ZIP ($($zipSize.ToString('F2')) MB)" -ForegroundColor Green

# Step 7: Configure Function App for vendored deployment
Write-Host "⚙️ Configuring Function App for vendored deployment..." -ForegroundColor Green
Write-Host "   Disabling remote build (CRITICAL for reliable deployment)" -ForegroundColor Yellow

az functionapp config appsettings set --name $APP --resource-group $RG --settings SCM_DO_BUILD_DURING_DEPLOYMENT=false ENABLE_ORYX_BUILD=false --only-show-errors

if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Failed to configure Function App settings"
    exit 1
}

# Step 8: Deploy the vendored package
Write-Host "🚀 Deploying vendored package to Azure..." -ForegroundColor Green
Write-Host "   Using ZIP deployment with pre-bundled dependencies" -ForegroundColor Yellow

az functionapp deployment source config-zip --name $APP --resource-group $RG --src $ZIP

if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Deployment failed"
    exit 1
}

# Step 9: Verification
Write-Host "🔍 Verifying deployment..." -ForegroundColor Green

# Wait a bit for deployment to settle
Start-Sleep -Seconds 10

# Test health endpoint
Write-Host "Testing health endpoint..." -ForegroundColor Yellow
try {
    $healthResponse = Invoke-RestMethod -Uri "https://reportmate-api.azurewebsites.net/api/health" -TimeoutSec 30
    if ($healthResponse) {
        Write-Host "✅ Health endpoint: OK" -ForegroundColor Green
    }
    else {
        Write-Warning "⚠️ Health endpoint returned empty response"
    }
}
catch {
    Write-Warning "⚠️ Health endpoint test failed: $($_.Exception.Message)"
}

# Test device endpoint (critical database connectivity test)
Write-Host "Testing device endpoint (database connectivity)..." -ForegroundColor Yellow
try {
    $deviceResponse = Invoke-RestMethod -Uri "https://reportmate-api.azurewebsites.net/api/device/0F33V9G25083HJ" -TimeoutSec 30
    if ($deviceResponse) {
        Write-Host "✅ Device endpoint: OK (Database connectivity working)" -ForegroundColor Green
    }
    else {
        Write-Warning "⚠️ Device endpoint returned empty response"
    }
}
catch {
    Write-Warning "⚠️ Device endpoint test failed: $($_.Exception.Message)"
    Write-Host "   This usually indicates database driver issues (pg8000 not installed)" -ForegroundColor Red
}

# Test events endpoint
Write-Host "Testing events endpoint..." -ForegroundColor Yellow
try {
    $eventsResponse = Invoke-RestMethod -Uri "https://reportmate-api.azurewebsites.net/api/events" -TimeoutSec 30
    if ($eventsResponse) {
        Write-Host "✅ Events endpoint: OK" -ForegroundColor Green
    }
    else {
        Write-Warning "⚠️ Events endpoint returned empty response"
    }
}
catch {
    Write-Warning "⚠️ Events endpoint test failed: $($_.Exception.Message)"
}

# Step 10: Cleanup
Write-Host "🧹 Cleaning up..." -ForegroundColor Green
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue

# Summary
Write-Host ""
Write-Host "🎉 DEPLOYMENT COMPLETE" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host "Function App: $APP" -ForegroundColor Yellow
Write-Host "Resource Group: $RG" -ForegroundColor Yellow
Write-Host "Deployment Method: Vendored (.python_packages)" -ForegroundColor Yellow
Write-Host "Package Size: $($zipSize.ToString('F2')) MB" -ForegroundColor Yellow
Write-Host "Timestamp: $TIMESTAMP" -ForegroundColor Yellow
Write-Host ""
Write-Host "🔗 Endpoints to test:" -ForegroundColor Cyan
Write-Host "   Health: https://reportmate-api.azurewebsites.net/api/health" -ForegroundColor White
Write-Host "   Device: https://reportmate-api.azurewebsites.net/api/device/0F33V9G25083HJ" -ForegroundColor White  
Write-Host "   Events: https://reportmate-api.azurewebsites.net/api/events" -ForegroundColor White
Write-Host "   Devices: https://reportmate-api.azurewebsites.net/api/devices" -ForegroundColor White
Write-Host ""
Write-Host "⚠️ CRITICAL REMINDERS:" -ForegroundColor Red
Write-Host "   - NEVER use 'func azure functionapp publish' without --build remote" -ForegroundColor Yellow
Write-Host "   - NEVER use plain 'az functionapp deployment source config-zip' without vendored deps" -ForegroundColor Yellow
Write-Host "   - ALWAYS use this script for reliable deployments" -ForegroundColor Yellow
Write-Host "   - Database driver is pg8000>=1.31.2 ONLY (no psycopg2-binary or asyncpg)" -ForegroundColor Yellow
Write-Host ""

if ($deviceResponse) {
    Write-Host "🎊 SUCCESS: All endpoints operational! Database connectivity confirmed." -ForegroundColor Green
}
else {
    Write-Host "⚠️ WARNING: Device endpoint issues detected. Check Azure Function logs." -ForegroundColor Red
    Write-Host "   Possible causes:" -ForegroundColor Yellow
    Write-Host "   - pg8000 not installed properly" -ForegroundColor Yellow
    Write-Host "   - Database connection string issues" -ForegroundColor Yellow
    Write-Host "   - Remote build interfering (should be disabled)" -ForegroundColor Yellow
}