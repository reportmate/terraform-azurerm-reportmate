# Deploy Infrastructure - ReportMate
# Single script to deploy all infrastructure components

param(
    [string]$ResourceGroup = "ReportMate",
    [string]$Location = "Canada Central",
    [switch]$SkipAuth = $false
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploying ReportMate Infrastructure..." -ForegroundColor Green

# Check if logged in to Azure
Write-Host "🔐 Checking Azure authentication..." -ForegroundColor Yellow
try {
    az account show --output none
    Write-Host "✅ Azure authentication verified" -ForegroundColor Green
} catch {
    Write-Host "❌ Not logged in to Azure. Please run: az login" -ForegroundColor Red
    exit 1
}

# Create resource group if it doesn't exist
Write-Host "📦 Ensuring resource group exists..." -ForegroundColor Yellow
az group create --name $ResourceGroup --location $Location --output none

# Deploy infrastructure with Terraform
Write-Host "🏗️  Deploying infrastructure with Terraform..." -ForegroundColor Yellow
Push-Location $PSScriptRoot\..

try {
    terraform init
    terraform plan -out=tfplan
    terraform apply tfplan
    Write-Host "✅ Infrastructure deployment completed" -ForegroundColor Green
} catch {
    Write-Error "❌ Infrastructure deployment failed: $_"
    exit 1
} finally {
    Pop-Location
}

# Run database migrations
Write-Host "🗄️  Running database migrations..." -ForegroundColor Yellow
try {
    & "$PSScriptRoot\..\database\migrate.ps1"
    Write-Host "✅ Database migrations completed" -ForegroundColor Green
} catch {
    Write-Warning "⚠️  Database migrations failed: $_"
}

# Deploy Azure Functions
Write-Host "⚡ Deploying Azure Functions..." -ForegroundColor Yellow
try {
    & "$PSScriptRoot\..\modules\functions\deploy.ps1"
    Write-Host "✅ Azure Functions deployment completed" -ForegroundColor Green
} catch {
    Write-Warning "⚠️  Azure Functions deployment failed: $_"
}

# Deploy containers if needed
Write-Host "🐳 Checking container deployments..." -ForegroundColor Yellow
if (Test-Path "$PSScriptRoot\deploy-containers.ps1") {
    try {
        & "$PSScriptRoot\deploy-containers.ps1"
        Write-Host "✅ Container deployments completed" -ForegroundColor Green
    } catch {
        Write-Warning "⚠️  Container deployment failed: $_"
    }
} else {
    Write-Host "ℹ️  No container deployments configured" -ForegroundColor Cyan
}

Write-Host "🎉 ReportMate infrastructure deployment completed!" -ForegroundColor Green
Write-Host "🔗 Check status at:" -ForegroundColor Cyan
Write-Host "   API: https://reportmate-api.azurewebsites.net/api/health" -ForegroundColor Cyan
Write-Host "   Dashboard: https://reportmate-frontend.azurewebsites.net" -ForegroundColor Cyan
