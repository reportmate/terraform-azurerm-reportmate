#Requires -Version 7.0
<#
.SYNOPSIS
    Deploy ReportMate Frontend (Next.js Web App)
.DESCRIPTION
    Builds and deploys the Next.js web application to Azure Container Apps
.PARAMETER Environment
    Target environment (prod, dev)
.PARAMETER ForceBuild
    Force rebuild of Docker image
.EXAMPLE
    .\deploy-frontend.ps1
    .\deploy-frontend.ps1 -Environment dev -ForceBuild
#>

param(
    [ValidateSet("prod", "dev")]
    [string]$Environment = "prod",
    [switch]$ForceBuild
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploying ReportMate Frontend (Next.js)" -ForegroundColor Green
Write-Host "Environment: $Environment" -ForegroundColor Yellow

try {
    # Use the existing deploy-containers.ps1 script
    $containerScript = Join-Path $PSScriptRoot "deploy-containers.ps1"
    
    if (Test-Path $containerScript) {
        $params = @("-Environment", $Environment)
        if ($ForceBuild) {
            $params += "-ForceBuild"
        }
        
        & $containerScript @params
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Frontend deployment completed successfully!" -ForegroundColor Green
        } else {
            throw "Frontend deployment failed"
        }
    } else {
        throw "deploy-containers.ps1 script not found"
    }
    
} catch {
    Write-Host "❌ Frontend deployment failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}