#Requires -Version 7.0
<#
================================================================================
 DEPRECATED - USE CI/CD PIPELINE INSTEAD
================================================================================
 This script is DEPRECATED. Use the Azure DevOps pipeline instead:
 
   pipelines/reportmate-deploy-infra.yml
 
 The pipeline provides:
   - Terraform as single source of truth
   - Image tag variables passed to infrastructure
   - Proper CI/CD with approval gates
   - Audit trail of all deployments
 
 This script is kept ONLY for emergency manual deployments.
================================================================================

.SYNOPSIS
    [DEPRECATED] Deploy ReportMate FastAPI Container - Use CI/CD pipeline instead.
    
.DESCRIPTION
    Deploys the FastAPI container to Azure Container Apps with critical device ID standardization.
    
    DEPRECATED: This script is replaced by pipelines/reportmate-deploy-infra.yml
    
    🚨 CRITICAL FIXES IN THIS VERSION:
    - API image pulled from GHCR (github.com/reportmate/reportmate-api)
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

Write-Status "ReportMate API Container Deployment"
Write-Status "DEVICE ID ALIGNMENT FIX - Version 2.1.0"
Write-Status "Deploying prebuilt API image from GHCR (github.com/reportmate/reportmate-api)"
Write-Status ""

# Configuration
$RegistryName = "reportmateacr"
$ImageName = "reportmate-api"
$ContainerAppName = "reportmate-functions-api"
$ResourceGroup = "ReportMate"
$APISourcePath = "ghcr.io/reportmate/reportmate-api"

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

# The API source lives in its own repo (github.com/reportmate/reportmate-api),
# published to GHCR. This script mirrors that prebuilt image into ACR - there is
# no local API source to validate.
Write-Status "Using prebuilt API image from GHCR (source: github.com/reportmate/reportmate-api)"

try {
    # Set working directory to infrastructure root
    Push-Location (Join-Path $PSScriptRoot "..")
    
    if (-not $SkipBuild) {
        # Authenticate to ACR first
        Write-Host "`nAuthenticating to Azure Container Registry..." -ForegroundColor Blue
        az acr login --name $RegistryName
        if ($LASTEXITCODE -ne 0) {
            throw "ACR authentication failed. Run 'az login' first if needed."
        }
        Write-Success "ACR authentication successful"
        
        Write-Host "`nPulling prebuilt API image from GHCR..." -ForegroundColor Blue
        $GhcrImage = "ghcr.io/reportmate/reportmate-api"
        $GhcrTag = if ($env:GHCR_TAG) { $env:GHCR_TAG } else { "latest" }
        Write-Status "  Source: ${GhcrImage}:${GhcrTag}"
        Write-Status "  Target: $FullImageName"

        & docker pull --platform linux/amd64 "${GhcrImage}:${GhcrTag}"
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to pull API image from GHCR (${GhcrImage}:${GhcrTag})"
        }
        & docker tag "${GhcrImage}:${GhcrTag}" $FullImageName
        if ($LASTEXITCODE -ne 0) {
            throw "Docker tag failed with exit code $LASTEXITCODE"
        }

        Write-Success "API image pulled from GHCR and tagged for ACR"
        
        # Push to Azure Container Registry
        Write-Host "`nPushing image to ACR..." -ForegroundColor Blue
        docker push $FullImageName
        
        if ($LASTEXITCODE -ne 0) {
            throw "Docker push failed with exit code $LASTEXITCODE"
        }
        
        Write-Success "Image pushed to ACR"
        
        # Update container app with new image
        Write-Host "`nUpdating container app..." -ForegroundColor Blue
        
        # Read existing env vars from the live container so they are preserved.
        # az containerapp update --image replaces the entire container spec,
        # which can reset env vars that were set outside Terraform.
        Write-Host "Reading existing environment variables from container..." -ForegroundColor Blue
        $ExistingSecret = az containerapp show `
            --name $ContainerAppName `
            --resource-group $ResourceGroup `
            --query "properties.template.containers[0].env[?name=='API_INTERNAL_SECRET'].value | [0]" `
            -o tsv 2>$null
        $ExistingPassphrase = az containerapp show `
            --name $ContainerAppName `
            --resource-group $ResourceGroup `
            --query "properties.template.containers[0].env[?name=='REPORTMATE_PASSPHRASE'].value | [0]" `
            -o tsv 2>$null
        
        if ([string]::IsNullOrWhiteSpace($ExistingSecret) -or $ExistingSecret -eq 'None') {
            throw "API_INTERNAL_SECRET is not set on the running container. Set it first via Terraform (terraform apply) or az containerapp update --set-env-vars."
        }
        if ([string]::IsNullOrWhiteSpace($ExistingPassphrase) -or $ExistingPassphrase -eq 'None') {
            throw "REPORTMATE_PASSPHRASE is not set on the running container. Set it first via Terraform."
        }
        
        Write-Success "Existing secrets read from live container (not hardcoded)"
        
        $revision = az containerapp update `
            --name $ContainerAppName `
            --resource-group $ResourceGroup `
            --image $FullImageName `
            --set-env-vars `
                "API_INTERNAL_SECRET=$ExistingSecret" `
                "REPORTMATE_PASSPHRASE=$ExistingPassphrase" `
            --query "properties.latestRevisionName" `
            -o tsv
        
        if ($LASTEXITCODE -ne 0) {
            throw "Container app update failed with exit code $LASTEXITCODE"
        }
        
        Write-Success "Container app updated to revision: $revision"
    } else {
        Write-Warning "Skipping Docker build (using existing image: $FullImageName)"
    }
    
    # Test API health
    Write-Host "`nTesting API health..." -ForegroundColor Blue
    $apiUrl = "https://$ContainerAppName.blackdune-79551938.canadacentral.azurecontainerapps.io"
    
    Start-Sleep -Seconds 10  # Give container time to start
    
    try {
        $response = Invoke-RestMethod -Uri "$apiUrl/api/v1/health" -TimeoutSec 30
        Write-Success "API health check passed"
        Write-Host "API URL: $apiUrl" -ForegroundColor Cyan
    } catch {
        Write-Warning "API health check failed, but deployment completed"
        Write-Host "   Try: curl $apiUrl/api/v1/health" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "`nAPI deployment failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}