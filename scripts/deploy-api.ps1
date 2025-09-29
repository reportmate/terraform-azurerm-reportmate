#Requires -Version 7.0
<#
.SYNOPSIS
    Deploy ReportMate FastAPI Container (API Functions)
.DESCRIPTION
    Deploys the FastAPI container to Azure Container Apps
.PARAMETER Environment
    Target environment (prod, dev)
.EXAMPLE
    .\deploy-api.ps1
    .\deploy-api.ps1 -Environment dev
#>

param(
    [ValidateSet("prod", "dev")]
    [string]$Environment = "prod"
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploying ReportMate API Container (FastAPI)" -ForegroundColor Green
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