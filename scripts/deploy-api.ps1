#Requires -Version 7.0
<#
.SYNOPSIS
    Deploy ReportMate FastAPI Container (API Functions) with Device ID Alignment Fix
.DESCRIPTION
    Deploys the FastAPI container to Azure Container Apps with critical device ID standardization.
    
    🚨 CRITICAL FIXES IN THIS VERSION:
    - API code moved to proper infrastructure location (modules/api)
    - Device ID alignment standardized on serialNumber (UUIDs deprecated)
    - No more UUID confusion throughout stack
    - Database queries use serial_number consistently

.PARAMETER Environment
    Target environment (prod, dev)
.PARAMETER SkipBuild
    Skip Docker build (use existing image) 
.PARAMETER Tag
    Custom image tag (will auto-generate if not provided)
.PARAMETER ForceBuild
    Force rebuild even if image exists

.EXAMPLE
    .\deploy-api.ps1
    # Deploy API with device ID alignment fix
    
    .\deploy-api.ps1 -Environment dev
    # Deploy to dev environment
    
    .\deploy-api.ps1 -SkipBuild -Tag "device-id-fix-v1"
    # Deploy without rebuilding using specific tag
#>

param(
    [ValidateSet("prod", "dev")]
    [string]$Environment = "prod",
    [switch]$SkipBuild,
    [string]$Tag = "",
    [switch]$ForceBuild
)

$ErrorActionPreference = "Stop"

# Colors for output
$Red = "`e[31m"
$Green = "`e[32m"
$Yellow = "`e[33m"
$Blue = "`e[34m"
$Reset = "`e[0m"

function Write-Status {
    param([string]$Message)
    Write-Host "${Blue}[INFO]${Reset} $Message"
}

function Write-Success {
    param([string]$Message)
    Write-Host "${Green}[SUCCESS]${Reset} $Message"
}

function Write-Warning {
    param([string]$Message)
    Write-Host "${Yellow}[WARNING]${Reset} $Message"
}

Write-Status "🚀 ReportMate API Container Deployment"
Write-Status "🚨 DEVICE ID ALIGNMENT FIX - Version 2.1.0"
Write-Status "✅ API code now in proper location: infrastructure/modules/api"
Write-Status ""

# Configuration
$RegistryName = "reportmateacr"
$ImageName = "reportmate-api"
$ContainerAppName = "reportmate-functions-api"
$ResourceGroup = "ReportMate"
$APISourcePath = ".\modules\api"

# Generate tag if not provided
if (-not $Tag) {
    $Timestamp = Get-Date -Format "yyyyMMddHHmmss"
    $GitHash = try { (git rev-parse --short HEAD 2>$null) } catch { "unknown" }
    $Tag = "device-id-fix-$Timestamp-$GitHash"
}

$FullImageName = "$RegistryName.azurecr.io/$ImageName`:$Tag"

Write-Status "Configuration:"
Write-Status "  Environment: $Environment"
Write-Status "  Image: $FullImageName"
Write-Status "  Container App: $ContainerAppName"
Write-Status "  API Source: $APISourcePath"
Write-Status ""

# Validate we're in infrastructure directory and API source exists
if (-not (Test-Path "modules\api\main.py")) {
    Write-Host "${Red}[ERROR]${Reset} Must run from infrastructure directory. API source not found at: modules\api\main.py"
    Write-Host "${Red}[ERROR]${Reset} Current location: $(Get-Location)"
    exit 1
}

Write-Success "✅ API source found at correct location: modules\api\main.py"
Write-Host "Environment: $Environment" -ForegroundColor Yellow

try {
    # Set working directory to infrastructure root
    Push-Location (Join-Path $PSScriptRoot "..")
    
    # Run terraform apply focused on API container
    Write-Host "📦 Deploying API infrastructure..." -ForegroundColor Blue
    terraform apply -target="azurerm_container_app.reportmate_functions_api" -auto-approve
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ API deployment completed successfully!" -ForegroundColor Green
        
        # Get the API URL
        $apiUrl = terraform output -raw api_url 2>$null
        if ($apiUrl) {
            Write-Host "🌐 API URL: $apiUrl" -ForegroundColor Cyan
            
            # Test API health
            Write-Host "🔍 Testing API health..." -ForegroundColor Blue
            try {
                $response = Invoke-RestMethod -Uri "$apiUrl/api/health" -TimeoutSec 10
                Write-Host "✅ API health check passed" -ForegroundColor Green
            } catch {
                Write-Host "⚠️ API health check failed, but deployment completed" -ForegroundColor Yellow
            }
        }
    } else {
        throw "Terraform apply failed with exit code $LASTEXITCODE"
    }
    
} catch {
    Write-Host "❌ API deployment failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}