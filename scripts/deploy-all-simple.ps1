#Requires -Version 7.0
<#
.SYNOPSIS
    Deploy Complete ReportMate Infrastructure
.DESCRIPTION
    Deploys the entire ReportMate infrastructure including API, frontend, and all resources
.PARAMETER Environment
    Target environment (prod, dev)
.EXAMPLE
    .\deploy-all.ps1
    .\deploy-all.ps1 -Environment dev
#>

param(
    [ValidateSet("prod", "dev")]
    [string]$Environment = "prod"
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploying Complete ReportMate Infrastructure" -ForegroundColor Green
Write-Host "Environment: $Environment" -ForegroundColor Yellow

try {
    # Set working directory to infrastructure root
    Push-Location (Join-Path $PSScriptRoot "..")
    
    Write-Host "📦 Deploying complete infrastructure..." -ForegroundColor Blue
    terraform apply -auto-approve
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Complete infrastructure deployment successful!" -ForegroundColor Green
        
        # Get outputs
        $apiUrl = terraform output -raw api_url 2>$null
        $webUrl = terraform output -raw web_app_url 2>$null
        
        if ($apiUrl) {
            Write-Host "🌐 API URL: $apiUrl" -ForegroundColor Cyan
        }
        if ($webUrl) {
            Write-Host "🌐 Web App URL: $webUrl" -ForegroundColor Cyan
        }
        
        # Test endpoints
        if ($apiUrl) {
            Write-Host "🔍 Testing API health..." -ForegroundColor Blue
            try {
                $response = Invoke-RestMethod -Uri "$apiUrl/api/health" -TimeoutSec 10
                Write-Host "✅ API health check passed" -ForegroundColor Green
            } catch {
                Write-Host "⚠️ API health check failed" -ForegroundColor Yellow
            }
        }
        
    } else {
        throw "Infrastructure deployment failed with exit code $LASTEXITCODE"
    }
    
} catch {
    Write-Host "❌ Infrastructure deployment failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}